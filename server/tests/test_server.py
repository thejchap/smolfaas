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
