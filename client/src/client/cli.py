import json
from pathlib import Path
from typing import Annotated

import requests
import typer
from rich import print

CLI = typer.Typer()
DEFAULT_BASE_URL = "http://localhost:8000"


@CLI.command()
def invoke(
    module_path: Annotated[
        Path,
        typer.Argument(
            ...,
            help="path to the module to be run. must export a default function.",
        ),
    ],
    base_url: Annotated[
        str,
        typer.Option(
            ...,
            help="base url of the tinyfaas server",
            envvar="BASE_URL",
        ),
    ] = DEFAULT_BASE_URL,
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


@CLI.command()
def deploy(
    function_id: Annotated[
        str,
        typer.Argument(..., help="function id to deploy the module as"),
    ],
    module_path: Annotated[
        Path,
        typer.Argument(
            ...,
            help="path to the module to be run. must export a default function.",
        ),
    ],
    base_url: Annotated[
        str,
        typer.Option(
            ...,
            help="base url of the tinyfaas server",
            envvar="BASE_URL",
        ),
    ] = DEFAULT_BASE_URL,
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
