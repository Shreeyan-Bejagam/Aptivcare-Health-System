"""
Database migrations.

We use plain `CREATE TABLE IF NOT EXISTS` statements rather than a heavyweight
migration framework — the schema is small, the deployment surface is a single
SQLite file, and idempotent DDL is enough for our needs.

The double-booking constraint is implemented as a *partial* unique index on
`(appointment_datetime)` that only matches `status='confirmed'` rows. That way
cancelling an appointment frees the slot up for someone else to book, while
two simultaneous "confirmed" rows for the same datetime are still rejected at
the storage layer (as a safety net behind the application-level pre-check).
"""

from __future__ import annotations

import logging

from .connection import get_db

logger = logging.getLogger("mykare.db.migrations")


_SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS users (
        phone       TEXT PRIMARY KEY,
        name        TEXT,
        created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS appointments (
        id                    TEXT PRIMARY KEY,
        user_phone            TEXT NOT NULL,
        appointment_datetime  TEXT NOT NULL,
        doctor_name           TEXT NOT NULL DEFAULT 'Dr. Priya Sharma',
        status                TEXT NOT NULL DEFAULT 'confirmed'
                              CHECK(status IN ('confirmed','cancelled')),
        created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_phone) REFERENCES users(phone)
    )
    """,
                                                                          
                                                                  
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_unique_confirmed
    ON appointments(appointment_datetime, doctor_name)
    WHERE status = 'confirmed'
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_appointments_user_phone
    ON appointments(user_phone)
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id              TEXT PRIMARY KEY,
        user_phone      TEXT,
        transcript      TEXT NOT NULL DEFAULT '[]',
        summary         TEXT,
        cost_breakdown  TEXT,
        started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ended_at        TIMESTAMP
    )
    """,
                                                                       
    """
    CREATE TABLE IF NOT EXISTS interaction_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL,
        kind        TEXT NOT NULL,
        payload     TEXT,
        created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_interaction_logs_session
    ON interaction_logs(session_id)
    """,
                                                                                      
    """
    CREATE VIEW IF NOT EXISTS conversations AS
    SELECT
        id,
        user_phone AS user_id,
        transcript,
        summary,
        started_at AS timestamp
    FROM sessions
    """,
]


async def run_migrations() -> None:
    """Apply every CREATE statement; safe to call repeatedly."""

    db = get_db()
    for statement in _SCHEMA_STATEMENTS:
        await db.execute(statement)
    await db.commit()
    logger.info("Database schema is up to date (%d statements applied).", len(_SCHEMA_STATEMENTS))
