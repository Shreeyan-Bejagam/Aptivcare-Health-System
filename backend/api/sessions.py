"""Session and summary HTTP endpoints."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

import httpx
from aiohttp.client_exceptions import ContentTypeError
from fastapi import APIRouter, HTTPException, Request, status
from livekit import api as lk_api
from pydantic import BaseModel, Field

from config import settings
from database.connection import get_db
from utils.debug_runtime import debug_log
from utils.rate_limiter import limiter

logger = logging.getLogger("mykare.api.sessions")

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionResponse(BaseModel):
    session_id: str
    livekit_token: str = Field(..., description="JWT for the LiveKit room.")
    livekit_url: str
    room: str


class WebSocketVoiceSessionResponse(BaseModel):
    session_id: str
    websocket_url: str = Field(
        ...,
        description="Browser WebSocket URL (PCM → Deepgram → tools → Cartesia).",
    )


class SummaryResponse(BaseModel):
    status: str
    summary: Optional[Dict[str, Any]] = None
    cost_breakdown: Optional[Dict[str, Any]] = None
    transcript: Optional[List[Dict[str, Any]]] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


def _new_session_id() -> str:
    return secrets.token_hex(8)


def _new_room_name(session_id: str) -> str:
    return f"mykare-{session_id}"


def _public_websocket_voice_url(session_id: str) -> str:
    base = settings.BACKEND_PUBLIC_URL.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base.removeprefix("https://") + f"/api/ws/voice/{session_id}"
    if base.startswith("http://"):
        return "ws://" + base.removeprefix("http://") + f"/api/ws/voice/{session_id}"
    return f"ws://{base}/api/ws/voice/{session_id}"


async def _create_livekit_room(room_name: str, session_id: str) -> None:
    lkapi = lk_api.LiveKitAPI(
        url=settings.LIVEKIT_URL,
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        await lkapi.room.create_room(
            lk_api.CreateRoomRequest(
                name=room_name,
                empty_timeout=300,
                max_participants=4,
                metadata=json.dumps({"session_id": session_id}),
            )
        )
    except lk_api.TwirpError as exc:
        if (
            exc.status in (401, 403)
            or exc.code == lk_api.TwirpErrorCode.UNAUTHENTICATED
            or exc.code == lk_api.TwirpErrorCode.PERMISSION_DENIED
        ):
            logger.error(
                "LiveKit API rejected credentials (room=%s): %s",
                room_name,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "LiveKit rejected the server API credentials (check API key and secret "
                    "for the same project as LIVEKIT_URL in backend/.env, then restart the API)."
                ),
            ) from exc
        logger.warning(
            "Could not pre-create LiveKit room %s; agent will rely on room name fallback: %s",
            room_name,
            exc,
        )
    except ContentTypeError as exc:
        status_code = getattr(exc, "status", None)
        if status_code in (401, 403) or " 401," in str(exc) or " 403," in str(exc):
            logger.error(
                "LiveKit API rejected credentials (room=%s, CreateRoom non-JSON error): %s",
                room_name,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "LiveKit rejected the server API credentials (check API key and secret "
                    "for the same project as LIVEKIT_URL in backend/.env, then restart the API)."
                ),
            ) from exc
        logger.warning(
            "Could not pre-create LiveKit room %s; agent will rely on room name fallback: %s",
            room_name,
            exc,
        )
    except Exception:
        logger.warning(
            "Could not pre-create LiveKit room %s; agent will rely on room name fallback.",
            room_name,
            exc_info=True,
        )
    finally:
        await lkapi.aclose()


def _mint_token(*, room_name: str, identity: str, session_id: str) -> str:
    grants = lk_api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    token = (
        lk_api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name("Patient")
        .with_grants(grants)
        .with_metadata(json.dumps({"session_id": session_id}))
        .with_ttl(timedelta(minutes=15))
    )
    return token.to_jwt()


async def _validate_participant_token_with_edge(server_url: str, token: str) -> None:
    parsed = urlparse(server_url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "LIVEKIT_URL must be a full URL, for example "
                "wss://your-project.livekit.cloud"
            ),
        )
    scheme = parsed.scheme
    if scheme.startswith("ws"):
        scheme = scheme.replace("ws", "http")
    http_base = f"{scheme}://{parsed.netloc}".rstrip("/")
    validate_url = f"{http_base}/rtc/v1/validate?{urlencode({'access_token': token})}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(validate_url)
    except httpx.RequestError as exc:
        logger.warning(
            "Could not reach LiveKit /rtc/v1/validate (skipping check): %s",
            exc,
        )
        return

    if resp.status_code in (401, 403):
        logger.error(
            "LiveKit /rtc/v1/validate rejected the participant token (HTTP %s).",
            resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "LiveKit rejected the participant token. Use LIVEKIT_API_KEY and "
                "LIVEKIT_API_SECRET from the same LiveKit Cloud project as LIVEKIT_URL "
                "in backend/.env, then restart the API."
            ),
        )
    if resp.status_code >= 400:
        logger.warning(
            "LiveKit /rtc/v1/validate returned HTTP %s (continuing without failing).",
            resp.status_code,
        )


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_session(request: Request) -> CreateSessionResponse:
    debug_log(
        run_id="baseline",
        hypothesis_id="H2",
        location="api/sessions.py:create_session:entry",
        message="create_session_called",
        data={
            "livekit_configured": settings.livekit_configured,
            "client": getattr(request.client, "host", None),
        },
    )

    if not settings.livekit_configured:
        debug_log(
            run_id="baseline",
            hypothesis_id="H2",
            location="api/sessions.py:create_session:guard",
            message="create_session_rejected_missing_livekit",
            data={"reason": "livekit_not_configured"},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Voice calls are not available yet. "
                "Please configure LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL "
                "in backend/.env and restart the server."
            ),
        )

    session_id = _new_session_id()
    room_name = _new_room_name(session_id)
    participant_identity = f"patient-{session_id}"

    await _create_livekit_room(room_name, session_id)

    try:
        livekit_token = _mint_token(
            room_name=room_name,
            identity=participant_identity,
            session_id=session_id,
        )
    except Exception as exc:
        debug_log(
            run_id="baseline",
            hypothesis_id="H3",
            location="api/sessions.py:create_session:mint",
            message="livekit_token_mint_failed",
            data={"error_type": type(exc).__name__},
        )

        logger.exception("Failed to mint LiveKit token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate LiveKit token.",
        ) from exc

    await _validate_participant_token_with_edge(settings.LIVEKIT_URL, livekit_token)

    db = get_db()
    try:
        await db.execute(
            "INSERT INTO sessions (id, transcript) VALUES (?, '[]')",
            (session_id,),
        )
        await db.commit()
    except Exception as exc:
        debug_log(
            run_id="baseline",
            hypothesis_id="H3",
            location="api/sessions.py:create_session:db_insert",
            message="session_insert_failed",
            data={"error_type": type(exc).__name__},
        )

        logger.exception("Failed to insert session row")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create session.",
        ) from exc

    logger.info("Created session %s (room=%s)", session_id, room_name)

    debug_log(
        run_id="baseline",
        hypothesis_id="H3",
        location="api/sessions.py:create_session:success",
        message="create_session_succeeded",
        data={"session_id_prefix": session_id[:4], "room": room_name},
    )

    return CreateSessionResponse(
        session_id=session_id,
        livekit_token=livekit_token,
        livekit_url=settings.LIVEKIT_URL,
        room=room_name,
    )


@router.post(
    "/websocket-voice",
    response_model=WebSocketVoiceSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def create_websocket_voice_session(
    request: Request,
) -> WebSocketVoiceSessionResponse:
    logger.debug(
        "websocket_voice_session client=%s", getattr(request.client, "host", None)
    )

    if not settings.websocket_voice_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "WebSocket mode is not configured. Set OPENAI_API_KEY in backend/.env."
            ),
        )

    session_id = _new_session_id()
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO sessions (id, transcript) VALUES (?, '[]')",
            (session_id,),
        )
        await db.commit()
    except Exception as exc:
        logger.exception("Failed to insert websocket voice session")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create session.",
        ) from exc

    logger.info("Created WebSocket voice session %s", session_id)
    return WebSocketVoiceSessionResponse(
        session_id=session_id,
        websocket_url=_public_websocket_voice_url(session_id),
    )


@router.get("/{session_id}/summary", response_model=SummaryResponse)
async def get_summary(session_id: str) -> SummaryResponse:
    db = get_db()
    async with db.execute(
        """
        SELECT id, transcript, summary, cost_breakdown, started_at, ended_at
        FROM sessions WHERE id = ?
        """,
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session id."
        )

    if not row["summary"]:
        return SummaryResponse(status="pending")

    try:
        summary = json.loads(row["summary"])
    except json.JSONDecodeError:
        summary = None

    cost = None
    if row["cost_breakdown"]:
        try:
            cost = json.loads(row["cost_breakdown"])
        except json.JSONDecodeError:
            cost = None

    transcript: List[Dict[str, Any]] = []
    if row["transcript"]:
        try:
            transcript = json.loads(row["transcript"]) or []
        except json.JSONDecodeError:
            transcript = []

    return SummaryResponse(
        status="ready",
        summary=summary,
        cost_breakdown=cost,
        transcript=transcript,
        started_at=row["started_at"],
        ended_at=row["ended_at"],
    )
