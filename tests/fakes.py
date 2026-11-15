"""인메모리 테스트 더블.

예약 규칙은 Postgres 없이 검증할 수 있어야 합니다. 도메인 함수가 ports.py
프로토콜만 받기 때문에 가능한 일이고, 이 파일이 그 프로토콜의 메모리 구현입니다.

**단 하나 흉내낼 수 없는 것**: 동시성입니다. 여기서 SlotTaken 은 딕셔너리를
훑어서 냅니다. 실제로는 appointments_active_slot 유니크 인덱스가 판정합니다.
두 통화가 같은 슬롯을 동시에 잡는 경우는 이 더블로 "통과"했다고 말할 수 없고,
그래서 그 테스트만 @pytest.mark.db 로 분리돼 실제 DB 를 기다립니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from uuid import UUID

from app.domain.errors import AppointmentNotFound, SlotTaken
from app.domain.models import (
    Appointment,
    AppointmentStatus,
    Patient,
    Provider,
    Slot,
    VisitType,
)

# 슬롯을 점유하고 있다고 보는 상태. 취소·노쇼는 자리를 비웁니다.
# 끝난 진료(COMPLETED)도 자리를 계속 차지합니다 — 기록이 남아야 하니까요.
ACTIVE = (AppointmentStatus.BOOKED, AppointmentStatus.COMPLETED)


@dataclass
class Store:
    """세 레포지토리가 공유하는 하나의 상태.

    레포지토리를 따로 만들면서 상태를 따로 들면, 예약을 잡았는데 슬롯은
    여전히 비어 보이는 식의 모순이 테스트 안에서만 생깁니다.
    """

    slots: dict[UUID, Slot] = field(default_factory=dict)
    appointments: dict[UUID, Appointment] = field(default_factory=dict)
    patients: dict[UUID, Patient] = field(default_factory=dict)
    providers: dict[UUID, Provider] = field(default_factory=dict)
    next_id: int = 60

    def mint(self) -> UUID:
        """새 UUID. 시드 id(40~52)와 겹치지 않는 구간에서 셉니다."""
        self.next_id += 1
        return UUID(f"00000000-0000-4000-8000-{self.next_id:012d}")

    def active_on(self, slot_id: UUID) -> Appointment | None:
        for appointment in self.appointments.values():
            if appointment.slot_id == slot_id and appointment.status in ACTIVE:
                return appointment
        return None


class FakeSlotRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def get(self, slot_id: UUID) -> Slot | None:
        return self._store.slots.get(slot_id)

    async def open_slots(
        self,
        clinic_id: UUID,
        *,
        after: datetime,
        department_id: UUID | None = None,
        provider_id: UUID | None = None,
        limit: int = 20,
    ) -> list[Slot]:
        found = []
        for slot in self._store.slots.values():
            if slot.clinic_id != clinic_id or not slot.open:
                continue
            if slot.starts_at <= after:
                continue
            if provider_id is not None and slot.provider_id != provider_id:
                continue
            if department_id is not None:
                provider = self._store.providers.get(slot.provider_id)
                if provider is None or provider.department_id != department_id:
                    continue
            found.append(slot)

        found.sort(key=lambda s: s.starts_at)
        return found[:limit]

    async def claim(
        self,
        slot_id: UUID,
        *,
        patient_id: UUID,
        visit: VisitType,
        idempotency_key: str,
    ) -> Appointment:
        slot = self._store.slots[slot_id]

        # 실제 구현에서는 이 검사가 유니크 제약 위반을 잡는 except 절입니다.
        if self._store.active_on(slot_id) is not None:
            raise SlotTaken(f"이미 예약이 붙어 있습니다: {slot_id}")

        appointment = Appointment(
            id=self._store.mint(),
            clinic_id=slot.clinic_id,
            slot_id=slot_id,
            patient_id=patient_id,
            visit=visit,
            status=AppointmentStatus.BOOKED,
            idempotency_key=idempotency_key,
        )
        self._store.appointments[appointment.id] = appointment
        self._store.slots[slot_id] = replace(slot, open=False)
        return appointment

    async def release(self, appointment_id: UUID) -> Appointment:
        appointment = self._store.appointments.get(appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"예약 없음: {appointment_id}")

        cancelled = replace(appointment, status=AppointmentStatus.CANCELLED)
        self._store.appointments[appointment_id] = cancelled

        slot = self._store.slots.get(appointment.slot_id)
        if slot is not None and self._store.active_on(slot.id) is None:
            self._store.slots[slot.id] = replace(slot, open=True)

        return cancelled


class FakeAppointmentRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def get(self, appointment_id: UUID) -> Appointment | None:
        return self._store.appointments.get(appointment_id)

    async def by_idempotency_key(self, key: str) -> Appointment | None:
        for appointment in self._store.appointments.values():
            if appointment.idempotency_key == key:
                return appointment
        return None


class FakePatientRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    async def find(
        self, clinic_id: UUID, *, phone: str, birth_date: date
    ) -> Patient | None:
        for patient in self._store.patients.values():
            if (
                patient.clinic_id == clinic_id
                and patient.phone == phone
                and patient.birth_date == birth_date
            ):
                return patient
        return None

    async def create(
        self, clinic_id: UUID, *, name: str, phone: str, birth_date: date
    ) -> Patient:
        patient = Patient(
            id=self._store.mint(),
            clinic_id=clinic_id,
            name=name,
            phone=phone,
            birth_date=birth_date,
        )
        self._store.patients[patient.id] = patient
        return patient

    async def has_completed_visit(self, patient_id: UUID) -> bool:
        """예약 기록에서 도출합니다. 따로 들고 있으면 둘이 어긋납니다."""
        return any(
            a.patient_id == patient_id and a.status is AppointmentStatus.COMPLETED
            for a in self._store.appointments.values()
        )
