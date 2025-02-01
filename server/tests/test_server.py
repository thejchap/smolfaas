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
    assert res.text == "smolfaas"


def test_invoke_script(client: TestClient):
    src = """
export default async function handler() {
    return {
        result: "hello"
    };
};
    """
    res = client.post("/invoke", json={"source": src})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["result"] == "hello"


def test_promise_basic(client: TestClient):
    src = """
export default async function handler() {
    return new Promise((resolve, reject) => {
        resolve({result: "hello"});
    });
};
    """
    res = client.post("/invoke", json={"source": src})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["result"] == "hello"


def test_promise_all(client: TestClient):
    src = """
async function sayHi(name) {
    return `Hello, ${name}!`;
}
export default async function handler() {
    const results = await Promise.all([
        sayHi('Alice'),
        sayHi('Bob'),
        sayHi('Charlie'),
        sayHi('Dave')
    ]);
    return {
        results
    };
};
"""
    res = client.post("/invoke", json={"source": src})
    assert res.status_code == 200, res.text
    assert res.json()["results"] == [
        "Hello, Alice!",
        "Hello, Bob!",
        "Hello, Charlie!",
        "Hello, Dave!",
    ]


def test_invoke_script_with_payload(client: TestClient):
    src = """
export default async function handler(payload) {
    return {
        result: "hello " + payload.name
    };
};
    """
    res = client.post("/invoke", json={"source": src, "payload": {"name": "world"}})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("result") == "hello world", body


def test_exceptions(client: TestClient):
    src = """
export default async function handler() {
    throw new Error("error");
};
    """
    with pytest.raises(RuntimeError):
        client.post("/invoke", json={"source": src})


def test_function_e2e(client: TestClient):
    src = """
let count = 0;
export default async function handler() {
    return {
        result: "hello" + count++
    }
};
    """
    res = client.post("/functions", json={"name": "hello"})
    assert res.status_code == 200, res.text
    function_id = res.json()["function"]["id"]
    res = client.post(f"/functions/{function_id}/deployments", json={"source": src})
    # test warm isolate cache
    for i in range(3):
        res = client.post(f"/functions/{function_id}/invocations")
        assert res.status_code == 200, res.text
        assert res.json()["result"] == f"hello{i}"
    src2 = """
export default async function handler() {
    return {
        result: "world"
    }
};
    """
    res = client.post(f"/functions/{function_id}/deployments", json={"source": src2})
    assert res.status_code == 200, res.text
    deployment_id = res.json()["deployment"]["id"]
    res = client.get(f"/functions/{function_id}")
    assert res.status_code == 200, res.text
    function = res.json()["function"]
    assert function["live_deployment_id"] == deployment_id
    res = client.post(f"/functions/{function_id}/invocations")
    assert res.status_code == 200, res.text
    assert res.json()["result"] == "world"


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
