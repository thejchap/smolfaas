import os
import sqlite3
from contextlib import contextmanager
from functools import cache
from typing import Annotated

from annotated_types import Len
from fastapi import Depends
from pydantic import Field
from pydantic_settings import BaseSettings
from ulid import ULID

from server._core import V8System


class Settings(BaseSettings):
    sqlite_url: str = Field(default="db.sqlite3")


def _load_sql() -> dict[str, str]:
    """
    load queries from queries.sql into a dict
    allows for a bunch of queries in one sql file that look like:
    -- query:begin name
    SELECT * FROM table;
    -- query:end
    """
    res: dict[str, str] = {}
    name = ""
    with open(os.path.join(os.path.dirname(__file__), "queries.sql")) as f:
        for line in f.readlines():
            if line.startswith("-- query:begin "):
                name = line.split(" ")[-1].strip()
                res[name] = ""
            elif line.startswith("-- query:end"):
                res[name] = res[name].strip()
            else:
                res[name] += line
    return res


SQL = _load_sql()


@cache
def get_v8():
    """
    ensure only one V8System instance is created
    and have control over when it is created
    """
    return V8System()


@cache
def get_settings():
    """
    load settings from environment variables + defaults
    """
    return Settings()


def get_conn(
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    get a connection to the sqlite db
    if any statements fail, the transaction is rolled back
    """
    conn = sqlite3.connect(settings.sqlite_url)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            conn.execute(SQL["foreign_keys_on"])
            yield conn
    finally:
        conn.close()


get_conn_ctx = contextmanager(get_conn)


def migrate():
    """
    run script to create tables and indexes
    """
    with get_conn_ctx(get_settings()) as conn:
        conn.executescript(SQL["migrate"])


PKPrefix = Annotated[str, Len(2)]


def new_primary_key(prefix: PKPrefix) -> str:
    """
    generate a new primary key
    primary key is entity type prefix (2 characters) followed by a hyphen and a ULID
    """
    ulid = ULID()
    return f"{prefix}-{ulid}".lower()
