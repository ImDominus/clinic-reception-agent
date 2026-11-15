"""테스트 공용 설비.

예약 테스트는 Postgres 없이 돕니다. 도메인 함수가 ports.py 프로토콜만 받기
때문이고, 그 프로토콜의 메모리 구현은 tests/fakes.py 에 있습니다.
실제 DB 가 있어야 의미 있는 테스트(동시성, 유니크 제약)만 @pytest.mark.db 로
분리해 건너뜁니다.

시간대는 고정 오프셋 +09:00 을 씁니다. 한국은 1988년 이후 서머타임이 없어서
KST 는 항상 +09:00 이고, 이러면 윈도에서 tzdata 없이도 테스트가 돕니다.
운영 코드는 Asia/Seoul 이름을 씁니다(app/config.py).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest

from app.domain.models import (
    Appointment,
    AppointmentStatus,
    Patient,
    Provider,
    Slot,
    VisitType,
)
from tests.fakes import (
    FakeAppointmentRepository,
    FakePatientRepository,
    FakeSlotRepository,
    Store,
)

KST = timezone(timedelta(hours=9))


def run(coro: Any) -> Any:
    """pytest-asyncio 없이 코루틴을 돌립니다. 의존성 하나 줄입니다."""
    return asyncio.run(coro)


def uid(n: int) -> UUID:
    """읽기 쉬운 고정 UUID. 테스트 실패 로그에서 눈으로 구분됩니다."""
    return UUID(f"00000000-0000-4000-8000-{n:012d}")


CLINIC = uid(1)
DEPT_INTERNAL = uid(10)
DEPT_PEDS = uid(11)
PROVIDER_A = uid(20)
PROVIDER_B = uid(21)
PATIENT = uid(30)
PATIENT_CHILD = uid(31)
PATIENT_NEVER_CAME = uid(32)

SLOT_A = uid(40)  # 예약이 붙어 있습니다 (appointment uid(50))
SLOT_B = uid(41)  # 비어 있습니다 — 변경 성공 시나리오의 목적지
SLOT_C = uid(42)  # 예약이 붙어 있습니다 (appointment uid(52)) — 변경 실패 시나리오
SLOT_PAST = uid(43)  # now 이전
SLOT_NOW = uid(44)  # 정확히 now 에 시작 (경계)
SLOT_PEDS = uid(45)  # 소아과
SLOT_COMPLETED = uid(48)  # 끝난 진료가 붙어 있습니다 (appointment uid(51))

APPT_BOOKED = uid(50)
APPT_COMPLETED = uid(51)
APPT_ON_SLOT_C = uid(52)

# book() 테스트가 쓰는 키. 시드 예약 uid(50) 이 이미 들고 있는 키와 같습니다.
# 그래서 같은 키로 book() 하면 새로 잡히지 않고 원래 예약이 돌아옵니다.
SEED_BOOK_KEY = "call-0001:book"

NOW = datetime(2026, 12, 7, 9, 0, tzinfo=KST)
assert NOW.weekday() == 0, "요일 계산이 들어가므로 월요일로 고정합니다"


@pytest.fixture
def now() -> datetime:
    """월요일 09:00 KST 로 고정. 요일 계산이 들어가므로 요일을 고정합니다."""
    return NOW


def _slot(slot_id: UUID, minutes_from_now: int, *, provider: UUID, open: bool) -> Slot:
    starts = NOW + timedelta(minutes=minutes_from_now)
    return Slot(
        id=slot_id,
        clinic_id=CLINIC,
        provider_id=provider,
        starts_at=starts,
        ends_at=starts + timedelta(minutes=15),
        open=open,
    )


def build_store() -> Store:
    """테스트 하나당 새로 세우는 시드.

    의원 하나, 진료과 둘, 의사 둘. 슬롯은 `now` 기준 상대 시각으로 깔아서
    "지난 슬롯", "정확히 지금 시작하는 슬롯" 같은 경계가 날짜와 무관하게
    유지됩니다.
    """
    store = Store()

    store.providers = {
        PROVIDER_A: Provider(
            id=PROVIDER_A,
            clinic_id=CLINIC,
            department_id=DEPT_INTERNAL,
            name="김내과",
        ),
        PROVIDER_B: Provider(
            id=PROVIDER_B,
            clinic_id=CLINIC,
            department_id=DEPT_PEDS,
            name="이소아",
        ),
    }

    for slot in (
        _slot(SLOT_PAST, -60, provider=PROVIDER_A, open=True),
        _slot(SLOT_NOW, 0, provider=PROVIDER_A, open=True),
        _slot(SLOT_A, 15, provider=PROVIDER_A, open=False),
        _slot(SLOT_B, 30, provider=PROVIDER_A, open=True),
        _slot(SLOT_C, 45, provider=PROVIDER_A, open=False),
        _slot(SLOT_PEDS, 60, provider=PROVIDER_B, open=True),
        _slot(uid(46), 75, provider=PROVIDER_A, open=True),
        _slot(uid(47), 90, provider=PROVIDER_A, open=True),
        _slot(SLOT_COMPLETED, 120, provider=PROVIDER_A, open=False),
    ):
        store.slots[slot.id] = slot

    for appointment in (
        Appointment(
            id=APPT_BOOKED,
            clinic_id=CLINIC,
            slot_id=SLOT_A,
            patient_id=PATIENT,
            visit=VisitType.FIRST,
            status=AppointmentStatus.BOOKED,
            idempotency_key=SEED_BOOK_KEY,
        ),
        Appointment(
            id=APPT_COMPLETED,
            clinic_id=CLINIC,
            slot_id=SLOT_COMPLETED,
            patient_id=PATIENT,
            visit=VisitType.RETURN,
            status=AppointmentStatus.COMPLETED,
            idempotency_key="seed:completed",
        ),
        Appointment(
            id=APPT_ON_SLOT_C,
            clinic_id=CLINIC,
            slot_id=SLOT_C,
            patient_id=PATIENT_CHILD,
            visit=VisitType.RETURN,
            status=AppointmentStatus.BOOKED,
            idempotency_key="seed:slot-c",
        ),
    ):
        store.appointments[appointment.id] = appointment

    # 같은 번호를 쓰는 가족. 생년월일로만 갈립니다.
    for patient in (
        Patient(
            id=PATIENT,
            clinic_id=CLINIC,
            name="조보호자",
            phone="01000000001",
            birth_date=date(1984, 3, 12),
        ),
        Patient(
            id=PATIENT_CHILD,
            clinic_id=CLINIC,
            name="조아이",
            phone="01000000001",
            birth_date=date(2019, 7, 2),
        ),
        Patient(
            id=PATIENT_NEVER_CAME,
            clinic_id=CLINIC,
            name="예약만한사람",
            phone="01000000002",
            birth_date=date(1991, 11, 30),
        ),
    ):
        store.patients[patient.id] = patient

    return store


@pytest.fixture
def store() -> Store:
    return build_store()


@pytest.fixture
def slots(store: Store) -> FakeSlotRepository:
    return FakeSlotRepository(store)


@pytest.fixture
def appointments(store: Store) -> FakeAppointmentRepository:
    return FakeAppointmentRepository(store)


@pytest.fixture
def patients(store: Store) -> FakePatientRepository:
    return FakePatientRepository(store)


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
