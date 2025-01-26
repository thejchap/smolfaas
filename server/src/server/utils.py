import os
import sqlite3
from contextlib import contextmanager
from functools import cache
from typing import Annotated

from annotated_types import Len
from ulid import ULID

from server._core import V8System

SQLITE_URL = "tmp/db.sqlite3"


def _load_sql() -> dict[str, str]:
    """
    load queries from queries.sql into a dict
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
    return V8System()


def get_conn():
    conn = sqlite3.connect(SQLITE_URL)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
    finally:
        conn.close()


get_conn_ctx = contextmanager(get_conn)


def migrate():
    """
    set up sqlite db on startup
    """
    with get_conn_ctx() as conn:
        conn.executescript(SQL["migrate"])


PKPrefix = Annotated[str, Len(2)]


def new_primary_key(prefix: PKPrefix) -> str:
    """
    generate a new primary key
    primary key is entity type prefix (2 characters) followed by a hyphen and a ULID
    """
    ulid = ULID()
    return f"{prefix}-{ulid}".lower()
