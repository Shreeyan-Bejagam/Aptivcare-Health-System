"""
Standalone OpenAI client used for the *post-call summarisation* step.

The realtime turn-by-turn LLM is provided by the LiveKit OpenAI plugin. Once
the call ends we still need a one-off model call that produces a structured
JSON summary; that's what this module is for.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from config import settings
from database.models import CostBreakdown, SessionSummary, TranscriptTurn

logger = logging.getLogger("mykare.llm")


_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "description": "Patient's name if mentioned."},
        "phone": {"type": "string", "description": "10-digit phone, no formatting."},
        "appointment_date": {"type": "string", "description": "Booked appointment date YYYY-MM-DD, if any."},
        "appointment_time": {"type": "string", "description": "Booked appointment time HH:MM, if any."},
        "doctor_name": {"type": "string", "description": "Doctor name for the confirmed appointment, if any."},
        "intent": {
            "type": "string",
            "description": "1-2 sentence plain-English summary of why they called.",
        },
        "appointments_booked": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "datetime": {"type": "string"},
                    "doctor": {"type": "string"},
                },
                "required": ["datetime", "doctor"],
            },
        },
        "appointments_cancelled": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "datetime": {"type": "string"},
                    "doctor": {"type": "string"},
                },
                "required": ["datetime", "doctor"],
            },
        },
        "appointments_modified": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "from_datetime": {"type": "string"},
                    "to_datetime": {"type": "string"},
                    "doctor": {"type": "string"},
                },
                "required": ["from_datetime", "to_datetime", "doctor"],
            },
        },
        "preferences": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Anything worth remembering for next time.",
        },
        "key_moments": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-4 short bullet points capturing conversation highlights.",
        },
    },
    "required": ["intent"],
}


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def summarise_call(
    transcript: list[TranscriptTurn],
    *,
    user_phone: str | None,
    user_name: str | None,
) -> tuple[SessionSummary, dict[str, int]]:
    """Ask OpenAI for a structured summary; return parsed object + token usage."""

    if not transcript:
        return (
            SessionSummary(
                phone=user_phone, name=user_name, intent="No conversation captured."
            ),
            {"input_tokens": 0, "output_tokens": 0},
        )

    formatted = "\n".join(f"{t.role.upper()}: {t.content}" for t in transcript)

    system = (
        "You are reviewing a transcript from a phone call to a healthcare clinic's "
        "front-desk AI. Return only strict JSON matching the required schema. "
        "Be terse and factual."
    )

    user_message = (
        f"Patient identifier on file: phone={user_phone or 'unknown'}, "
        f"name={user_name or 'unknown'}.\n\n"
        f"Transcript:\n{formatted}"
    )

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_SUMMARY_MODEL,
        max_tokens=1024,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "call_summary",
                "schema": _SUMMARY_SCHEMA,
                "strict": False,
            },
        },
    )

    summary_payload: dict[str, Any] = {}
    content = response.choices[0].message.content if response.choices else None
    if content:
        try:
            summary_payload = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("OpenAI summary response was not valid JSON.")

    if not summary_payload:
                                                           
        logger.warning("OpenAI did not return a valid summary payload.")
        summary_payload = {"intent": "Summary unavailable."}

    summary_payload.setdefault("phone", user_phone)
    summary_payload.setdefault("name", user_name)

    summary = SessionSummary(
        name=summary_payload.get("name") or user_name,
        phone=summary_payload.get("phone") or user_phone,
        appointment_date=summary_payload.get("appointment_date") or None,
        appointment_time=summary_payload.get("appointment_time") or None,
        doctor_name=summary_payload.get("doctor_name") or None,
        intent=summary_payload.get("intent", ""),
        appointments_booked=summary_payload.get("appointments_booked", []) or [],
        appointments_cancelled=summary_payload.get("appointments_cancelled", []) or [],
        appointments_modified=summary_payload.get("appointments_modified", []) or [],
        preferences=summary_payload.get("preferences", []) or [],
        key_moments=summary_payload.get("key_moments", []) or [],
        turn_count=len(transcript),
    )

    usage = {
        "input_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
        "output_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
    }
    return summary, usage


def calculate_cost(
    *,
    deepgram_seconds: float,
    cartesia_chars: int,
    claude_input_tokens: int,
    claude_output_tokens: int,
) -> CostBreakdown:
    """Combine running metrics with the configured per-unit prices."""

    deepgram_minutes = deepgram_seconds / 60.0
    deepgram_usd = deepgram_minutes * settings.DEEPGRAM_PRICE_PER_MIN
    cartesia_usd = cartesia_chars * settings.CARTESIA_PRICE_PER_CHAR
    claude_usd = (
        claude_input_tokens / 1_000_000 * settings.OPENAI_INPUT_PRICE_PER_MTOK
        + claude_output_tokens / 1_000_000 * settings.OPENAI_OUTPUT_PRICE_PER_MTOK
    )
    return CostBreakdown(
        deepgram_minutes=round(deepgram_minutes, 4),
        deepgram_usd=round(deepgram_usd, 6),
        cartesia_chars=cartesia_chars,
        cartesia_usd=round(cartesia_usd, 6),
        claude_input_tokens=claude_input_tokens,
        claude_output_tokens=claude_output_tokens,
        claude_usd=round(claude_usd, 6),
        total_usd=round(deepgram_usd + cartesia_usd + claude_usd, 6),
    )
