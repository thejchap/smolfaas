import logging
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from functools import cache
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ._core import V8System

logging.basicConfig(level=logging.INFO)

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
    source TEXT NOT NULL
);
    """
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    get_v8()
    yield


APP = FastAPI(lifespan=lifespan)


@APP.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    # log ms
    logging.info(
        f"latency {request.method} {request.url.path} {response.status_code} {process_time * 1000:.2f}ms"
    )
    return response


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
    result = v8.compile_and_invoke_source(req.source)
    return SourceInvocationResponse(result=result)


class FunctionDeployRequest(BaseModel):
    source: str


class FunctionDeployResponse(BaseModel):
    ok: bool = True


@APP.post("/functions/{function_id}/deploy", response_model=FunctionDeployResponse)
def deploy(
    function_id: str,
    req: FunctionDeployRequest,
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
):
    cur = conn.cursor()
    cur.execute(
        """
INSERT INTO function (function_id, source)
VALUES (?, ?)
ON CONFLICT (function_id)
DO UPDATE SET
source = excluded.source;
    """,
        (function_id, req.source),
    )
    return FunctionDeployResponse()


class FunctionInvokeRequest(BaseModel):
    payload: dict[str, Any] | None = None


class FunctionInvokeResponse(BaseModel):
    result: str | None = None


@APP.post("/functions/{function_id}/invoke", response_model=FunctionInvokeResponse)
def invoke_function(
    function_id: str,
    v8: Annotated[V8System, Depends(get_v8)],
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
    req: FunctionInvokeRequest | None = None,
):
    cur = conn.cursor()
    cur.execute(
        """
SELECT source
FROM function
WHERE function_id = ?
LIMIT 1;
    """,
        (function_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    source = row["source"]
    if not source:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    res = v8.invoke_function(function_id, source)
    return FunctionInvokeResponse(result=res)
