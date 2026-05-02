"""
Tool: fetch_slots.

Returns the next batch of available appointment slots filtered against the
existing confirmed bookings, optionally narrowed to a specific date.
"""

from __future__ import annotations

import logging

from database.connection import get_db
from agent.state import AgentSessionState

from ._helpers import enumerate_future_slots, publish_tool_event

logger = logging.getLogger("mykare.tools.fetch_slots")

                                                                                           
_MAX_SLOTS_RETURNED = 8
_VALID_DOCTORS = {
    "Dr. Priya Sharma",
    "Dr. Rohan Mehta",
    "Dr. Neha Kapoor",
    "Dr. Arjun Iyer",
    "Dr. Kavita Rao",
}


async def handler(
    state: AgentSessionState,
    *,
    date_preference: str | None = None,
    doctor_name: str | None = None,
) -> dict:
    """Return up to 8 free slots, optionally biased to a date / doctor."""

    await publish_tool_event(state, tool="fetch_slots", status="loading")

    universe = enumerate_future_slots()

    db = get_db()
    try:
        async with db.execute(
            "SELECT appointment_datetime, doctor_name FROM appointments WHERE status = 'confirmed'"
        ) as cursor:
            booked = {(row["appointment_datetime"], row["doctor_name"]) async for row in cursor}

        wanted_doctor = doctor_name or "Dr. Priya Sharma"
        if wanted_doctor not in _VALID_DOCTORS:
            message = (
                f"I don't have a doctor named {wanted_doctor}. Available doctors are "
                "Dr. Priya Sharma, Dr. Rohan Mehta, Dr. Neha Kapoor, "
                "Dr. Arjun Iyer, and Dr. Kavita Rao."
            )
            await publish_tool_event(
                state, tool="fetch_slots", status="error", message=message
            )
            return {
                "ok": False,
                "error": "unknown_doctor",
                "message": message,
            }

        candidates: list[dict] = []
        for slot in universe:
            if (slot["datetime"], wanted_doctor) in booked:
                continue
            if date_preference and date_preference not in slot["datetime"]:
                continue
            candidates.append({**slot, "doctor": wanted_doctor})

        slots = candidates[:_MAX_SLOTS_RETURNED]
        state.extracted_entities["last_available_slots"] = slots
        state.extracted_entities["last_doctor"] = wanted_doctor
        result = {
            "ok": True,
            "available_slots": slots,
            "doctor": wanted_doctor,
            "count": len(slots),
        }
        await publish_tool_event(
            state,
            tool="fetch_slots",
            status="success",
            result={"count": len(slots), "doctor": wanted_doctor},
        )
        return result
    except Exception as exc:                
        logger.exception("fetch_slots failed")
        message = "I'm having trouble pulling up the calendar — give me a second."
        await publish_tool_event(
            state, tool="fetch_slots", status="error", message=message
        )
        return {
            "ok": False,
            "error": "internal_error",
            "message": message,
            "detail": str(exc),
        }
