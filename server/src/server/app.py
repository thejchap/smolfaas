from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ._core import V8


@asynccontextmanager
async def lifespan(_: FastAPI):
    V8.init()
    yield


APP = FastAPI(lifespan=lifespan)


@APP.get("/", response_class=PlainTextResponse)
def root():
    return "faas"


class DeployRequest(BaseModel):
    src: str


class DeployResponse(BaseModel):
    function_id: str
    ok: bool = True


@APP.post("/functions/{function_id}/deploy", response_model=DeployResponse)
def deploy(function_id: str, req: DeployRequest):
    compiled = V8.compile(req.src)
    return DeployResponse(function_id=function_id)


class InvokeRequest(BaseModel):
    pass


class InvokeResponse(BaseModel):
    pass


@APP.post("/functions/{function_id}/invoke", response_model=InvokeResponse)
def invoke(function_id: str, req: InvokeRequest | None = None):
    return InvokeResponse()
