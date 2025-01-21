from contextlib import asynccontextmanager

from fastapi import FastAPI

from ._core import v8_init, v8_shutdown


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if v8_init() != 0:
        raise RuntimeError("failed to initialize v8")
    yield
    if v8_shutdown() != 0:
        raise RuntimeError("failed to shutdown v8")


APP = FastAPI(lifespan=lifespan)


@APP.get("/")
def root():
    return "hello, world!"


def main():
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=8000)
