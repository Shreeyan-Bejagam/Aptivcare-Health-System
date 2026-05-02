"""
Per-call agent session state.

A fresh `AgentSessionState` is constructed when the LiveKit agent worker accepts
a new room. It carries everything tool handlers need: the database session row
they're meant to mutate, the LiveKit room handle for publishing data messages,
and a small running tally of metrics used to compute the post-call cost.

Keeping this in one place (instead of stuffing it into module globals) means
multiple concurrent calls on the same worker process don't step on each other.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from livekit import rtc


@dataclass
class CallMetrics:
    """Lightweight running totals for cost calculation at end of call."""

    deepgram_seconds: float = 0.0
    cartesia_chars: int = 0
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    turn_count: int = 0


@dataclass
class AgentSessionState:
    session_id: str
    room: Optional[rtc.Room] = None
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    is_returning_user: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended: bool = False
    metrics: CallMetrics = field(default_factory=CallMetrics)
                                                                            
                                                                       
    transcript_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
                                                                        
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    extracted_entities: dict[str, Any] = field(default_factory=dict)
                                                                                          
    tool_emit: Optional[Callable[[dict[str, Any]], Awaitable[None]]] = None
