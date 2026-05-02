"""
Tool registry — builds the LiveKit `FunctionContext` the LLM uses to call tools.

We define each tool as a method on `MykareToolContext` decorated with
`@llm.ai_callable()`. The decorator inspects type hints (including `Annotated[...]`
metadata) to build the JSON schema that's sent to Claude. Each method delegates
to the corresponding `handler(...)` in its own file — keeping tool logic out of
the registry makes the handlers easy to unit-test in isolation.

Each tool method returns a JSON-encoded string. LiveKit forwards that to Claude
as the tool result; the assistant turns it into natural-language replies.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from livekit.agents import llm

from agent.state import AgentSessionState

from . import (
    book_appointment,
    cancel_appointment,
    end_conversation,
    fetch_slots,
    identify_user,
    modify_appointment,
    retrieve_appointments,
)

logger = logging.getLogger("mykare.tools.registry")


def _to_string(payload: dict) -> str:
    """Serialise a tool result to the string form LiveKit expects."""
    return json.dumps(payload, ensure_ascii=False)


class MykareToolContext(llm.FunctionContext):
    """All seven tools, exposed as @ai_callable methods bound to a session state."""

    def __init__(self, state: AgentSessionState) -> None:
        super().__init__()
        self.state = state

    @llm.ai_callable(
        description=(
            "Identify the patient by their phone number. Always call this before any "
            "booking, cancellation, or modification. Pass the phone exactly as the "
            "user said it; the tool normalises it."
        )
    )
    async def identify_user(
        self,
        phone_number: Annotated[
            str,
            llm.TypeInfo(
                description="The patient's phone number (unique id), any common Indian format."
            ),
        ],
        name: Annotated[
            str,
            llm.TypeInfo(description="The patient's name, if they've given it. Optional."),
        ] = "",
    ) -> str:
        result = await identify_user.handler(
            self.state, phone=phone_number, name=(name or None)
        )
        return _to_string(result)

    @llm.ai_callable(
        description=(
            "Fetch available appointment slots from the clinic calendar. "
            "Call this before quoting any times to the patient."
        )
    )
    async def fetch_slots(
        self,
        date_preference: Annotated[
            str,
            llm.TypeInfo(
                description=(
                    "Optional date filter in YYYY-MM-DD format. Empty string means no filter."
                )
            ),
        ] = "",
        doctor_name: Annotated[
            str,
            llm.TypeInfo(
                description=(
                    "Doctor name. Supported: Dr. Priya Sharma, Dr. Rohan Mehta, "
                    "Dr. Neha Kapoor, Dr. Arjun Iyer, Dr. Kavita Rao. "
                    "Defaults to Dr. Priya Sharma."
                )
            ),
        ] = "",
    ) -> str:
        result = await fetch_slots.handler(
            self.state,
            date_preference=(date_preference or None),
            doctor_name=(doctor_name or None),
        )
        return _to_string(result)

    @llm.ai_callable(
        description=(
            "Book an appointment for the identified patient. Confirm date, time, "
            "and doctor with the patient before calling this."
        )
    )
    async def book_appointment(
        self,
        appointment_datetime: Annotated[
            str,
            llm.TypeInfo(
                description=(
                    "Appointment date+time in 'YYYY-MM-DD HH:MM' 24-hour form. "
                    "Leave empty if passing date + time separately."
                )
            ),
        ] = "",
        doctor_name: Annotated[
            str,
            llm.TypeInfo(
                description=(
                    "Doctor's full name (e.g. 'Dr. Priya Sharma'). "
                    "Defaults to Dr. Priya Sharma if empty."
                )
            ),
        ] = "",
        name: Annotated[
            str,
            llm.TypeInfo(description="Patient full name if not already on file."),
        ] = "",
        phone: Annotated[
            str,
            llm.TypeInfo(description="10-digit phone if not already identified."),
        ] = "",
        date: Annotated[
            str,
            llm.TypeInfo(description="Date YYYY-MM-DD if not using appointment_datetime."),
        ] = "",
        time: Annotated[
            str,
            llm.TypeInfo(description="Time HH:MM 24h if not using appointment_datetime."),
        ] = "",
    ) -> str:
        result = await book_appointment.handler(
            self.state,
            appointment_datetime=appointment_datetime,
            doctor_name=(doctor_name or None),
            name=(name or None),
            phone=(phone or None),
            date=(date or None),
            time=(time or None),
        )
        return _to_string(result)

    @llm.ai_callable(
        description="List the currently confirmed appointments for the identified patient."
    )
    async def retrieve_appointments(self) -> str:
        result = await retrieve_appointments.handler(self.state)
        return _to_string(result)

    @llm.ai_callable(
        description=(
            "Cancel an existing appointment by id. The id is the one returned by "
            "retrieve_appointments or book_appointment."
        )
    )
    async def cancel_appointment(
        self,
        appointment_id: Annotated[
            str, llm.TypeInfo(description="The 8-character appointment id.")
        ],
    ) -> str:
        result = await cancel_appointment.handler(
            self.state, appointment_id=appointment_id
        )
        return _to_string(result)

    @llm.ai_callable(
        description=(
            "Reschedule an existing appointment to a new datetime in a single atomic "
            "operation. Use this instead of calling cancel + book separately."
        )
    )
    async def modify_appointment(
        self,
        appointment_id: Annotated[
            str, llm.TypeInfo(description="The 8-character appointment id to reschedule.")
        ],
        new_datetime: Annotated[
            str,
            llm.TypeInfo(description="New appointment time in 'YYYY-MM-DD HH:MM' form."),
        ],
    ) -> str:
        result = await modify_appointment.handler(
            self.state,
            appointment_id=appointment_id,
            new_datetime=new_datetime,
        )
        return _to_string(result)

    @llm.ai_callable(
        description=(
            "End the call. Call this exactly once when the patient says goodbye, "
            "is done, or asks to hang up. After this, do not call any other tools."
        )
    )
    async def end_conversation(self) -> str:
        result = await end_conversation.handler(self.state)
        return _to_string(result)


def build(state: AgentSessionState) -> MykareToolContext:
    """Convenience factory used by the agent entrypoint."""
    return MykareToolContext(state)
