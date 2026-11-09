"""근무표 → 슬롯 실체화.

I/O 가 없는 순수 함수입니다. 날짜·시간 경계가 이 프로젝트에서 가장 틀리기 쉬운
부분이라, DB 없이 돌려볼 수 있게 분리했습니다.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from app.domain.models import Closure, Provider, ProviderSchedule, SlotDraft


def materialize_slots(
    provider: Provider,
    schedules: list[ProviderSchedule],
    *,
    since: date,
    until: date,
    tz: str,
    closures: list[Closure] | None = None,
) -> list[SlotDraft]:
    """[since, until] 기간의 슬롯을 만듭니다. until 포함.

    계약:
      - provider.slot_minutes 간격으로 자른다.
      - 근무 구간에 딱 들어가지 않는 꼬리는 버린다. 마지막 슬롯의 ends_at 은
        근무 종료 시각을 넘지 않는다.
      - 같은 요일에 근무 구간이 여러 줄이면 각각 따로 자른다. 구간 사이
        (점심시간)에는 슬롯이 생기지 않는다.
      - 휴진과 겹치는 슬롯은 만들지 않는다. 일부만 겹쳐도 만들지 않는다.
      - 결과는 starts_at 오름차순, 중복 없음.
      - tz 기준 벽시계로 계산하고 결과는 aware datetime 으로 돌려준다.
    """
    raise NotImplementedError("M1")


def is_closed(closures: list[Closure], *, provider_id: UUID, at: datetime) -> bool:
    """해당 시각이 휴진인지. provider_id 가 None 인 휴진은 의원 전체 휴진입니다."""
    raise NotImplementedError("M1")
