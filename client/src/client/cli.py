from pathlib import Path
from typing import Annotated

import requests
import typer

CLI = typer.Typer()
DEFAULT_BASE_URL = "http://localhost:8000"


@CLI.command()
def run(
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
    res = requests.post(f"{base_url}/run", json={"src": src})
    if not res.ok:
        try:
            typer.secho(res.json()["error"]["message"], fg="red")
        except Exception:
            typer.secho(res.text, fg="red")
        raise typer.Exit(1)
    typer.echo(res.json()["result"])
