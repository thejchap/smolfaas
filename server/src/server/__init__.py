from fastapi import FastAPI

from ._core import hello_from_bin

APP = FastAPI()


def hello():
    return hello_from_bin()


@APP.get("/")
async def root():
    return hello()
