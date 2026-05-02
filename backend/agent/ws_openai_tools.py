"""
OpenAI tool-calling loop for the WebSocket voice transport.

Shares the same SQLite-backed tool handlers as the LiveKit agent, but drives
them from `chat.completions` instead of the LiveKit `FunctionContext` wrapper.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI

from agent.state import AgentSessionState
from agent.system_prompt import SYSTEM_PROMPT
from agent.tools import (
    book_appointment,
    cancel_appointment,
    end_conversation,
    fetch_slots,
    identify_user,
    modify_appointment,
    retrieve_appointments,
)
from config import settings

logger = logging.getLogger("mykare.ws_agent")

_MAX_TOOL_ROUNDS = 12
_BOOK_CONFIRM_RE = re.compile(
    r"\b(yes|yeah|yep|go ahead|go-ahead|book it|book that|confirm|proceed)\b",
    re.IGNORECASE,
)

_OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "identify_user",
            "description": "Identify the patient by phone (unique id). Call before booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["phone_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_slots",
            "description": "Fetch available appointment slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_preference": {"type": "string"},
                    "doctor_name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book after verbal confirmation. Use datetime OR date+time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_datetime": {"type": "string"},
                    "doctor_name": {"type": "string"},
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_appointments",
            "description": "List confirmed appointments for the identified patient.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel by appointment id.",
            "parameters": {
                "type": "object",
                "properties": {"appointment_id": {"type": "string"}},
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_appointment",
            "description": "Reschedule an appointment atomically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "new_datetime": {"type": "string"},
                },
                "required": ["appointment_id", "new_datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_conversation",
            "description": "End the call once the patient is done.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


async def _dispatch_tool(name: str, args: dict[str, Any], state: AgentSessionState) -> dict:
    if name == "identify_user":
        return await identify_user.handler(
            state,
            phone=args.get("phone_number") or args.get("phone", ""),
            name=args.get("name") or None,
        )
    if name == "fetch_slots":
        return await fetch_slots.handler(
            state,
            date_preference=args.get("date_preference") or None,
            doctor_name=args.get("doctor_name") or None,
        )
    if name == "book_appointment":
        return await book_appointment.handler(
            state,
            appointment_datetime=args.get("appointment_datetime") or "",
            doctor_name=args.get("doctor_name") or None,
            name=args.get("name") or None,
            phone=args.get("phone") or None,
            date=args.get("date") or None,
            time=args.get("time") or None,
        )
    if name == "retrieve_appointments":
        return await retrieve_appointments.handler(state)
    if name == "cancel_appointment":
        return await cancel_appointment.handler(
            state, appointment_id=args.get("appointment_id", "")
        )
    if name == "modify_appointment":
        return await modify_appointment.handler(
            state,
            appointment_id=args.get("appointment_id", ""),
            new_datetime=args.get("new_datetime", ""),
        )
    if name == "end_conversation":
        return await end_conversation.handler(state)
    return {"ok": False, "error": "unknown_tool", "tool": name}


def _pick_slot_from_last_options(state: AgentSessionState, user_text: str) -> dict[str, Any] | None:
    slots = state.extracted_entities.get("last_available_slots")
    if not isinstance(slots, list) or not slots:
        return None

    text = user_text.lower()
                                                           
    hour_map = {
        "nine": "09:", "9": "09:",
        "ten": "10:", "10": "10:",
        "eleven": "11:", "11": "11:",
        "twelve": "12:", "12": "12:",
        "one": "13:", "1": "13:",
        "two": "14:", "2": "14:",
        "three": "15:", "3": "15:",
        "four": "16:", "4": "16:",
    }
    for token, hh in hour_map.items():
        if token in text:
            for slot in slots:
                if isinstance(slot, dict) and hh in str(slot.get("datetime", "")):
                    return slot

                                                                  
    for slot in slots:
        if isinstance(slot, dict) and slot.get("datetime"):
            return slot
    return None


async def run_ws_agent_turn(state: AgentSessionState, user_text: str) -> tuple[str, bool]:
    """Run one user utterance through the tool-capable assistant.

    Returns (assistant_spoken_text, call_ended_via_end_conversation_tool).
    """

    state.conversation_history.append({"role": "user", "content": user_text})
                                                                         
                                                                       
    if _BOOK_CONFIRM_RE.search(user_text or ""):
        slot = _pick_slot_from_last_options(state, user_text)
        if slot and state.user_phone:
            result = await book_appointment.handler(
                state,
                appointment_datetime=str(slot.get("datetime", "")),
                doctor_name=str(slot.get("doctor") or state.extracted_entities.get("last_doctor") or ""),
            )
            if result.get("ok"):
                text = (
                    f"Done — your appointment is confirmed for "
                    f"{result.get('confirmed_datetime')} with {result.get('doctor_name')}."
                )
            else:
                text = result.get("message") or "I couldn't complete that booking right now."
            state.conversation_history.append({"role": "assistant", "content": text})
            return text, False

    today = datetime.now().strftime("%A %d %B %Y")
    entity_blob = json.dumps(state.extracted_entities, ensure_ascii=False)
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\nToday's date is {today}.\n"
                f"Structured memory (may be empty): {entity_blob}"
            ),
        },
        *[
            {"role": m["role"], "content": m["content"]}
            for m in state.conversation_history
            if m.get("content")
        ],
    ]

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    call_ended = False

    for _ in range(_MAX_TOOL_ROUNDS):
        response = await client.chat.completions.create(
            model=settings.OPENAI_LLM_MODEL,
            temperature=0.3,
            messages=messages,
            tools=_OPENAI_TOOLS,
            tool_choice="auto",
        )
        choice = response.choices[0].message
        usage = response.usage
        if usage:
            state.metrics.claude_input_tokens += int(usage.prompt_tokens or 0)
            state.metrics.claude_output_tokens += int(usage.completion_tokens or 0)

        if choice.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in choice.tool_calls
                    ],
                }
            )
            for tc in choice.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                try:
                    result = await _dispatch_tool(name, args, state)
                except Exception as exc:                
                    logger.exception("Tool %s failed", name)
                    result = {"ok": False, "error": "tool_exception", "detail": str(exc)}
                if name == "end_conversation" and result.get("ok"):
                    call_ended = True
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            continue

        text = (choice.content or "").strip() or "Okay."
        state.conversation_history.append({"role": "assistant", "content": text})
        return text, call_ended

    fallback = "I'm having trouble with that — could you say it once more?"
    state.conversation_history.append({"role": "assistant", "content": fallback})
    return fallback, call_ended
