"""STT / TTS / LLM 어댑터 인터페이스.

벤더는 바뀝니다. 한국어 인식률도 가격도 아직 실측 전입니다(docs/open-questions.md).
그래서 호출부는 이 프로토콜만 알고, 구현을 갈아끼웁니다.

구간별 지연을 재는 자리를 인터페이스에 박아둡니다. 나중에 붙이는 계측은
안 붙습니다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    is_final: bool
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class SpeechChunk:
    audio: bytes
    # 합성 요청 → 첫 바이트. 체감 지연의 대부분이 여기 있습니다.
    first_byte_ms: int | None = None


class SpeechToText(Protocol):
    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        """부분 결과를 계속 흘리고, 발화가 끝나면 is_final=True 를 한 번 낸다."""
        ...


class TextToSpeech(Protocol):
    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[SpeechChunk]:
        """문장 단위로 기다리지 않는다. 들어오는 조각부터 합성을 시작한다."""
        ...


class Responder(Protocol):
    async def reply(self, *, call_id: str, user_text: str) -> AsyncIterator[str]:
        """툴 호출을 포함한 한 턴. 토큰을 흘려서 TTS 가 먼저 시작할 수 있게 한다."""
        ...
