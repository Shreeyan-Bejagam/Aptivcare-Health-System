"""
Tool: end_conversation.

Marks the session as ended, kicks off the post-call summarisation in the
background (so the agent can deliver a clean farewell while we crunch the
transcript), and persists cost metrics. Returns immediately to the LLM so
the realtime conversation isn't held up by a separate Claude round-trip.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from database.connection import get_db
from database.models import TranscriptTurn
from agent.state import AgentSessionState
from agent.llm_client import calculate_cost, summarise_call

from ._helpers import publish_tool_event

logger = logging.getLogger("mykare.tools.end_conversation")


async def _persist_summary(
    session_id: str, state: AgentSessionState
) -> None:
    """Background task: build summary + cost, write them onto the sessions row."""

    db = get_db()
    try:
        async with db.execute(
            "SELECT transcript FROM sessions WHERE id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()

        transcript_raw = row["transcript"] if row else "[]"
        try:
            transcript_list = json.loads(transcript_raw or "[]")
        except json.JSONDecodeError:
            transcript_list = []

        turns = [TranscriptTurn(**t) for t in transcript_list if isinstance(t, dict)]

        summary, usage = await summarise_call(
            turns,
            user_phone=state.user_phone,
            user_name=state.user_name,
        )

                                                                                   
        if state.user_phone:
            async with db.execute(
                """
                SELECT appointment_datetime, doctor_name
                FROM appointments
                WHERE user_phone = ? AND status = 'confirmed'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (state.user_phone,),
            ) as cursor:
                appt = await cursor.fetchone()
            if appt and appt["appointment_datetime"]:
                dt = str(appt["appointment_datetime"])
                if " " in dt:
                    date_part, time_part = dt.split(" ", 1)
                    summary.appointment_date = summary.appointment_date or date_part
                    summary.appointment_time = summary.appointment_time or time_part[:5]
                summary.doctor_name = summary.doctor_name or appt["doctor_name"]

                                                                              
        state.metrics.claude_input_tokens += usage.get("input_tokens", 0)
        state.metrics.claude_output_tokens += usage.get("output_tokens", 0)

        elapsed = (
            datetime.now(timezone.utc) - state.started_at
        ).total_seconds()
        summary.duration_seconds = round(elapsed, 2)

        cost = calculate_cost(
            deepgram_seconds=state.metrics.deepgram_seconds or elapsed,
            cartesia_chars=state.metrics.cartesia_chars,
            claude_input_tokens=state.metrics.claude_input_tokens,
            claude_output_tokens=state.metrics.claude_output_tokens,
        )

        await db.execute(
            """
            UPDATE sessions
            SET summary = ?, cost_breakdown = ?, ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (summary.model_dump_json(), cost.model_dump_json(), session_id),
        )
        await db.commit()
        logger.info("Session %s summary persisted (turns=%d).", session_id, len(turns))
    except Exception as exc:                
        logger.exception("Background summary generation failed for %s", session_id)
                                                          
        elapsed = (
            datetime.now(timezone.utc) - state.started_at
        ).total_seconds()
        fallback_summary = {
            "name": state.user_name,
            "phone": state.user_phone,
            "appointment_date": None,
            "appointment_time": None,
            "doctor_name": None,
            "intent": "Summary unavailable due to a temporary processing issue.",
            "appointments_booked": [],
            "appointments_cancelled": [],
            "appointments_modified": [],
            "preferences": [],
            "key_moments": [],
            "turn_count": state.metrics.turn_count,
            "duration_seconds": round(elapsed, 2),
            "error": str(exc),
        }
        fallback_cost = calculate_cost(
            deepgram_seconds=state.metrics.deepgram_seconds or elapsed,
            cartesia_chars=state.metrics.cartesia_chars,
            claude_input_tokens=state.metrics.claude_input_tokens,
            claude_output_tokens=state.metrics.claude_output_tokens,
        )
        try:
            await db.execute(
                """
                UPDATE sessions
                SET summary = ?, cost_breakdown = ?, ended_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(fallback_summary), fallback_cost.model_dump_json(), session_id),
            )
            await db.commit()
        except Exception:                
            logger.exception("Fallback summary persistence failed for %s", session_id)


async def handler(state: AgentSessionState) -> dict:
    """Mark the session ended and schedule the summary write."""

    await publish_tool_event(state, tool="end_conversation", status="loading")

    if state.ended:
        return {"ok": True, "already_ended": True}

    state.ended = True
    asyncio.create_task(_persist_summary(state.session_id, state))

    await publish_tool_event(
        state,
        tool="end_conversation",
        status="success",
        result={"session_id": state.session_id},
    )
    return {
        "ok": True,
        "session_id": state.session_id,
        "message": "Saying goodbye and saving the call summary.",
    }
