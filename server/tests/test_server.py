from fastapi.testclient import TestClient

from server.app import APP

CLIENT = TestClient(APP)


def test_root():
    res = CLIENT.get("/")
    assert res.status_code == 200
    assert res.text == "faas"
