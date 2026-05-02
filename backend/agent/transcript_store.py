"""Append-only transcript persistence for sessions (LiveKit + WebSocket)."""

from __future__ import annotations

import json
import logging
from database.connection import get_db
from database.models import TranscriptTurn

logger = logging.getLogger("mykare.transcript")


async def append_transcript_turn(session_id: str, turn: TranscriptTurn) -> None:
    """Read-modify-write the JSON transcript column for the given session."""

    db = get_db()
    async with db.execute(
        "SELECT transcript FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()

    raw = row["transcript"] if row else "[]"
    try:
        history = json.loads(raw or "[]")
    except json.JSONDecodeError:
        history = []
    if not isinstance(history, list):
        history = []

    history.append(turn.model_dump())

    await db.execute(
        "UPDATE sessions SET transcript = ? WHERE id = ?",
        (json.dumps(history, ensure_ascii=False), session_id),
    )
    await db.commit()
