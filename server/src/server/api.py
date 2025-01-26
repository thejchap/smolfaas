import logging
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime
from random import randint
from typing import Annotated, Any

from faker import Faker
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, PrivateAttr

from server.utils import SQL, get_conn, get_v8, migrate, new_primary_key

from ._core import V8System

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    get_v8()
    yield


FAKER = Faker()
API = FastAPI(lifespan=lifespan)


@API.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(
        f"latency {request.method} {request.url.path} {response.status_code} {process_time * 1000:.2f}ms"
    )
    return response


@API.get("/", response_class=PlainTextResponse)
def root():
    return "tinyfaas"


"""

invoke arbitrary source code

"""


class SourceInvocationRequest(BaseModel):
    source: str


class SourceInvocationResponse(BaseModel):
    result: str


@API.post("/invoke", response_model=SourceInvocationResponse)
def invoke_source(
    req: SourceInvocationRequest,
    v8: Annotated[V8System, Depends(get_v8)],
):
    """
    compile and run script on the fly
    """
    result = v8.compile_and_invoke_source(req.source)
    return SourceInvocationResponse(result=result)


"""

functions

"""


"""

create a function

"""


class FunctionCreateRequest(BaseModel):
    name: str = Field(
        default_factory=lambda: "-".join(
            FAKER.words(2, unique=True) + [str(randint(1000, 9999))]
        ),
        min_length=1,
    )
    _id: str = PrivateAttr(default_factory=lambda: new_primary_key("fn"))


class CreatedFunction(BaseModel):
    id_: str = Field(alias="id")
    name: str
    created_at: datetime
    updated_at: datetime
    live_deployment_id: str | None = None


class FunctionCreateResponse(BaseModel):
    function: CreatedFunction


@API.post("/functions", response_model=FunctionCreateResponse)
def create_function(
    req: FunctionCreateRequest,
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
):
    cur = conn.cursor()
    cur.execute(SQL["create_function"], (req._id, req.name))
    row = cur.fetchone()
    return FunctionCreateResponse(function=CreatedFunction.model_validate(dict(row)))


"""

deploy a function

"""


class FunctionDeployRequest(BaseModel):
    source: str
    _id: str = PrivateAttr(default_factory=lambda: new_primary_key("dp"))


class CreatedDeployment(BaseModel):
    id_: str = Field(alias="id")
    source: str
    function_id: str


class FunctionDeployResponse(BaseModel):
    deployment: CreatedDeployment


@API.post("/functions/{function_id}/deployments", response_model=FunctionDeployResponse)
def deploy_function(
    function_id: str,
    req: FunctionDeployRequest,
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
):
    cur = conn.cursor()
    cur.execute(SQL["create_deployment"], (req._id, function_id, req.source))
    row = cur.fetchone()
    cur.execute(SQL["update_live_deployment"], (req._id, function_id))
    return FunctionDeployResponse(
        deployment=CreatedDeployment.model_validate(dict(row))
    )


"""

invoke a function

"""


class FunctionInvokeResponse(BaseModel):
    result: str | None = None


@API.post("/functions/{function_id}/invocations", response_model=FunctionInvokeResponse)
def invoke_function(
    function_id: str,
    v8: Annotated[V8System, Depends(get_v8)],
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
    request: dict[Any, Any] | None = None,
):
    cur = conn.cursor()
    cur.execute(SQL["get_live_deployment_for_function"], (function_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no live deployment",
        )
    source = row["source"]
    deployment_id = row["deployment_id"]
    if not source or not deployment_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="missing source code or deployment id",
        )
    res = v8.invoke_function(
        function_id,
        source,
        deployment_id,
        request,
    )
    return FunctionInvokeResponse(result=res)


"""

fetch a function

"""


class FunctionGetResponse(BaseModel):
    function: CreatedFunction


@API.get("/functions/{function_id}", response_model=FunctionGetResponse)
def get_function(
    function_id: str,
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
):
    cur = conn.cursor()
    cur.execute(SQL["get_function"], (function_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="function not found",
        )
    return FunctionGetResponse(function=CreatedFunction.model_validate(dict(row)))
