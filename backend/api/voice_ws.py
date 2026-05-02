"""
WebSocket realtime voice path: browser PCM → Deepgram live → OpenAI tools → Cartesia TTS.

Complements LiveKit WebRTC when you want a single-origin WebSocket transport (e.g. simpler
corporate firewalls). Requires `websocket_voice_configured` on `Settings`.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agent.state import AgentSessionState
from agent.transcript_store import append_transcript_turn
from agent.tools import end_conversation
from agent.ws_openai_tools import run_ws_agent_turn
from config import settings
from database.connection import get_db
from database.models import TranscriptTurn
from utils.analytics import log_interaction

logger = logging.getLogger("mykare.voice_ws")

router = APIRouter()

_DG_QUERY = (
    "model=nova-2-general&language=en-US&smart_format=true&interim_results=true"
    "&punctuate=true&encoding=linear16&sample_rate=48000&channels=1"
)


def _parse_dg_transcript(payload: dict[str, Any]) -> tuple[str, bool]:
    is_final = bool(payload.get("is_final") or payload.get("speech_final"))
    ch = payload.get("channel")
    if not ch and isinstance(payload.get("channels"), list) and payload["channels"]:
        ch = payload["channels"][0]
    alts = (ch or {}).get("alternatives") or payload.get("alternatives") or []
    if not alts:
        return "", False
    text = (alts[0].get("transcript") or "").strip()
    return text, is_final


async def _synthesize_wav(text: str) -> bytes:
    import httpx

                         
    if settings.cartesia_configured:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "Cartesia-Version": "2025-04-16",
                    "Authorization": f"Bearer {settings.CARTESIA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model_id": settings.CARTESIA_TTS_MODEL,
                    "transcript": text,
                    "voice": {"mode": "id", "id": settings.CARTESIA_VOICE_ID},
                    "output_format": {
                        "container": "wav",
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000,
                    },
                },
            )
            response.raise_for_status()
            return response.content

                                                   
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENAI_TTS_MODEL,
                "voice": settings.OPENAI_TTS_VOICE,
                "input": text,
                "response_format": "wav",
            },
        )
        response.raise_for_status()
        return response.content


@router.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    if not settings.websocket_voice_configured:
        await websocket.send_json(
            {
                "type": "error",
                "message": "WebSocket mode requires OPENAI_API_KEY in backend/.env.",
            }
        )
        await websocket.close(code=4403)
        return

    db = get_db()
    async with db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        await websocket.send_json({"type": "error", "message": "Unknown session id."})
        await websocket.close(code=4404)
        return

    state = AgentSessionState(session_id=session_id, room=None)

    async def emit(payload: dict[str, Any]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:                
            logger.debug("tool_emit send skipped (socket closed)")

    state.tool_emit = emit
    await log_interaction(session_id, "ws_voice_connect", {})

    stop = asyncio.Event()
    utterance_q: asyncio.Queue[str] = asyncio.Queue(maxsize=32)

    async def handle_final_utterance(text: str) -> None:
        await log_interaction(session_id, "stt_final", {"chars": len(text)})
        try:
            await websocket.send_json({"type": "user_text", "text": text})
        except Exception:                
            pass
        await append_transcript_turn(
            session_id,
            TranscriptTurn(
                role="user",
                content=text,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )
        reply, ended = await run_ws_agent_turn(state, text)
        state.metrics.cartesia_chars += len(reply)
        await append_transcript_turn(
            session_id,
            TranscriptTurn(
                role="assistant",
                content=reply,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )
        await websocket.send_json({"type": "assistant_text", "text": reply})
        try:
            audio = await _synthesize_wav(reply)
            await websocket.send_json(
                {
                    "type": "assistant_audio_wav",
                    "encoding": "base64",
                    "data": base64.b64encode(audio).decode("ascii"),
                }
            )
        except Exception:                
            logger.exception("TTS failed for session=%s", session_id)
            await websocket.send_json(
                {"type": "tts_error", "message": "Could not synthesize speech for this reply."}
            )
        await log_interaction(session_id, "assistant_audio", {"reply_chars": len(reply)})
        if ended:
            await websocket.send_json({"type": "call_ended"})
            stop.set()

    async def consume_utterances() -> None:
        while not stop.is_set():
            try:
                text = await asyncio.wait_for(utterance_q.get(), timeout=3600.0)
            except asyncio.TimeoutError:
                continue
            try:
                await handle_final_utterance(text)
            except Exception:                
                logger.exception("Utterance handler failed session=%s", session_id)

    async def pump_deepgram(dg_ws: aiohttp.ClientWebSocketResponse) -> None:
        try:
            while not stop.is_set():
                msg = await dg_ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    text, is_final = _parse_dg_transcript(data)
                    if text and not is_final:
                        try:
                            await websocket.send_json(
                                {"type": "transcript_interim", "text": text}
                            )
                        except Exception:                
                            break
                    if text and is_final:
                        await utterance_q.put(text)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
        except asyncio.CancelledError:
            raise
        except Exception:                
            logger.exception("Deepgram reader stopped for session=%s", session_id)
        finally:
            stop.set()

    async def forward_browser_audio(dg_ws: aiohttp.ClientWebSocketResponse | None) -> None:
        try:
            while not stop.is_set():
                try:
                    message = await websocket.receive()
                except WebSocketDisconnect:
                    break
                if message["type"] == "websocket.disconnect":
                    break
                if message["type"] != "websocket.receive":
                    continue
                if message.get("bytes"):
                    chunk = message["bytes"]
                    if dg_ws is not None:
                        await dg_ws.send_bytes(chunk)
                        state.metrics.deepgram_seconds += len(chunk) / (48000 * 2)
                elif message.get("text"):
                    try:
                        ctrl = json.loads(message["text"])
                    except json.JSONDecodeError:
                        continue
                    if ctrl.get("type") == "ping":
                        try:
                            await websocket.send_json({"type": "pong"})
                        except Exception:                
                            break
                    if ctrl.get("type") == "hangup":
                                                                                
                        try:
                            await end_conversation.handler(state)
                        except Exception:                
                            logger.exception("end_conversation failed during hangup")
                        stop.set()
                        break
                    if ctrl.get("type") == "user_text":
                        text = str(ctrl.get("text") or "").strip()
                        if text:
                            await utterance_q.put(text)
        finally:
            stop.set()

    use_deepgram = settings.deepgram_configured
    consumer_task: asyncio.Task | None = None
    try:
        await websocket.send_json(
            {
                "type": "ready",
                "input_mode": "pcm" if use_deepgram else "text",
                "tts_mode": "cartesia" if settings.cartesia_configured else "openai",
                "sample_rate_hz": 48000,
                "encoding": "linear16",
                "channels": 1,
            }
        )
        consumer_task = asyncio.create_task(consume_utterances())

        if use_deepgram:
            async with aiohttp.ClientSession() as http:
                dg_url = f"wss://api.deepgram.com/v1/listen?{_DG_QUERY}"
                headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
                dg_ws = await http.ws_connect(dg_url, headers=headers, autoping=True)
                await asyncio.gather(
                    pump_deepgram(dg_ws),
                    forward_browser_audio(dg_ws),
                    return_exceptions=True,
                )
                await dg_ws.close()
        else:
            logger.warning(
                "DEEPGRAM_API_KEY is empty: ws voice is running in text-input fallback mode."
            )
            await forward_browser_audio(None)
    except WebSocketDisconnect:
        logger.info("WebSocket voice disconnected session=%s", session_id)
    except Exception:                
        logger.exception("WebSocket voice session failed session=%s", session_id)
        try:
            await websocket.send_json({"type": "error", "message": "Voice session failed."})
        except Exception:                
            pass
    finally:
                                                                             
                                                                          
        if not state.ended:
            try:
                await end_conversation.handler(state)
            except Exception:                
                logger.exception("end_conversation finaliser failed session=%s", session_id)
        stop.set()
        if consumer_task is not None:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        await log_interaction(session_id, "ws_voice_disconnect", {})
