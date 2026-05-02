"""
Tool: book_appointment.

Creates a confirmed appointment row, with a defence-in-depth approach to the
double-booking problem:

  1. Application-level pre-check via SELECT (cheap, common case).
  2. UNIQUE partial index in the schema (catches the rare race condition
     between concurrent agents).

If either check rejects the booking we return up to three nearby alternatives
so the agent can read them straight back to the patient.
"""

from __future__ import annotations

import logging
import secrets

import aiosqlite

from database.connection import get_db
from agent.state import AgentSessionState

from ._helpers import (
    enumerate_future_slots,
    normalize_phone,
    parse_user_datetime,
    publish_tool_event,
)

logger = logging.getLogger("mykare.tools.book_appointment")

_VALID_DOCTORS = {
    "Dr. Priya Sharma",
    "Dr. Rohan Mehta",
    "Dr. Neha Kapoor",
    "Dr. Arjun Iyer",
    "Dr. Kavita Rao",
}


async def _alternatives(doctor_name: str, around: str, count: int = 3) -> list[dict]:
    """Return up to `count` open slots near `around` with the same doctor."""

    universe = enumerate_future_slots()
    db = get_db()
    async with db.execute(
        "SELECT appointment_datetime, doctor_name FROM appointments WHERE status = 'confirmed'"
    ) as cursor:
        booked = {(row["appointment_datetime"], row["doctor_name"]) async for row in cursor}

    free = [s for s in universe if (s["datetime"], doctor_name) not in booked]

                                                                        
    later = [s for s in free if s["datetime"] >= around]
    earlier = [s for s in free if s["datetime"] < around]
    ordered = later + earlier
    return [{**slot, "doctor": doctor_name} for slot in ordered[:count]]


async def handler(
    state: AgentSessionState,
    *,
    appointment_datetime: str = "",
    doctor_name: str | None = None,
    user_phone: str | None = None,
    name: str | None = None,
    date: str | None = None,
    time: str | None = None,
    phone: str | None = None,
) -> dict:
    """Insert a confirmed appointment, returning a friendly result or alternatives."""

    await publish_tool_event(state, tool="book_appointment", status="loading")

    composed_dt = (appointment_datetime or "").strip()
    if not composed_dt and date and time:
        composed_dt = f"{date.strip()} {time.strip()}"

    if name:
        state.user_name = name or state.user_name
        state.extracted_entities["name"] = state.user_name
    if phone:
        p = normalize_phone(phone)
        if p:
            state.user_phone = p
            state.extracted_entities["phone"] = p

    phone = user_phone or state.user_phone
    if not phone:
        message = "I need your phone number first — could you share it?"
        await publish_tool_event(
            state, tool="book_appointment", status="error", message=message
        )
        return {"ok": False, "error": "no_user_identified", "message": message}

    canonical_dt = parse_user_datetime(composed_dt)
    if canonical_dt is None:
        message = (
            "I couldn't parse that date and time — could you say it as "
            "'October 5th at 3pm', for example?"
        )
        await publish_tool_event(
            state, tool="book_appointment", status="error", message=message
        )
        return {
            "ok": False,
            "error": "invalid_datetime",
            "message": message,
            "received": composed_dt,
        }

                                                            
    allowed_slots = {slot["datetime"] for slot in enumerate_future_slots()}
    if canonical_dt not in allowed_slots:
        message = (
            "That time isn't in our available slot schedule. Please pick one of the listed slots."
        )
        await publish_tool_event(
            state, tool="book_appointment", status="error", message=message
        )
        return {
            "ok": False,
            "error": "outside_slot_schedule",
            "message": message,
            "received": canonical_dt,
        }

    doctor = doctor_name or "Dr. Priya Sharma"
    if doctor not in _VALID_DOCTORS:
        message = (
            f"I don't have a doctor named {doctor}. Available doctors are "
            "Dr. Priya Sharma, Dr. Rohan Mehta, Dr. Neha Kapoor, "
            "Dr. Arjun Iyer, and Dr. Kavita Rao."
        )
        await publish_tool_event(
            state, tool="book_appointment", status="error", message=message
        )
        return {"ok": False, "error": "unknown_doctor", "message": message}

    db = get_db()
    try:
        async with db.execute(
            """
            SELECT 1 FROM appointments
            WHERE appointment_datetime = ?
              AND doctor_name = ?
              AND status = 'confirmed'
            """,
            (canonical_dt, doctor),
        ) as cursor:
            already = await cursor.fetchone()

        if already is not None:
            alternatives = await _alternatives(doctor, canonical_dt)
            await publish_tool_event(
                state,
                tool="book_appointment",
                status="error",
                message="That slot is already taken — offering alternatives.",
                result={"alternatives": alternatives},
            )
            return {
                "ok": False,
                "error": "slot_taken",
                "alternatives": alternatives,
                "message": "That slot is already booked. Here are some nearby openings.",
            }

        appointment_id = secrets.token_hex(4)
        try:
            await db.execute(
                """
                INSERT INTO appointments
                    (id, user_phone, appointment_datetime, doctor_name, status)
                VALUES (?, ?, ?, ?, 'confirmed')
                """,
                (appointment_id, phone, canonical_dt, doctor),
            )
            await db.commit()
        except aiosqlite.IntegrityError:
                                                                          
            await db.rollback()
            alternatives = await _alternatives(doctor, canonical_dt)
            await publish_tool_event(
                state,
                tool="book_appointment",
                status="error",
                message="That slot was just taken — offering alternatives.",
                result={"alternatives": alternatives},
            )
            return {
                "ok": False,
                "error": "slot_taken",
                "alternatives": alternatives,
                "message": "Someone just grabbed that slot. Try one of these.",
            }

        result = {
            "ok": True,
            "appointment_id": appointment_id,
            "confirmed_datetime": canonical_dt,
            "doctor_name": doctor,
            "message": f"Booked with {doctor} on {canonical_dt}.",
        }
        state.extracted_entities["last_booking"] = {
            "appointment_id": appointment_id,
            "datetime": canonical_dt,
            "doctor": doctor,
        }
        state.extracted_entities["intent"] = state.extracted_entities.get(
            "intent", "appointment_booking"
        )
        await publish_tool_event(
            state,
            tool="book_appointment",
            status="success",
            result={
                "appointment_id": appointment_id,
                "datetime": canonical_dt,
                "doctor": doctor,
            },
        )
        return result
    except Exception as exc:                
        logger.exception("book_appointment failed for phone=%s dt=%s", phone, canonical_dt)
        message = "Something went wrong saving the booking — let me try once more."
        await publish_tool_event(
            state, tool="book_appointment", status="error", message=message
        )
        return {
            "ok": False,
            "error": "internal_error",
            "message": message,
            "detail": str(exc),
        }
