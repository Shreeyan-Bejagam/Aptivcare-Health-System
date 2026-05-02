from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils.debug_runtime import debug_log

logger = logging.getLogger("mykare.config")

_BACKEND_ROOT = Path(__file__).resolve().parent
_DOTENV_PATH = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_DOTENV_PATH) if _DOTENV_PATH.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    LIVEKIT_URL: str = ""

    OPENAI_API_KEY: str = ""
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_STT_MODEL: str = "whisper-1"
    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE: str = "alloy"
    OPENAI_SUMMARY_MODEL: str = "gpt-4o-mini"

    DEEPGRAM_API_KEY: str = ""
    DEEPGRAM_MODEL: str = "nova-2-general"

    CARTESIA_API_KEY: str = ""
    CARTESIA_TTS_MODEL: str = "sonic-2"
    CARTESIA_VOICE_ID: str = ""

    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

    DATABASE_PATH: str = "./data/mykare.db"

    FRONTEND_ORIGIN: str = "http://localhost:5173"

    ALLOWED_SLOTS: str = '{"slots": ["09:00","10:00","11:00","14:00","15:00","16:00"]}'

    SLOT_HORIZON_DAYS: int = 7

    LOG_LEVEL: str = "INFO"

    OPENAI_STT_PRICE_PER_MIN: float = 0.006
    OPENAI_TTS_PRICE_PER_CHAR: float = 0.000015
    OPENAI_INPUT_PRICE_PER_MTOK: float = 0.15
    OPENAI_OUTPUT_PRICE_PER_MTOK: float = 0.60
    DEEPGRAM_PRICE_PER_MIN: float = 0.0043
    CARTESIA_PRICE_PER_CHAR: float = 0.00004

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.upper().strip()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Unknown LOG_LEVEL: {value!r}")
        return normalized

    @field_validator("DATABASE_PATH", mode="before")
    @classmethod
    def _resolve_database_path(cls, value: object) -> str:
        if value is None:
            return "./data/mykare.db"
        raw = str(value).strip()
        if not raw:
            return str((_BACKEND_ROOT / "data" / "mykare.db").resolve())
        path = Path(raw)
        if path.is_absolute():
            return str(path)
        return str((_BACKEND_ROOT / path).resolve())

    @field_validator(
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "LIVEKIT_URL",
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY",
        "CARTESIA_VOICE_ID",
        mode="before",
    )
    @classmethod
    def _strip_trimmed_secrets(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @property
    def livekit_configured(self) -> bool:
        return bool(self.LIVEKIT_API_KEY and self.LIVEKIT_API_SECRET and self.LIVEKIT_URL)

    @property
    def voice_pipeline_configured(self) -> bool:
        return self.livekit_configured and bool(self.OPENAI_API_KEY)

    @property
    def deepgram_configured(self) -> bool:
        return bool(self.DEEPGRAM_API_KEY)

    @property
    def cartesia_configured(self) -> bool:
        return bool(self.CARTESIA_API_KEY and self.CARTESIA_VOICE_ID)

    @property
    def websocket_voice_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def time_slots(self) -> List[str]:
        try:
            decoded = json.loads(self.ALLOWED_SLOTS)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"ALLOWED_SLOTS is not valid JSON: {exc.msg}"
            ) from exc

        if not isinstance(decoded, dict) or "slots" not in decoded:
            raise ValueError(
                "ALLOWED_SLOTS must be a JSON object with a 'slots' array."
            )

        slots = decoded["slots"]
        if not isinstance(slots, list) or not all(isinstance(s, str) for s in slots):
            raise ValueError("ALLOWED_SLOTS.slots must be a list of HH:MM strings.")
        return slots


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    if _DOTENV_PATH.is_file():
        logger.info("Loading environment from %s", _DOTENV_PATH)
    else:
        logger.warning(
            "No .env file at %s — using process environment and defaults only.",
            _DOTENV_PATH,
        )
    try:
        s = Settings()
    except ValidationError as exc:
        missing = [
            ".".join(str(loc) for loc in err["loc"])
            for err in exc.errors()
            if err["type"] == "missing"
        ]
        if missing:
            logger.critical(
                "Missing required environment variables: %s. "
                "Copy backend/.env.example to backend/.env and fill them in.",
                ", ".join(missing),
            )
        raise

    empty_keys = [
        name
        for name in (
            "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL",
            "OPENAI_API_KEY",
        )
        if not getattr(s, name, "")
    ]
    if empty_keys:
        logger.warning(
            "The following API keys are empty: %s. "
            "The HTTP server will start but voice calls will NOT work until "
            "you fill them in at backend/.env and restart.",
            ", ".join(empty_keys),
        )

    debug_log(
        run_id="baseline",
        hypothesis_id="H1",
        location="config.py:get_settings",
        message="settings_loaded",
        data={
            "livekit_configured": s.livekit_configured,
            "voice_pipeline_configured": s.voice_pipeline_configured,
            "empty_keys_count": len(empty_keys),
            "livekit_url_present": bool(s.LIVEKIT_URL),
            "openai_key_present": bool(s.OPENAI_API_KEY),
        },
    )

    return s


settings = get_settings()
