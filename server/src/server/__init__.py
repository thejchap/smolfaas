from fastapi import FastAPI

from ._core import hello_from_bin

APP = FastAPI()


def hello():
    return hello_from_bin()


@APP.get("/")
async def root():
    return hello()


def main():
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=8000)
