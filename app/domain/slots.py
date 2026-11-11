"""근무표 → 슬롯 실체화.

I/O 가 없는 순수 함수입니다. 날짜·시간 경계가 이 프로젝트에서 가장 틀리기 쉬운
부분이라, DB 없이 돌려볼 수 있게 분리했습니다.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from uuid import UUID

from app.domain.models import Closure, Provider, ProviderSchedule, SlotDraft

# ZoneInfo 가 있으면 그걸 씁니다. 다만 윈도에는 시스템 시간대 데이터베이스가
# 없어서 tzdata 패키지 없이는 ZoneInfo("Asia/Seoul") 가 실패합니다. 한국은
# 1988년 이후 서머타임이 없으므로 KST 는 항상 +09:00 이고, 이 고정 오프셋은
# Asia/Seoul 에 대해 근사가 아니라 정확합니다.
#
# 서머타임이 있는 지역을 지원하게 되면 tzdata 를 의존성에 넣고 이 표를 지운
# 다음, 아래의 벽시계 산술(전환 시각을 건너뛰거나 두 번 지나는 경우)을
# 다시 봐야 합니다.
_FIXED_OFFSETS: dict[str, tzinfo] = {
    "Asia/Seoul": timezone(timedelta(hours=9)),
}


def _zone(name: str) -> tzinfo:
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:  # pragma: no cover - 3.9+ 에는 항상 있습니다
        pass
    else:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            pass

    fixed = _FIXED_OFFSETS.get(name)
    if fixed is None:
        raise ValueError(
            f"시간대를 해석할 수 없습니다: {name!r}. tzdata 를 설치하거나 "
            f"_FIXED_OFFSETS 에 추가하세요."
        )
    return fixed


def _applicable(closures: list[Closure] | None, provider: Provider) -> list[Closure]:
    """이 의사에게 적용되는 휴진만 남깁니다. provider_id 가 None 이면 의원 전체."""
    if not closures:
        return []
    return [
        c
        for c in closures
        if c.clinic_id == provider.clinic_id
        and (c.provider_id is None or c.provider_id == provider.id)
    ]


def _blocked(closures: list[Closure], starts_at: datetime, ends_at: datetime) -> bool:
    """반만 걸쳐도 막힌 것으로 봅니다. 반만 진료할 수는 없으니까요."""
    return any(starts_at < c.ends_at and c.starts_at < ends_at for c in closures)


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
    if provider.slot_minutes <= 0:
        raise ValueError(f"slot_minutes 는 양수여야 합니다: {provider.slot_minutes}")
    if until < since:
        return []

    zone = _zone(tz)
    step = timedelta(minutes=provider.slot_minutes)
    blocking = _applicable(closures, provider)

    # 요일 → 근무 구간들. weekday 는 0=월 … 6=일 로 date.weekday() 와 같습니다.
    rows: dict[int, list[ProviderSchedule]] = {}
    for s in schedules:
        if s.provider_id != provider.id:
            continue
        if s.ends_at <= s.starts_at:  # DDL 에도 체크가 있지만 한 번 더 막습니다
            continue
        rows.setdefault(s.weekday, []).append(s)

    drafts: list[SlotDraft] = []
    seen: set[datetime] = set()  # (provider_id, starts_at) 유니크 제약과 같은 기준

    day = since
    while day <= until:
        for row in rows.get(day.weekday(), ()):
            window_end = datetime.combine(day, row.ends_at, tzinfo=zone)
            cursor = datetime.combine(day, row.starts_at, tzinfo=zone)
            while cursor + step <= window_end:
                slot_end = cursor + step
                if cursor not in seen and not _blocked(blocking, cursor, slot_end):
                    seen.add(cursor)
                    drafts.append(
                        SlotDraft(
                            clinic_id=provider.clinic_id,
                            provider_id=provider.id,
                            starts_at=cursor,
                            ends_at=slot_end,
                        )
                    )
                cursor = slot_end
        day += timedelta(days=1)

    drafts.sort(key=lambda d: d.starts_at)
    return drafts


def is_closed(closures: list[Closure], *, provider_id: UUID, at: datetime) -> bool:
    """해당 시각이 휴진인지. provider_id 가 None 인 휴진은 의원 전체 휴진입니다.

    구간은 시작 포함, 끝 제외입니다. 휴진이 끝나는 순간은 진료가 가능합니다.
    """
    return any(
        (c.provider_id is None or c.provider_id == provider_id)
        and c.starts_at <= at < c.ends_at
        for c in closures
    )
