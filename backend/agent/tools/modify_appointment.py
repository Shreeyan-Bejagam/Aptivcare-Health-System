"""
Tool: modify_appointment.

Re-schedules an existing appointment by atomically cancelling the old row
and inserting a new confirmed one. We open an explicit transaction
(`BEGIN ... COMMIT`) so that a partial failure (e.g. the new slot is taken)
leaves the old appointment untouched.
"""

from __future__ import annotations

import logging
import secrets

import aiosqlite

from database.connection import get_db
from agent.state import AgentSessionState

from ._helpers import enumerate_future_slots, parse_user_datetime, publish_tool_event

logger = logging.getLogger("mykare.tools.modify_appointment")


async def _alternatives(doctor_name: str, around: str, count: int = 3) -> list[dict]:
    universe = enumerate_future_slots()
    db = get_db()
    async with db.execute(
        "SELECT appointment_datetime, doctor_name FROM appointments WHERE status = 'confirmed'"
    ) as cursor:
        booked = {(row["appointment_datetime"], row["doctor_name"]) async for row in cursor}
    free = [s for s in universe if (s["datetime"], doctor_name) not in booked]
    later = [s for s in free if s["datetime"] >= around]
    earlier = [s for s in free if s["datetime"] < around]
    return [{**slot, "doctor": doctor_name} for slot in (later + earlier)[:count]]


async def handler(
    state: AgentSessionState,
    *,
    appointment_id: str,
    new_datetime: str,
    user_phone: str | None = None,
) -> dict:
    await publish_tool_event(state, tool="modify_appointment", status="loading")

    phone = user_phone or state.user_phone
    if not phone:
        message = "I need your phone number first."
        await publish_tool_event(
            state, tool="modify_appointment", status="error", message=message
        )
        return {"ok": False, "error": "no_user_identified", "message": message}

    canonical_dt = parse_user_datetime(new_datetime)
    if canonical_dt is None:
        message = "I couldn't parse that new time — could you say it again?"
        await publish_tool_event(
            state, tool="modify_appointment", status="error", message=message
        )
        return {
            "ok": False,
            "error": "invalid_datetime",
            "message": message,
            "received": new_datetime,
        }

    db = get_db()
    try:
        async with db.execute(
            "SELECT user_phone, doctor_name, status FROM appointments WHERE id = ?",
            (appointment_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            message = "I don't see that appointment in our system."
            await publish_tool_event(
                state, tool="modify_appointment", status="error", message=message
            )
            return {"ok": False, "error": "not_found", "message": message}

        if row["user_phone"] != phone:
            message = "That appointment isn't under your phone number."
            await publish_tool_event(
                state, tool="modify_appointment", status="error", message=message
            )
            return {"ok": False, "error": "ownership_mismatch", "message": message}

        if row["status"] != "confirmed":
            message = "That booking isn't active any more — let's set up a new one."
            await publish_tool_event(
                state, tool="modify_appointment", status="error", message=message
            )
            return {"ok": False, "error": "not_confirmed", "message": message}

        doctor = row["doctor_name"]
        new_appointment_id = secrets.token_hex(4)

        try:
            await db.execute("BEGIN")
            await db.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = ?",
                (appointment_id,),
            )
            await db.execute(
                """
                INSERT INTO appointments
                    (id, user_phone, appointment_datetime, doctor_name, status)
                VALUES (?, ?, ?, ?, 'confirmed')
                """,
                (new_appointment_id, phone, canonical_dt, doctor),
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            await db.rollback()
            alternatives = await _alternatives(doctor, canonical_dt)
            message = "That new slot is taken — here are some alternatives."
            await publish_tool_event(
                state,
                tool="modify_appointment",
                status="error",
                message=message,
                result={"alternatives": alternatives},
            )
            return {
                "ok": False,
                "error": "slot_taken",
                "alternatives": alternatives,
                "message": message,
            }

        result = {
            "ok": True,
            "old_appointment_id": appointment_id,
            "new_appointment_id": new_appointment_id,
            "new_datetime": canonical_dt,
            "doctor_name": doctor,
            "message": f"Moved to {canonical_dt} with {doctor}.",
        }
        await publish_tool_event(
            state,
            tool="modify_appointment",
            status="success",
            result={
                "old_appointment_id": appointment_id,
                "new_appointment_id": new_appointment_id,
                "new_datetime": canonical_dt,
                "doctor": doctor,
            },
        )
        return result
    except Exception as exc:                
        logger.exception("modify_appointment failed for id=%s", appointment_id)
        message = "Something went wrong rescheduling — give me a moment."
        await publish_tool_event(
            state, tool="modify_appointment", status="error", message=message
        )
        return {
            "ok": False,
            "error": "internal_error",
            "message": message,
            "detail": str(exc),
        }
