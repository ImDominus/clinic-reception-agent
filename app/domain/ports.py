"""도메인이 바깥에 요구하는 것. 구현은 app/infra 에서(M1).

도메인 함수는 세션이나 커넥션을 직접 들고 있지 않습니다. 여기 프로토콜만 받습니다.
그래서 예약 규칙 테스트는 Postgres 없이 돌고, 동시성 테스트만 실제 DB 를 씁니다.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.domain.models import (
    Appointment,
    Closure,
    Patient,
    Provider,
    ProviderSchedule,
    Slot,
    VisitType,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class SlotRepository(Protocol):
    async def get(self, slot_id: UUID) -> Slot | None: ...

    async def open_slots(
        self,
        clinic_id: UUID,
        *,
        after: datetime,
        department_id: UUID | None = None,
        provider_id: UUID | None = None,
        limit: int = 20,
    ) -> list[Slot]: ...

    async def claim(
        self,
        slot_id: UUID,
        *,
        patient_id: UUID,
        visit: VisitType,
        idempotency_key: str,
    ) -> Appointment:
        """슬롯을 점유하고 예약을 만듭니다.

        충돌 판정은 appointments_active_slot 유니크 인덱스가 합니다.
        애플리케이션 락을 쓰지 않습니다 — 프로세스가 늘어나면 깨지니까요.
        제약 위반은 SlotTaken 으로 올립니다.
        """
        ...

    async def release(self, appointment_id: UUID) -> Appointment: ...


class AppointmentRepository(Protocol):
    async def get(self, appointment_id: UUID) -> Appointment | None: ...

    async def by_idempotency_key(self, key: str) -> Appointment | None: ...


class PatientRepository(Protocol):
    async def find(self, clinic_id: UUID, *, phone: str, birth_date: date) -> Patient | None: ...

    async def create(
        self, clinic_id: UUID, *, name: str, phone: str, birth_date: date
    ) -> Patient: ...

    async def has_completed_visit(self, patient_id: UUID) -> bool: ...


class ScheduleRepository(Protocol):
    async def provider(self, provider_id: UUID) -> Provider | None: ...

    async def schedules(self, provider_id: UUID) -> list[ProviderSchedule]: ...

    async def closures(
        self, clinic_id: UUID, *, since: datetime, until: datetime
    ) -> list[Closure]: ...
