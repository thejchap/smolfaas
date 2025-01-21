import uvicorn

from server import APP

uvicorn.run(APP, host="0.0.0.0", port=8000)
