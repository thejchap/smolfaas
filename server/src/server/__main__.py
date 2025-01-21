import uvicorn

from server import APP

if __name__ == "__main__":
    uvicorn.run(APP, host="0.0.0.0", port=8000)
