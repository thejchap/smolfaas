import json
from pathlib import Path
from typing import Annotated

import requests
import typer
from rich import print

CLI = typer.Typer()
FUNCTIONS_CLI = typer.Typer()
CLI.add_typer(FUNCTIONS_CLI, name="functions")
DEFAULT_BASE_URL = "http://localhost:8000"


ModulePath = Annotated[
    Path,
    typer.Argument(
        ..., help="path to the module to be run. must export a default function."
    ),
]
BaseURL = Annotated[
    str,
    typer.Option(..., help="base url of the tinyfaas server", envvar="BASE_URL"),
]
FunctionId = Annotated[
    str,
    typer.Option(..., help="function id to deploy the module to"),
]


@CLI.command(name="invoke", help="invoke a script")
def invoke(
    module_path: ModulePath,
    base_url: BaseURL = DEFAULT_BASE_URL,
):
    with open(module_path) as f:
        src = f.read()
    res = requests.post(f"{base_url}/invoke", json={"source": src})
    res.raise_for_status()
    print(json.dumps(res.json(), indent=2))


@FUNCTIONS_CLI.command(name="deploy", help="deploy a function")
def deploy_function(
    function_id: FunctionId,
    module_path: ModulePath,
    base_url: BaseURL = DEFAULT_BASE_URL,
):
    with open(module_path) as f:
        src = f.read()
    res = requests.post(
        f"{base_url}/functions/{function_id}/deployments", json={"source": src}
    )
    res.raise_for_status()
    print(json.dumps(res.json(), indent=2))


@FUNCTIONS_CLI.command(name="invoke", help="invoke a function")
def invoke_function(
    function_id: FunctionId,
    base_url: BaseURL = DEFAULT_BASE_URL,
):
    res = requests.post(f"{base_url}/functions/{function_id}/invocations")
    res.raise_for_status()
    print(json.dumps(res.json(), indent=2))


@FUNCTIONS_CLI.command(name="create", help="create a function")
def create_functions(
    name: Annotated[
        str,
        typer.Option(..., help="function name"),
    ]
    | None = None,
    base_url: BaseURL = DEFAULT_BASE_URL,
):
    body = {}
    if name:
        body["name"] = name
    res = requests.post(f"{base_url}/functions", json=body)
    if res.status_code == 422:
        print(json.dumps(res.json(), indent=2))
        typer.Exit(code=1)
    else:
        res.raise_for_status()
    print(json.dumps(res.json(), indent=2))
