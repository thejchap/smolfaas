import json
import logging
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime
from random import randint
from typing import Annotated, Any

from faker import Faker
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
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
API = FastAPI(
    lifespan=lifespan,
    title="smolfaas",
    description="""\
a tiny (<1k loc) faas platform.
inspired by CloudFlare Workers/Vercel Edge Functions.
adventures in embedded V8.
<a href='https://github.com/thejchap/smolfaas'>github.com/thejchap/smolfaas</a>
""".strip(),
    servers=[
        {"url": "https://smolfaas.jchap.me", "description": "production"},
        {"url": "http://localhost:8000", "description": "development"},
    ],
)


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


@API.get("/", response_class=HTMLResponse)
def root():
    return """\
<html>
    <head>
        <title>smolfaas</title>
    </head>
    <body>
        <h1>smolfaas</h1>
        <a href="/docs">docs</a>
        <a href="https://github.com/thejchap/smolfaas">source</a>
    </body>
</html>
""".strip()


"""

invoke arbitrary source code

"""


class SourceInvocationRequest(BaseModel):
    source: str = Field(
        ...,
        min_length=1,
        description="source code to run",
        examples=[
            "export default async (payload)=>({hello: payload.name})",
        ],
    )
    payload: dict[str, Any] | None = Field(
        None, description="function invocation payload", examples=[{"name": "world"}]
    )


@API.post(
    "/invoke",
    response_class=JSONResponse,
    description="invoke arbitrary source code with or without a payload",
    summary="invoke source code",
)
def invoke_source(
    req: SourceInvocationRequest,
    v8: Annotated[V8System, Depends(get_v8)],
):
    """
    compile and run script on the fly
    """
    result = v8.compile_and_invoke_source(
        req.source,
        json.dumps(req.payload),
    )
    return JSONResponse(content=json.loads(result))


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
        description="function name",
        examples=["hello-world-1234"],
    )
    _id: str = PrivateAttr(default_factory=lambda: new_primary_key("fn"))


class FunctionRow(BaseModel):
    id_: str = Field(alias="id", description="function id")
    name: str = Field(description="function name")
    created_at: datetime = Field(description="function creation time")
    updated_at: datetime = Field(description="function last update time")
    live_deployment_id: str | None = Field(
        None, description="currently live deployment id responding to invocations"
    )


class FunctionCreateResponse(BaseModel):
    function: FunctionRow


@API.post(
    "/functions",
    response_model=FunctionCreateResponse,
    tags=["functions"],
    description="create a new function",
    summary="create function",
)
def create_function(
    req: FunctionCreateRequest,
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
):
    cur = conn.cursor()
    cur.execute(SQL["create_function"], (req._id, req.name))
    row = cur.fetchone()
    return FunctionCreateResponse(function=FunctionRow.model_validate(dict(row)))


"""

deploy a function

"""


class FunctionDeployRequest(BaseModel):
    source: str = Field(
        ...,
        min_length=1,
        description="source code to deploy",
        examples=[
            "export default async (payload)=>({hello: payload.name})",
        ],
    )
    _id: str = PrivateAttr(default_factory=lambda: new_primary_key("dp"))


class CreatedDeployment(BaseModel):
    id_: str = Field(alias="id")
    source: str = Field(description="source code")
    function_id: str = Field(description="function id")


class FunctionDeployResponse(BaseModel):
    deployment: CreatedDeployment


@API.post(
    "/functions/{function_id}/deployments",
    response_model=FunctionDeployResponse,
    tags=["functions"],
    summary="deploy function",
    description="deploy a new version of a function and set it as the live deployment",
)
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


@API.post(
    "/functions/{function_id}/invocations",
    response_class=JSONResponse,
    tags=["functions"],
    summary="invoke function",
    description="invoke a function with or without a payload",
)
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
        json.dumps(request or {}),
    )
    return JSONResponse(content=json.loads(res))


"""

fetch a function

"""


class FunctionGetResponse(BaseModel):
    function: FunctionRow


@API.get(
    "/functions/{function_id}",
    response_model=FunctionGetResponse,
    tags=["functions"],
    summary="get function",
    description="get a function by id",
)
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
    return FunctionGetResponse(function=FunctionRow.model_validate(dict(row)))


"""

list functions

"""


class FunctionListResponse(BaseModel):
    functions: list[FunctionRow]


@API.get(
    "/functions",
    response_model=FunctionListResponse,
    tags=["functions"],
    summary="list functions",
    description="list all functions",
)
def list_functions(
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
):
    cur = conn.cursor()
    cur.execute(SQL["list_functions"])
    rows = [FunctionRow.model_validate(dict(row)) for row in cur.fetchall()]
    return FunctionListResponse(functions=rows)
