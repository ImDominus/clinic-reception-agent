"""예약 코어.

이 프로젝트의 설계 원칙 하나: **예약 확정은 여기서만 일어납니다.**
모델은 후보를 제안할 뿐이고 가능/불가 판정은 전부 이 모듈이 합니다.
모델이 없는 시간을 지어내도 예약은 잡히지 않습니다.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.domain.models import Appointment, Slot, VisitType
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
    """
    raise NotImplementedError("M1")


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
    raise NotImplementedError("M1")


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
    raise NotImplementedError("M1")


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
    """
    raise NotImplementedError("M1")
