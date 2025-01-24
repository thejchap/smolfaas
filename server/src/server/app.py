import sqlite3
from contextlib import asynccontextmanager, contextmanager
from functools import cache
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ._core import V8System

SQLITE_URL = "tmp/db.sqlite3"


@cache
def get_v8():
    return V8System()


def get_conn():
    conn = sqlite3.connect(SQLITE_URL)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


get_conn_ctx = contextmanager(get_conn)


def migrate():
    """
    set up sqlite db on startup
    """
    with get_conn_ctx() as conn:
        conn.execute(
            """
CREATE TABLE IF NOT EXISTS function (
    function_id TEXT PRIMARY KEY,
    snapshot BLOB NOT NULL
);
    """
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    get_v8()
    yield


APP = FastAPI(lifespan=lifespan)


@APP.get("/", response_class=PlainTextResponse)
def root():
    return "tinyfaas"


class SourceInvocationRequest(BaseModel):
    source: str


class SourceInvocationResponse(BaseModel):
    result: str


@APP.post("/invoke", response_model=SourceInvocationResponse)
def invoke_source(
    req: SourceInvocationRequest,
    v8: Annotated[V8System, Depends(get_v8)],
):
    """
    compile and run script on the fly
    """
    result = v8.compile_and_run(req.source)
    return SourceInvocationResponse(result=result)


class FunctionDeployRequest(BaseModel):
    source: str


class FunctionDeployResponse(BaseModel):
    ok: bool = True


@APP.post(
    "/functions/{function_id}/deploy",
    response_model=FunctionDeployResponse,
    status_code=status.HTTP_201_CREATED,
)
def deploy(
    function_id: str,
    req: FunctionDeployRequest,
    v8: Annotated[V8System, Depends(get_v8)],
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
    response: Response,
):
    """
    compile script and snapshot v8 heap, store in sqlite for invocation
    """
    snapshot = v8.compile(req.source)
    cur = conn.cursor()
    cur.execute(
        """
INSERT INTO function (function_id, snapshot)
VALUES (?, ?)
ON CONFLICT (function_id)
DO UPDATE SET snapshot = excluded.snapshot;
    """,
        (function_id, snapshot),
    )
    return FunctionDeployResponse()
