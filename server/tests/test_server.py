import pytest
from fastapi.testclient import TestClient

from server.app import APP


@pytest.fixture(scope="module")
def client():
    with TestClient(APP) as client:
        yield client


def test_root(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert res.text == "faas"


def test_deploy(client: TestClient):
    res = client.post("/functions/foo/deploy", json={"src": "console.log('hello')"})
    assert res.status_code == 200
    body = res.json()
    assert body["function_id"] == "foo"
    assert body["ok"]


def test_invoke(client: TestClient):
    res = client.post("/functions/foo/invoke")
    assert res.status_code == 200
