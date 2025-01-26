import sqlite3
from contextlib import contextmanager
from functools import cache
from typing import Annotated

from annotated_types import Len
from ulid import ULID

from server._core import V8System

SQLITE_URL = "tmp/db.sqlite3"


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
        conn.executescript(
            """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS function (
    id CHAR(29) PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    live_deployment_id TEXT REFERENCES deployment (id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS deployment (
    id CHAR(29) PRIMARY KEY,
    function_id TEXT REFERENCES function (id) ON DELETE CASCADE NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
    """
        )


PKPrefix = Annotated[str, Len(2)]


def new_primary_key(prefix: PKPrefix) -> str:
    """
    generate a new primary key
    primary key is entity type prefix (2 characters) followed by a hyphen and a ULID
    """
    ulid = ULID()
    return f"{prefix}-{ulid}".lower()
