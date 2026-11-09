"""환경 설정.

의존성 없이 표준 라이브러리만 씁니다. 설정 읽기에 프레임워크를 끼우면
테스트할 때마다 그 프레임워크를 깔아야 합니다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = "postgresql+asyncpg://clinic:clinic@localhost:5433/clinic"
    clinic_tz: str = "Asia/Seoul"

    # 벤더는 어댑터 뒤에 있습니다. 빈 문자열이면 아직 안 고른 상태입니다.
    stt_provider: str = ""
    tts_provider: str = ""
    llm_provider: str = ""

    # 발화 종료 → 첫 음성 출력. docs/architecture.md 2절.
    latency_budget_ms: int = 800

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        e = os.environ if env is None else env
        default = cls()
        return cls(
            database_url=e.get("DATABASE_URL", default.database_url),
            clinic_tz=e.get("CLINIC_TZ", default.clinic_tz),
            stt_provider=e.get("STT_PROVIDER", default.stt_provider),
            tts_provider=e.get("TTS_PROVIDER", default.tts_provider),
            llm_provider=e.get("LLM_PROVIDER", default.llm_provider),
            latency_budget_ms=int(e.get("LATENCY_BUDGET_MS", default.latency_budget_ms)),
        )
