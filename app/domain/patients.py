"""환자 식별과 초진/재진 판정."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.domain.models import Identity
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
    """
    raise NotImplementedError("M1")
