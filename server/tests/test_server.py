import tempfile

import pytest
from fastapi.testclient import TestClient

from server.api import API
from server.utils import get_settings, new_primary_key


@pytest.fixture(scope="module")
def client():
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = get_settings()
        settings.sqlite_url = f"{tmpdir}/db.test.sqlite3"
        with TestClient(API) as client:
            yield client


def test_root(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert res.text == "tinyfaas"


def test_invoke_script(client: TestClient):
    src = """
export default async function handler() {
    return "hello";
};
    """
    res = client.post("/invoke", json={"source": src})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["result"] == "hello"


def test_function_e2e(client: TestClient):
    src = """
export default async function handler() {
    return "hello";
};
    """
    res = client.post("/functions", json={"name": "hello"})
    assert res.status_code == 200, res.text
    function_id = res.json()["function"]["id"]
    res = client.post(f"/functions/{function_id}/deployments", json={"source": src})
    # test warm isolate cache
    for _ in range(3):
        res = client.post(f"/functions/{function_id}/invocations")
        assert res.status_code == 200, res.text
        assert res.json()["result"] == "hello"


def test_create_function(client: TestClient):
    res = client.post("/functions", json={"name": "hello-world"})
    assert res.status_code == 200, res.text
    function = res.json()["function"]
    assert function["id"].startswith("fn-")
    assert len(function["id"]) == 29
    assert function["name"] == "hello-world"
    assert "created_at" in function
    assert "updated_at" in function
    assert "live_deployment_id" in function


def test_pk():
    pk = new_primary_key("fn")
    assert pk.startswith("fn-")
    assert len(pk) == 29
    assert pk == pk.lower()
