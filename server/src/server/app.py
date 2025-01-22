from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from ._core import V8

V8_INSTANCE = V8()


@asynccontextmanager
async def lifespan(_: FastAPI):
    V8_INSTANCE.init()
    yield


APP = FastAPI(lifespan=lifespan)


@APP.get("/", response_class=PlainTextResponse)
def root():
    return "faas"
