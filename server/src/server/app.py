import sqlite3
from contextlib import asynccontextmanager
from functools import cache
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ._core import V8System


@cache
def get_v8():
    return V8System()


def get_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_v8()
    yield


APP = FastAPI(lifespan=lifespan)


@APP.get("/", response_class=PlainTextResponse)
def root():
    return "tinyfaas"


class RunRequest(BaseModel):
    src: str


class ExceptionResponse(BaseModel):
    message: str


class RunResponse(BaseModel):
    result: str | None = None
    error: ExceptionResponse | None = None


@APP.post("/run", response_model=RunResponse)
def run(
    req: RunRequest,
    v8: Annotated[V8System, Depends(get_v8)],
    response: Response,
):
    result: str | None = None
    err: ExceptionResponse | None = None
    try:
        result = v8.compile_and_run(req.src)
    except RuntimeError as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        err = ExceptionResponse(message=str(e))
    return RunResponse(result=result, error=err)


class DeployRequest(BaseModel):
    src: str


class DeployResponse(BaseModel):
    pass


@APP.post(
    "/functions/{function_id}/deploy",
    response_model=DeployResponse,
    status_code=status.HTTP_201_CREATED,
)
def deploy(
    function_id: str,
    req: DeployRequest,
    v8: Annotated[V8System, Depends(get_v8)],
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
    response: Response,
):
    _snapshot = v8.compile(req.src)
    cur = conn.cursor()
    res = cur.execute("SELECT 'hello';")
    _row = res.fetchone()
    return DeployResponse()
