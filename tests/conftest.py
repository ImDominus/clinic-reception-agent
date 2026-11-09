"""테스트 공용 설비.

지금 예약 테스트는 전부 빨간불입니다. 의도된 상태입니다 — 구현이 없으니까요.
테스트 본문은 최종 형태로 써둡니다. M1 은 "이 테스트들을 켜는 일"입니다.

시간대는 고정 오프셋 +09:00 을 씁니다. 한국은 1988년 이후 서머타임이 없어서
KST 는 항상 +09:00 이고, 이러면 윈도에서 tzdata 없이도 테스트가 돕니다.
운영 코드는 Asia/Seoul 이름을 씁니다(app/config.py).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest

KST = timezone(timedelta(hours=9))


def run(coro: Any) -> Any:
    """pytest-asyncio 없이 코루틴을 돌립니다. 의존성 하나 줄입니다."""
    return asyncio.run(coro)


class Unbuilt:
    """아직 구현이 없는 레포지토리 자리.

    실수로 여기까지 흘러오면 TypeError 같은 애매한 실패가 아니라
    무엇이 없는지 말하고 죽습니다.
    """

    def __init__(self, what: str) -> None:
        self._what = what

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError(f"M1: {self._what}.{name} 구현 없음")


def uid(n: int) -> UUID:
    """읽기 쉬운 고정 UUID. 테스트 실패 로그에서 눈으로 구분됩니다."""
    return UUID(f"00000000-0000-4000-8000-{n:012d}")


CLINIC = uid(1)
DEPT_INTERNAL = uid(10)
DEPT_PEDS = uid(11)
PROVIDER_A = uid(20)
PROVIDER_B = uid(21)
PATIENT = uid(30)
SLOT_A = uid(40)
SLOT_B = uid(41)


@pytest.fixture
def now() -> datetime:
    """월요일 09:00 KST 로 고정. 요일 계산이 들어가므로 요일을 고정합니다."""
    d = datetime(2026, 12, 7, 9, 0, tzinfo=KST)
    assert d.weekday() == 0
    return d


@pytest.fixture
def slots() -> Any:
    return Unbuilt("SlotRepository")


@pytest.fixture
def appointments() -> Any:
    return Unbuilt("AppointmentRepository")


@pytest.fixture
def patients() -> Any:
    return Unbuilt("PatientRepository")


@pytest.fixture
def pg_dsn() -> str:
    """실제 Postgres 가 필요한 테스트용.

    DB 없이 "통과"했다고 할 수 없는 테스트들이 있습니다(동시성, 유니크 제약).
    그런 테스트는 빨간불이 아니라 건너뜀으로 둡니다.
        make db && TEST_DATABASE_URL=... make test
    """
    import os

    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL 없음 — make db 로 띄우고 다시 돌리세요")
    return dsn
