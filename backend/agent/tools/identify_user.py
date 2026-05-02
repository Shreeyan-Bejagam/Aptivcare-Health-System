"""
Tool: identify_user.

Normalises the spoken phone number, looks the user up in the `users` table,
upserts on first contact, and stores the canonical phone on the agent session
state so subsequent tools can rely on it.
"""

from __future__ import annotations

import logging

from database.connection import get_db
from agent.state import AgentSessionState

from ._helpers import normalize_phone, publish_tool_event

logger = logging.getLogger("mykare.tools.identify_user")


async def handler(
    state: AgentSessionState,
    *,
    phone: str,
    name: str | None = None,
) -> dict:
    """Look up or create a user record and bind the canonical phone to the session."""

    await publish_tool_event(state, tool="identify_user", status="loading")

    canonical = normalize_phone(phone)
    if canonical is None:
        result = {
            "ok": False,
            "error": "invalid_phone",
            "message": (
                "I couldn't parse that as a 10-digit phone number — "
                "could you say it again, digit by digit?"
            ),
        }
        await publish_tool_event(
            state, tool="identify_user", status="error", message=result["message"]
        )
        return result

    db = get_db()
    try:
        async with db.execute(
            "SELECT phone, name FROM users WHERE phone = ?",
            (canonical,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            await db.execute(
                "INSERT INTO users (phone, name) VALUES (?, ?)",
                (canonical, name),
            )
            await db.commit()
            is_returning = False
            stored_name = name
        else:
            is_returning = True
            stored_name = row["name"]
                                                                                
            if name and not stored_name:
                await db.execute(
                    "UPDATE users SET name = ? WHERE phone = ?",
                    (name, canonical),
                )
                await db.commit()
                stored_name = name

                                                                            
        state.user_phone = canonical
        state.user_name = stored_name
        state.is_returning_user = is_returning
        state.extracted_entities["phone"] = canonical
        if stored_name:
            state.extracted_entities["name"] = stored_name

                                                  
        await db.execute(
            "UPDATE sessions SET user_phone = ? WHERE id = ?",
            (canonical, state.session_id),
        )
        await db.commit()

        greeting = (
            f"Welcome back {stored_name}!"
            if is_returning and stored_name
            else "Welcome to AptivCare."
        )
        result = {
            "ok": True,
            "user_id": canonical,
            "name": stored_name,
            "is_returning_user": is_returning,
            "greeting": greeting,
        }
        await publish_tool_event(
            state,
            tool="identify_user",
            status="success",
            result={
                "phone": canonical,
                "name": stored_name,
                "is_returning": is_returning,
            },
        )
        return result
    except Exception as exc:                
        logger.exception("identify_user failed for raw=%r", phone)
        message = "Something went wrong looking up your details — let me try once more."
        await publish_tool_event(
            state, tool="identify_user", status="error", message=message
        )
        return {"ok": False, "error": "internal_error", "message": message, "detail": str(exc)}
