"""HTTP 진입점.

지금은 헬스체크만 있습니다. 예약 API는 M2, 음성은 M3입니다.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings

MILESTONE = "M0"

settings = Settings.from_env()
app = FastAPI(title="clinic-reception-agent", version="0.0.1")


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "milestone": MILESTONE,
        "timezone": settings.clinic_tz,
        "latency_budget_ms": settings.latency_budget_ms,
        "vendors": {
            "stt": settings.stt_provider or "undecided",
            "tts": settings.tts_provider or "undecided",
            "llm": settings.llm_provider or "undecided",
        },
    }
