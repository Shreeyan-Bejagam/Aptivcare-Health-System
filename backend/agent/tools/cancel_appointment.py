"""
Tool: cancel_appointment.

Soft-deletes a booking by flipping its status to 'cancelled'. The user_phone
on the call is checked against the row's owner to prevent a stranger from
cancelling somebody else's appointment.
"""

from __future__ import annotations

import logging

from database.connection import get_db
from agent.state import AgentSessionState

from ._helpers import publish_tool_event

logger = logging.getLogger("mykare.tools.cancel_appointment")


async def handler(
    state: AgentSessionState,
    *,
    appointment_id: str,
    user_phone: str | None = None,
) -> dict:
    await publish_tool_event(state, tool="cancel_appointment", status="loading")

    phone = user_phone or state.user_phone
    if not phone:
        message = "I need your phone number before I can change a booking."
        await publish_tool_event(
            state, tool="cancel_appointment", status="error", message=message
        )
        return {"ok": False, "error": "no_user_identified", "message": message}

    if not appointment_id or not appointment_id.strip():
        message = "I need the appointment reference — could you confirm which one?"
        await publish_tool_event(
            state, tool="cancel_appointment", status="error", message=message
        )
        return {"ok": False, "error": "invalid_id", "message": message}

    db = get_db()
    try:
        async with db.execute(
            "SELECT user_phone, status FROM appointments WHERE id = ?",
            (appointment_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            message = "I don't see that appointment in our system."
            await publish_tool_event(
                state, tool="cancel_appointment", status="error", message=message
            )
            return {"ok": False, "error": "not_found", "message": message}

        if row["user_phone"] != phone:
            message = "That appointment isn't under your phone number."
            await publish_tool_event(
                state, tool="cancel_appointment", status="error", message=message
            )
            return {"ok": False, "error": "ownership_mismatch", "message": message}

        if row["status"] == "cancelled":
            await publish_tool_event(
                state,
                tool="cancel_appointment",
                status="success",
                result={"appointment_id": appointment_id, "already_cancelled": True},
            )
            return {
                "ok": True,
                "cancelled": True,
                "appointment_id": appointment_id,
                "already_cancelled": True,
                "message": "That appointment is already cancelled.",
            }

        await db.execute(
            "UPDATE appointments SET status = 'cancelled' WHERE id = ?",
            (appointment_id,),
        )
        await db.commit()

        await publish_tool_event(
            state,
            tool="cancel_appointment",
            status="success",
            result={"appointment_id": appointment_id},
        )
        return {
            "ok": True,
            "cancelled": True,
            "appointment_id": appointment_id,
            "message": "Cancelled successfully.",
        }
    except Exception as exc:                
        logger.exception("cancel_appointment failed for id=%s", appointment_id)
        message = "Something went wrong cancelling — let me try once more."
        await publish_tool_event(
            state, tool="cancel_appointment", status="error", message=message
        )
        return {
            "ok": False,
            "error": "internal_error",
            "message": message,
            "detail": str(exc),
        }
