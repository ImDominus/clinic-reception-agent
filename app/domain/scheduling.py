"""예약 코어.

이 프로젝트의 설계 원칙 하나: **예약 확정은 여기서만 일어납니다.**
모델은 후보를 제안할 뿐이고 가능/불가 판정은 전부 이 모듈이 합니다.
모델이 없는 시간을 지어내도 예약은 잡히지 않습니다.

검사 순서가 계약의 일부입니다. 멱등키 조회보다 슬롯 검증이 먼저 옵니다 —
재시도라고 해서 없는 슬롯이나 지난 슬롯이 통과되면 안 됩니다. 멱등은
"같은 요청을 두 번 처리하지 않는다"는 뜻이고, "틀린 요청을 통과시킨다"는
뜻이 아닙니다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.domain.errors import (
    AppointmentNotFound,
    NotCancellable,
    SlotInPast,
    SlotNotFound,
)
from app.domain.models import Appointment, AppointmentStatus, Slot, VisitType
from app.domain.ports import AppointmentRepository, SlotRepository

# 전화로 후보를 열 개 읽어줄 수는 없습니다. 음성 채널의 제약이 도메인 기본값입니다.
MAX_SUGGESTIONS = 3


async def find_slots(
    slots: SlotRepository,
    clinic_id: UUID,
    *,
    now: datetime,
    visit: VisitType,
    department_id: UUID | None = None,
    provider_id: UUID | None = None,
    limit: int = MAX_SUGGESTIONS,
) -> list[Slot]:
    """예약 가능한 슬롯 후보.

    계약:
      - open=true 인 슬롯만.
      - now 이전에 시작하는 슬롯은 제외. 경계(starts_at == now)도 제외.
      - 빠른 시각 순, 최대 limit 개.
      - department_id / provider_id 는 주면 좁히고, 안 주면 의원 전체.
      - 후보가 없으면 빈 리스트. 예외를 쓰지 않습니다. "없다"는 정상 응답입니다.

    `visit` 는 아직 후보를 바꾸지 않습니다. 초진은 진료시간이 더 길어서 슬롯을
    두 칸 묶어야 하는데, 그 길이가 docs/open-questions.md 1번으로 열려 있습니다.
    정해지기 전에 임의의 숫자를 넣으면 그 숫자가 사실처럼 굳습니다.

    필터를 레포지토리에 넘기고 여기서 한 번 더 겁니다. 중복이지만 의도된
    중복입니다 — 지난 시각이나 닫힌 슬롯을 환자에게 읽어주는 것이 이 시스템에서
    가장 비싼 실수고, SQL 한 줄 틀리는 것으로 거기까지 가면 안 됩니다.
    """
    if limit <= 0:
        return []

    candidates = await slots.open_slots(
        clinic_id,
        after=now,
        department_id=department_id,
        provider_id=provider_id,
        limit=limit,
    )

    usable = [s for s in candidates if s.open and s.starts_at > now]
    usable.sort(key=lambda s: s.starts_at)
    return usable[:limit]


async def book(
    slots: SlotRepository,
    appointments: AppointmentRepository,
    clinic_id: UUID,
    *,
    slot_id: UUID,
    patient_id: UUID,
    visit: VisitType,
    idempotency_key: str,
    now: datetime,
) -> Appointment:
    """슬롯 하나를 예약합니다.

    계약:
      - 같은 idempotency_key 로 다시 부르면 **원래 예약을 그대로** 돌려줍니다.
        통화는 끊기고 재시도는 일어납니다. 두 번 잡히면 안 됩니다.
      - 없는 슬롯 → SlotNotFound.
      - 이미 지난 슬롯 → SlotInPast.
      - 이미 살아있는 예약이 붙은 슬롯 → SlotTaken.
      - 확정은 slots.claim() 안의 유니크 제약으로 판정합니다. 여기서 먼저
        "비었나" 읽고 나중에 쓰는 식으로 두 단계로 나누지 않습니다.
      - 성공하면 status=BOOKED.
    """
    slot = await slots.get(slot_id)
    if slot is None or slot.clinic_id != clinic_id:
        # 다른 의원의 슬롯은 존재하지 않는 것과 같게 답합니다. 어느 의원에
        # 어떤 슬롯이 있는지를 slot_id 추측으로 알아낼 수 없게 합니다.
        raise SlotNotFound(f"슬롯 없음: {slot_id}")

    if slot.starts_at <= now:
        raise SlotInPast(f"이미 지난 슬롯입니다: {slot.starts_at.isoformat()}")

    existing = await appointments.by_idempotency_key(idempotency_key)
    if existing is not None:
        return existing

    # 빈자리 확인과 점유를 나누지 않습니다. 판정은 유니크 제약이 합니다.
    # 여기서 미리 slot.open 을 보고 분기하면 그 사이에 남이 잡습니다.
    return await slots.claim(
        slot_id,
        patient_id=patient_id,
        visit=visit,
        idempotency_key=idempotency_key,
    )


async def cancel(
    slots: SlotRepository,
    appointments: AppointmentRepository,
    *,
    appointment_id: UUID,
    now: datetime,
) -> Appointment:
    """예약을 취소하고 슬롯을 다시 엽니다.

    계약:
      - 멱등합니다. 이미 취소된 예약을 또 취소하면 그 예약을 그대로 돌려줍니다.
      - completed / no_show 는 취소 대상이 아닙니다 → DomainError.
      - 취소된 슬롯은 다시 예약 가능해야 합니다.
    """
    appointment = await appointments.get(appointment_id)
    if appointment is None:
        raise AppointmentNotFound(f"예약 없음: {appointment_id}")

    if appointment.status is AppointmentStatus.CANCELLED:
        return appointment

    if appointment.status is not AppointmentStatus.BOOKED:
        raise NotCancellable(
            f"취소할 수 없는 상태입니다: {appointment.status.value}"
        )

    return await slots.release(appointment_id)


async def reschedule(
    slots: SlotRepository,
    appointments: AppointmentRepository,
    *,
    appointment_id: UUID,
    new_slot_id: UUID,
    idempotency_key: str,
    now: datetime,
) -> Appointment:
    """예약 시각을 옮깁니다.

    계약:
      - 새 슬롯 점유가 실패하면 **기존 예약은 살아 있어야 합니다.** 먼저 취소하고
        다음에 잡는 순서는 금지입니다. 중간에 실패하면 환자는 예약을 잃습니다.
      - 같은 슬롯으로 옮기면 아무 일도 하지 않고 기존 예약을 돌려줍니다.
      - 성공하면 옛 슬롯은 다시 열립니다.

    순서가 전부입니다: **claim 먼저, release 나중.** claim 이 SlotTaken 으로
    죽으면 release 에 도달하지 못하고, 그래서 환자의 원래 예약은 그대로
    남습니다. 반대로 쓰면 실패한 변경이 예약을 지웁니다.
    """
    appointment = await appointments.get(appointment_id)
    if appointment is None:
        raise AppointmentNotFound(f"예약 없음: {appointment_id}")

    if appointment.status is not AppointmentStatus.BOOKED:
        raise NotCancellable(
            f"변경할 수 없는 상태입니다: {appointment.status.value}"
        )

    if appointment.slot_id == new_slot_id:
        # 같은 시각으로 옮기라는 요청. 환자가 확인차 다시 말한 경우입니다.
        # 점유를 시도하면 자기 예약 때문에 SlotTaken 이 납니다.
        return appointment

    existing = await appointments.by_idempotency_key(idempotency_key)
    if existing is not None:
        return existing

    new_slot = await slots.get(new_slot_id)
    if new_slot is None or new_slot.clinic_id != appointment.clinic_id:
        raise SlotNotFound(f"슬롯 없음: {new_slot_id}")

    if new_slot.starts_at <= now:
        raise SlotInPast(f"이미 지난 슬롯입니다: {new_slot.starts_at.isoformat()}")

    # 1) 새 자리를 먼저 확보합니다. 실패하면 여기서 끝나고 원래 예약은 무사합니다.
    moved = await slots.claim(
        new_slot_id,
        patient_id=appointment.patient_id,
        visit=appointment.visit,
        idempotency_key=idempotency_key,
    )

    # 2) 확보된 다음에야 옛 자리를 놓습니다.
    await slots.release(appointment_id)

    return moved
