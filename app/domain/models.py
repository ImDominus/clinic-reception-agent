"""도메인 타입. schema/001_init.sql 과 1:1 로 맞춥니다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum
from uuid import UUID


class VisitType(StrEnum):
    FIRST = "first"
    RETURN = "return"


class AppointmentStatus(StrEnum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


@dataclass(frozen=True, slots=True)
class Clinic:
    id: UUID
    name: str
    timezone: str
    phone: str | None = None


@dataclass(frozen=True, slots=True)
class Department:
    id: UUID
    clinic_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class Provider:
    id: UUID
    clinic_id: UUID
    department_id: UUID
    name: str
    slot_minutes: int = 15
    active: bool = True


@dataclass(frozen=True, slots=True)
class ProviderSchedule:
    """요일별 근무 구간. weekday 0=월 … 6=일.

    점심시간은 별도 칼럼이 아니라 같은 요일에 구간을 두 줄로 넣어 표현합니다
    (예: 09:00-13:00, 14:00-18:00). 쉬는 시간의 종류가 늘어도 스키마가 안 변합니다.
    """

    id: UUID
    provider_id: UUID
    weekday: int
    starts_at: time
    ends_at: time


@dataclass(frozen=True, slots=True)
class Closure:
    """휴진 구간. provider_id 가 None 이면 의원 전체 휴진."""

    id: UUID
    clinic_id: UUID
    starts_at: datetime
    ends_at: datetime
    provider_id: UUID | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SlotDraft:
    """DB 에 넣기 전의 슬롯. materialize_slots 의 출력."""

    clinic_id: UUID
    provider_id: UUID
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True, slots=True)
class Slot:
    id: UUID
    clinic_id: UUID
    provider_id: UUID
    starts_at: datetime
    ends_at: datetime
    open: bool = True


@dataclass(frozen=True, slots=True)
class Patient:
    id: UUID
    clinic_id: UUID
    name: str
    phone: str
    birth_date: date


@dataclass(frozen=True, slots=True)
class Appointment:
    id: UUID
    clinic_id: UUID
    slot_id: UUID
    patient_id: UUID
    visit: VisitType
    status: AppointmentStatus
    idempotency_key: str
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Identity:
    """초진/재진 판정 결과."""

    visit: VisitType
    patient: Patient | None = None
