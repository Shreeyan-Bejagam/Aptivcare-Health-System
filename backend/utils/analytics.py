"""Structured interaction logging for cost and ops dashboards."""

from __future__ import annotations

import json
import logging
from typing import Any

from database.connection import get_db

logger = logging.getLogger("mykare.analytics")


async def log_interaction(
    session_id: str,
    kind: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Best-effort insert; never raises to callers."""

    try:
        db = get_db()
        await db.execute(
            """
            INSERT INTO interaction_logs (session_id, kind, payload)
            VALUES (?, ?, ?)
            """,
            (session_id, kind, json.dumps(payload or {}, ensure_ascii=False)),
        )
        await db.commit()
    except Exception:                
        logger.debug("log_interaction failed", exc_info=True)
