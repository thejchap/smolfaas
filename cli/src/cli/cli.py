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


@CLI.command(name="invoke", help="invoke a module")
def invoke(
    module_path: ModulePath,
    base_url: BaseURL = DEFAULT_BASE_URL,
):
    with open(module_path) as f:
        src = f.read()
    res = requests.post(f"{base_url}/invoke", json={"source": src})
    if not res.ok:
        try:
            typer.secho(res.json()["error"]["message"], fg="red")
        except Exception:
            typer.secho(res.text, fg="red")
        raise typer.Exit(1)
    print(json.dumps(res.json(), indent=2))


@FUNCTIONS_CLI.command(name="deploy", help="deploy a function")
def deploy_function(
    function_id: Annotated[
        str,
        typer.Argument(..., help="function id to deploy the module as"),
    ],
    module_path: ModulePath,
    base_url: BaseURL = DEFAULT_BASE_URL,
):
    with open(module_path) as f:
        src = f.read()
    res = requests.post(
        f"{base_url}/functions/{function_id}/deploy", json={"source": src}
    )
    if not res.ok:
        try:
            typer.secho(res.json()["error"]["message"], fg="red")
        except Exception:
            typer.secho(res.text, fg="red")
        raise typer.Exit(1)
    print(json.dumps(res.json(), indent=2))


@FUNCTIONS_CLI.command(name="invoke", help="invoke a function")
def invoke_function(
    function_id: Annotated[
        str,
        typer.Argument(..., help="function id to invoke"),
    ],
    base_url: BaseURL = DEFAULT_BASE_URL,
):
    res = requests.post(f"{base_url}/functions/{function_id}/invoke")
    if not res.ok:
        try:
            typer.secho(res.json()["error"]["message"], fg="red")
        except Exception:
            typer.secho(res.text, fg="red")
        raise typer.Exit(1)
    print(json.dumps(res.json(), indent=2))
