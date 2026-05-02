"""
Appointments REST API.

A small administrative surface alongside the voice flow — these endpoints exist
so the frontend's summary page (and any future ops dashboard) can list and
manage bookings without going through the voice agent. All inputs go through
Pydantic validation; all SQL is parameterised.
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional

import aiosqlite
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from agent.tools._helpers import normalize_phone, parse_user_datetime
from database.connection import get_db

logger = logging.getLogger("mykare.api.appointments")

router = APIRouter(prefix="/appointments", tags=["appointments"])


_VALID_DOCTORS = {"Dr. Priya Sharma", "Dr. Rohan Mehta"}


class AppointmentRecord(BaseModel):
    id: str
    user_phone: str
    appointment_datetime: str
    doctor_name: str
    status: str
    created_at: Optional[str] = None


class CreateAppointmentBody(BaseModel):
    user_phone: str = Field(..., description="10-digit phone, any reasonable format.")
    appointment_datetime: str
    doctor_name: str = "Dr. Priya Sharma"

    @field_validator("user_phone")
    @classmethod
    def _normalise_phone(cls, value: str) -> str:
        canonical = normalize_phone(value)
        if canonical is None:
            raise ValueError("Phone must normalise to 10 digits.")
        return canonical

    @field_validator("appointment_datetime")
    @classmethod
    def _normalise_datetime(cls, value: str) -> str:
        canonical = parse_user_datetime(value)
        if canonical is None:
            raise ValueError("appointment_datetime must be in 'YYYY-MM-DD HH:MM' form.")
        return canonical

    @field_validator("doctor_name")
    @classmethod
    def _validate_doctor(cls, value: str) -> str:
        if value not in _VALID_DOCTORS:
            raise ValueError(f"doctor_name must be one of {sorted(_VALID_DOCTORS)}.")
        return value


class UpdateAppointmentBody(BaseModel):
    appointment_datetime: Optional[str] = None
    status: Optional[str] = None

    @field_validator("appointment_datetime")
    @classmethod
    def _normalise_datetime(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        canonical = parse_user_datetime(value)
        if canonical is None:
            raise ValueError("appointment_datetime must be in 'YYYY-MM-DD HH:MM' form.")
        return canonical

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if value not in {"confirmed", "cancelled"}:
            raise ValueError("status must be 'confirmed' or 'cancelled'.")
        return value


@router.get("", response_model=list[AppointmentRecord])
async def list_appointments(
    phone: str = Query(..., description="Patient phone number, any common format."),
    include_cancelled: bool = Query(False),
) -> list[AppointmentRecord]:
    canonical = normalize_phone(phone)
    if canonical is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="phone must normalise to 10 digits.",
        )

    db = get_db()
    if include_cancelled:
        sql = (
            "SELECT id, user_phone, appointment_datetime, doctor_name, status, created_at "
            "FROM appointments WHERE user_phone = ? "
            "ORDER BY appointment_datetime ASC"
        )
    else:
        sql = (
            "SELECT id, user_phone, appointment_datetime, doctor_name, status, created_at "
            "FROM appointments WHERE user_phone = ? AND status = 'confirmed' "
            "ORDER BY appointment_datetime ASC"
        )
    async with db.execute(sql, (canonical,)) as cursor:
        rows = await cursor.fetchall()
    return [AppointmentRecord(**dict(row)) for row in rows]


@router.post("", response_model=AppointmentRecord, status_code=status.HTTP_201_CREATED)
async def create_appointment(body: CreateAppointmentBody) -> AppointmentRecord:
    db = get_db()
    appt_id = secrets.token_hex(4)

                                                           
    await db.execute(
        "INSERT OR IGNORE INTO users (phone) VALUES (?)", (body.user_phone,)
    )
    try:
        await db.execute(
            """
            INSERT INTO appointments
                (id, user_phone, appointment_datetime, doctor_name, status)
            VALUES (?, ?, ?, ?, 'confirmed')
            """,
            (appt_id, body.user_phone, body.appointment_datetime, body.doctor_name),
        )
        await db.commit()
    except aiosqlite.IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot is already booked.",
        ) from exc

    return AppointmentRecord(
        id=appt_id,
        user_phone=body.user_phone,
        appointment_datetime=body.appointment_datetime,
        doctor_name=body.doctor_name,
        status="confirmed",
    )


@router.patch("/{appointment_id}", response_model=AppointmentRecord)
async def update_appointment(
    appointment_id: str, body: UpdateAppointmentBody
) -> AppointmentRecord:
    db = get_db()
    async with db.execute(
        "SELECT id, user_phone, appointment_datetime, doctor_name, status, created_at "
        "FROM appointments WHERE id = ?",
        (appointment_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    new_dt = body.appointment_datetime or row["appointment_datetime"]
    new_status = body.status or row["status"]

    try:
        await db.execute(
            "UPDATE appointments SET appointment_datetime = ?, status = ? WHERE id = ?",
            (new_dt, new_status, appointment_id),
        )
        await db.commit()
    except aiosqlite.IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target slot is already booked.",
        ) from exc

    return AppointmentRecord(
        id=appointment_id,
        user_phone=row["user_phone"],
        appointment_datetime=new_dt,
        doctor_name=row["doctor_name"],
        status=new_status,
        created_at=row["created_at"],
    )


@router.delete("/{appointment_id}", status_code=status.HTTP_200_OK)
async def cancel_appointment(appointment_id: str) -> dict:
    db = get_db()
    async with db.execute(
        "SELECT id FROM appointments WHERE id = ?", (appointment_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    await db.execute(
        "UPDATE appointments SET status = 'cancelled' WHERE id = ?",
        (appointment_id,),
    )
    await db.commit()
    return {"cancelled": True, "appointment_id": appointment_id}
