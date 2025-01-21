from contextlib import asynccontextmanager

from fastapi import FastAPI

from ._core import hello_from_bin, v8_init, v8_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    if v8_init() != 0:
        raise RuntimeError("Failed to initialize V8")
    yield
    if v8_shutdown() != 0:
        raise RuntimeError("Failed to shutdown V8")


APP = FastAPI(lifespan=lifespan)


def hello():
    return hello_from_bin()


@APP.get("/")
async def root():
    return hello()


def main():
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=8000)
