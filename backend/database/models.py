"""
Pydantic models that describe the shape of database rows and the JSON payloads
the API exposes. Keeping these in one place gives us:

  * Clear, typed conversion from `aiosqlite.Row` -> serialisable dict.
  * A single source of truth for field names that both the agent tools and the
    REST endpoints consume.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    phone: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None


class Appointment(BaseModel):
    id: str
    user_phone: str
    appointment_datetime: str
    doctor_name: str = "Dr. Priya Sharma"
    status: Literal["confirmed", "cancelled"] = "confirmed"
    created_at: Optional[datetime] = None


class TranscriptTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str


class CostBreakdown(BaseModel):
    deepgram_minutes: float = 0.0
    deepgram_usd: float = 0.0
    cartesia_chars: int = 0
    cartesia_usd: float = 0.0
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    claude_usd: float = 0.0
    total_usd: float = 0.0


class SessionSummary(BaseModel):
    """Structured output of the post-call summarisation step."""

    name: Optional[str] = None
    phone: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    doctor_name: Optional[str] = None
    intent: str = ""
    appointments_booked: List[dict] = Field(default_factory=list)
    appointments_cancelled: List[dict] = Field(default_factory=list)
    appointments_modified: List[dict] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    key_moments: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    turn_count: int = 0


class Session(BaseModel):
    id: str
    user_phone: Optional[str] = None
    transcript: List[TranscriptTurn] = Field(default_factory=list)
    summary: Optional[SessionSummary] = None
    cost_breakdown: Optional[CostBreakdown] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
