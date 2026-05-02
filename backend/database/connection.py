"""
Async SQLite connection management.

We hold a single shared `aiosqlite.Connection` for the lifetime of the process.
SQLite serialises writes anyway, so a connection pool would buy us nothing —
having one connection means we can guarantee `PRAGMA journal_mode=WAL` is applied
exactly once, and avoids the transaction-isolation gotchas that plague pooled
SQLite setups.

The connection is created in `init_db()` (called from FastAPI's lifespan) and
disposed in `close_db()`. Other modules call `get_db()` to retrieve it.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import aiosqlite

from config import settings

logger = logging.getLogger("mykare.db")

_db: Optional[aiosqlite.Connection] = None


async def init_db() -> aiosqlite.Connection:
    """Open the SQLite connection, configure WAL mode + foreign keys, and return it."""

    global _db
    if _db is not None:
        return _db

    db_path = settings.DATABASE_PATH
    parent_dir = os.path.dirname(os.path.abspath(db_path))
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    logger.info("Opening SQLite database at %s", db_path)
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row

                                                                              
                                                        
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await conn.commit()

    _db = conn
    return conn


def get_db() -> aiosqlite.Connection:
    """Return the shared connection. Raises if `init_db()` hasn't been called yet."""

    if _db is None:
        raise RuntimeError(
            "Database is not initialised. Did you forget to call init_db()?"
        )
    return _db


async def close_db() -> None:
    """Flush and close the shared connection. Safe to call more than once."""

    global _db
    if _db is None:
        return
    try:
        await _db.commit()
        await _db.close()
        logger.info("SQLite connection closed cleanly.")
    finally:
        _db = None
