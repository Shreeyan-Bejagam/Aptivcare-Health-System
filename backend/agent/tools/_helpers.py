"""
Shared helpers used by more than one tool: phone normalisation, slot
enumeration, and the small JSON publisher that emits `tool_event` data
messages into the LiveKit room so the frontend can render its live tool feed.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Iterable, Optional

from livekit import rtc

from config import settings

logger = logging.getLogger("mykare.tools.helpers")


                                                                              

                                  
                  
               
               
              
                                      
_DIGITS_ONLY = re.compile(r"\D+")
_NUMBER_WORD_TO_DIGIT = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "two": "2",
    "to": "2",
    "too": "2",
    "three": "3",
    "four": "4",
    "for": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "ate": "8",
    "nine": "9",
}
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
    "twenty first": 21,
    "twenty-first": 21,
    "twenty second": 22,
    "twenty-second": 22,
    "twenty third": 23,
    "twenty-third": 23,
    "twenty fourth": 24,
    "twenty-fourth": 24,
    "twenty fifth": 25,
    "twenty-fifth": 25,
    "twenty sixth": 26,
    "twenty-sixth": 26,
    "twenty seventh": 27,
    "twenty-seventh": 27,
    "twenty eighth": 28,
    "twenty-eighth": 28,
    "twenty ninth": 29,
    "twenty-ninth": 29,
    "thirtieth": 30,
    "thirty first": 31,
    "thirty-first": 31,
}


def normalize_phone(raw: str) -> Optional[str]:
    """Return a canonical 10-digit phone number, or None if `raw` is invalid."""

    if raw is None:
        return None

    text = str(raw).strip()
    digits = _DIGITS_ONLY.sub("", text)
    if len(digits) < 10:
                                                                       
        spoken = text.lower().replace("-", " ")
        tokens = [tok for tok in re.split(r"\s+", spoken) if tok]
        spoken_digits = "".join(_NUMBER_WORD_TO_DIGIT.get(tok, "") for tok in tokens)
        if len(spoken_digits) >= len(digits):
            digits = spoken_digits

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) != 10 or not digits.isdigit():
        return None
    return digits


                                                                              


def enumerate_future_slots(
    horizon_days: Optional[int] = None,
) -> list[dict[str, str]]:
    """Build the universe of bookable slots for the configured horizon.

    Each entry is `{datetime: ISO-8601, display_label: human, time: HH:MM, date: YYYY-MM-DD}`.
    The clinic is closed on Sundays (weekday == 6).
    """

    horizon = horizon_days if horizon_days is not None else settings.SLOT_HORIZON_DAYS
    today = datetime.now().date()
    out: list[dict[str, str]] = []

    for day_offset in range(horizon):
        day = today + timedelta(days=day_offset)
        if day.weekday() == 6:                          
            continue
        for hhmm in settings.time_slots:
            hour, minute = (int(part) for part in hhmm.split(":"))
            slot_dt = datetime(day.year, day.month, day.day, hour, minute)

                                                            
            if day == today and slot_dt <= datetime.now():
                continue

            out.append(
                {
                    "datetime": slot_dt.strftime("%Y-%m-%d %H:%M"),
                    "date": slot_dt.strftime("%Y-%m-%d"),
                    "time": hhmm,
                    "display_label": slot_dt.strftime("%A %d %b at %I:%M %p").lstrip("0"),
                }
            )
    return out


def parse_user_datetime(value: str) -> Optional[str]:
    """Best-effort parsing of a datetime string into the canonical 'YYYY-MM-DD HH:MM' form.

    Accepts ISO-8601, 'YYYY-MM-DD HH:MM', and a couple of forgiving variants
    that the LLM might emit. Returns None if nothing matches.
    """

    if not value:
        return None
    candidate = value.strip().replace("T", " ")

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %I %p",
        "%d %B %Y %I:%M %p",
        "%d %B %Y %I %p",
        "%B %d %Y %I:%M %p",
        "%B %d %Y %I %p",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue

    text = candidate.lower()
    text = (
        text.replace(",", " ")
        .replace("  ", " ")
        .replace("a.m.", "am")
        .replace("p.m.", "pm")
        .replace("a.m", "am")
        .replace("p.m", "pm")
    )

                                                               
    base_day = datetime.now().date()
    target_day = None
    if "tomorrow" in text:
        target_day = base_day + timedelta(days=1)
    elif "today" in text:
        target_day = base_day
    else:
                                                         
        md = re.search(
            r"\b(\d{1,2}(?:st|nd|rd|th)?|[a-z]+(?:[- ][a-z]+)?)\s*(?:of\s+)?"
            r"(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\b",
            text,
        )
        if not md:
            md = re.search(
                r"\b(january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\s+"
                r"(\d{1,2}(?:st|nd|rd|th)?|[a-z]+(?:[- ][a-z]+)?)\b",
                text,
            )
            if md:
                month_word = md.group(1)
                day_token = md.group(2)
            else:
                month_word = ""
                day_token = ""
        else:
            day_token = md.group(1)
            month_word = md.group(2)

        if month_word and day_token:
            day_num = _ORDINAL_WORDS.get(day_token.strip())
            if day_num is None:
                digit_match = re.match(r"(\d{1,2})", day_token.strip())
                if digit_match:
                    day_num = int(digit_match.group(1))
            month_num = _MONTHS.get(month_word.strip())
            if day_num and month_num:
                year = base_day.year
                year_match = re.search(r"\b(20\d{2})\b", text)
                if year_match:
                    year = int(year_match.group(1))
                try:
                    dt = datetime(year, month_num, day_num)
                    if dt.date() < base_day and not year_match:
                        dt = datetime(year + 1, month_num, day_num)
                    target_day = dt.date()
                except ValueError:
                    target_day = None

                                                                   
    hm24 = None
    if "noon" in text:
        hm24 = "12:00"
    elif "midnight" in text:
        hm24 = "00:00"
    else:
        m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b", text)
        if m:
            hour = int(m.group(1)) % 12
            minute = int(m.group(2))
            if m.group(3) == "pm":
                hour += 12
            hm24 = f"{hour:02d}:{minute:02d}"
        if hm24 is None:
            m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", text)
            if m:
                hour = int(m.group(1)) % 12
                if m.group(2) == "pm":
                    hour += 12
                hm24 = f"{hour:02d}:00"
        if hm24 is None:
            m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(am|pm)\b", text)
            if m:
                words = {
                    "one": 1,
                    "two": 2,
                    "three": 3,
                    "four": 4,
                    "five": 5,
                    "six": 6,
                    "seven": 7,
                    "eight": 8,
                    "nine": 9,
                    "ten": 10,
                    "eleven": 11,
                    "twelve": 12,
                }
                hour = words[m.group(1)] % 12
                if m.group(2) == "pm":
                    hour += 12
                hm24 = f"{hour:02d}:00"

    if target_day and hm24:
        return f"{target_day.strftime('%Y-%m-%d')} {hm24}"
    return None


                                                                              


async def publish_tool_event(
    state: Any,
    *,
    tool: str,
    status: str,
    result: Any = None,
    message: Optional[str] = None,
) -> None:
    """Send a `tool_event` to LiveKit data channel and/or the WebSocket bridge.

    `state` is an `AgentSessionState` with optional `.room` and `.tool_emit`.
    """

    payload: dict[str, Any] = {
        "type": "tool_event",
        "tool": tool,
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if result is not None:
        payload["result"] = result
    if message is not None:
        payload["message"] = message

    emit: Optional[Callable[[dict[str, Any]], Awaitable[None]]] = getattr(
        state, "tool_emit", None
    )
    if emit is not None:
        try:
            await emit(payload)
        except Exception:                
            logger.exception("tool_emit failed for %s", tool)

    room: Optional[rtc.Room] = getattr(state, "room", None)
    if room is None or room.local_participant is None:
        return

    try:
        await room.local_participant.publish_data(
            json.dumps(payload).encode("utf-8"),
            reliable=True,
            topic="tool_event",
        )
    except Exception:                              
        logger.exception("Failed to publish tool_event for %s", tool)


def take_first_n(seq: Iterable[Any], n: int) -> list[Any]:
    """Tiny helper used by alternatives lists; avoids importing islice everywhere."""

    out: list[Any] = []
    for item in seq:
        if len(out) >= n:
            break
        out.append(item)
    return out
