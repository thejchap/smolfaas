import uvicorn

from server import API

uvicorn.run(API, host="0.0.0.0", port=8000)
