"""모델에게 주는 툴 명세.

네 개입니다. 늘리지 않습니다 — 툴이 많아지면 모델이 고르는 데서 틀립니다.
설명문은 프롬프트의 일부입니다. 코드만큼 신중하게 고칩니다.

핸들러는 M2 에서 붙입니다. 여기는 계약만 있습니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()


LOOKUP_PATIENT = ToolSpec(
    name="lookup_patient",
    description=(
        "전화번호와 생년월일로 환자를 조회하고 초진/재진을 판정한다. "
        "예약을 잡기 전에 반드시 한 번 부른다. "
        "둘 중 하나라도 못 들었으면 추측하지 말고 되묻는다."
    ),
    parameters={
        "phone": {"type": "string", "description": "하이픈 없는 숫자만. 예: 01012345678"},
        "birth_date": {"type": "string", "description": "YYYY-MM-DD"},
    },
    required=("phone", "birth_date"),
)

FIND_SLOTS = ToolSpec(
    name="find_slots",
    description=(
        "예약 가능한 시간 후보를 받아온다. 최대 세 개만 돌아온다. "
        "돌아온 시각만 환자에게 제시한다. 비어 있으면 '그 날은 자리가 없다'고 말하고 "
        "다른 날짜로 다시 부른다. 시간을 임의로 만들어 말하지 않는다."
    ),
    parameters={
        "department": {"type": "string", "description": "진료과 이름. 모르면 생략"},
        "provider": {"type": "string", "description": "의사 이름. 지정이 없으면 생략"},
        "after": {"type": "string", "description": "이 시각 이후. ISO 8601"},
    },
)

BOOK_APPOINTMENT = ToolSpec(
    name="book_appointment",
    description=(
        "find_slots 가 돌려준 slot_id 하나로 예약을 확정한다. "
        "환자가 시각을 복창하고 동의한 뒤에만 부른다. "
        "같은 통화에서 재시도할 때는 idempotency_key 를 바꾸지 않는다."
    ),
    parameters={
        "slot_id": {"type": "string", "description": "find_slots 결과의 값. 직접 만들지 않는다"},
        "patient_name": {"type": "string"},
        "idempotency_key": {"type": "string", "description": "통화 1건 + 예약 1건에 고정"},
    },
    required=("slot_id", "patient_name", "idempotency_key"),
)

ESCALATE_TO_HUMAN = ToolSpec(
    name="escalate_to_human",
    description=(
        "접수·예약 범위를 벗어난 요청은 즉시 이 툴로 넘긴다. "
        "증상 상담, 진단, 치료 방침, 복약 안내, 검사 결과, 보험·비용 문의, "
        "그리고 환자가 사람을 요구할 때. "
        "범위 밖 질문에 추측으로 답하지 않는다. 답하려 시도조차 하지 않는다."
    ),
    parameters={
        "reason": {"type": "string", "description": "넘기는 사유 한 줄"},
        "summary": {"type": "string", "description": "지금까지 파악한 내용 요약"},
    },
    required=("reason",),
)

TOOLS: tuple[ToolSpec, ...] = (
    LOOKUP_PATIENT,
    FIND_SLOTS,
    BOOK_APPOINTMENT,
    ESCALATE_TO_HUMAN,
)
