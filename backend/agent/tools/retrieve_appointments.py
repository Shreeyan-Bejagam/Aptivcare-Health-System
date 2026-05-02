"""
Tool: retrieve_appointments.

Lists every confirmed appointment for the identified patient. Cancelled rows
are excluded by default — the agent rarely needs to mention them out loud.
"""

from __future__ import annotations

import logging

from database.connection import get_db
from agent.state import AgentSessionState

from ._helpers import publish_tool_event

logger = logging.getLogger("mykare.tools.retrieve_appointments")


async def handler(
    state: AgentSessionState,
    *,
    user_phone: str | None = None,
    include_cancelled: bool = False,
) -> dict:
    await publish_tool_event(state, tool="retrieve_appointments", status="loading")

    phone = user_phone or state.user_phone
    if not phone:
        message = "I need your phone number first — could you share it?"
        await publish_tool_event(
            state,
            tool="retrieve_appointments",
            status="error",
            message=message,
        )
        return {"ok": False, "error": "no_user_identified", "message": message}

    db = get_db()
    try:
        if include_cancelled:
            sql = (
                "SELECT id, appointment_datetime, doctor_name, status, created_at "
                "FROM appointments WHERE user_phone = ? "
                "ORDER BY appointment_datetime ASC"
            )
        else:
            sql = (
                "SELECT id, appointment_datetime, doctor_name, status, created_at "
                "FROM appointments WHERE user_phone = ? AND status = 'confirmed' "
                "ORDER BY appointment_datetime ASC"
            )

        async with db.execute(sql, (phone,)) as cursor:
            rows = await cursor.fetchall()

        appointments = [
            {
                "id": row["id"],
                "datetime": row["appointment_datetime"],
                "doctor": row["doctor_name"],
                "status": row["status"],
            }
            for row in rows
        ]
        result = {"ok": True, "appointments": appointments, "count": len(appointments)}
        await publish_tool_event(
            state,
            tool="retrieve_appointments",
            status="success",
            result={"count": len(appointments)},
        )
        return result
    except Exception as exc:                
        logger.exception("retrieve_appointments failed for phone=%s", phone)
        message = "I couldn't pull up your appointments just now — bear with me."
        await publish_tool_event(
            state,
            tool="retrieve_appointments",
            status="error",
            message=message,
        )
        return {
            "ok": False,
            "error": "internal_error",
            "message": message,
            "detail": str(exc),
        }
