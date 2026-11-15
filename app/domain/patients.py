"""환자 식별과 초진/재진 판정."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.domain.errors import PatientNotIdentified
from app.domain.models import Identity, VisitType
from app.domain.ports import PatientRepository


async def identify(
    patients: PatientRepository,
    clinic_id: UUID,
    *,
    phone: str | None,
    birth_date: date | None,
) -> Identity:
    """전화번호 + 생년월일로 사람을 특정하고 초진/재진을 판정합니다.

    계약:
      - 둘 중 하나라도 없으면 PatientNotIdentified.
      - 기록이 없으면 Identity(visit=FIRST, patient=None).
      - 기록이 있고 완료된 진료가 한 번이라도 있으면 RETURN.
      - 기록은 있지만 전부 취소/노쇼면 FIRST. 온 적이 없으니까요.
      - 같은 번호에 생년월일이 다르면 다른 사람입니다. 가족이 번호 하나를
        쓰는 경우가 흔합니다.

    여기서 환자를 만들지 않습니다. 식별은 읽기만 합니다. 처음 온 사람의
    레코드는 예약을 확정하는 시점에 생깁니다 — 전화를 걸어보고 끊은 사람까지
    환자로 쌓이면 초진/재진 판정이 금방 더러워집니다.
    """
    if not phone or birth_date is None:
        raise PatientNotIdentified("전화번호와 생년월일이 모두 필요합니다")

    patient = await patients.find(clinic_id, phone=phone, birth_date=birth_date)
    if patient is None:
        return Identity(visit=VisitType.FIRST, patient=None)

    if await patients.has_completed_visit(patient.id):
        return Identity(visit=VisitType.RETURN, patient=patient)

    # 기록은 있지만 완료된 진료가 없습니다. 예약만 잡고 안 온 사람입니다.
    return Identity(visit=VisitType.FIRST, patient=patient)
