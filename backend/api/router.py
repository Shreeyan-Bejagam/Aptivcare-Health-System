"""
Top-level API router that mounts every sub-router under `/api`.
"""

from fastapi import APIRouter

from . import appointments, health, sessions, voice_ws

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(sessions.router)
router.include_router(appointments.router)
router.include_router(voice_ws.router)
