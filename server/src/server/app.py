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
def run(req: RunRequest, v8: Annotated[V8System, Depends(get_v8)], response: Response):
    result: str | None = None
    err: ExceptionResponse | None = None
    try:
        result = v8.run(req.src)
    except RuntimeError as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        err = ExceptionResponse(message=str(e))
    return RunResponse(result=result, error=err)
