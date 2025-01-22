from contextlib import asynccontextmanager
from functools import cache
from typing import Annotated

from fastapi import Depends, FastAPI
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
    func: str
    args: list[str | int]


class RunResponse(BaseModel):
    result: str


@APP.post("/run", response_model=RunResponse)
def run(req: RunRequest, v8: Annotated[V8System, Depends(get_v8)]):
    result = v8.run(req.func)
    return RunResponse(result=result)
