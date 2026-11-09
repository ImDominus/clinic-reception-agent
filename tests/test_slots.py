"""근무표 → 슬롯 실체화. 순수 함수라 DB 없이 전부 검증됩니다.

날짜·시간 경계가 이 프로젝트에서 제일 자주 깨지는 곳입니다. 그래서 여기가
테스트가 제일 두껍습니다.
"""

from __future__ import annotations

from datetime import date, datetime, time

import pytest

from app.domain.models import Closure, Provider, ProviderSchedule
from app.domain.slots import is_closed, materialize_slots
from tests.conftest import (
    CLINIC,
    DEPT_INTERNAL,
    KST,
    PROVIDER_A,
    PROVIDER_B,
    uid,
)

MONDAY = date(2026, 12, 7)
SUNDAY = date(2026, 12, 13)


def provider(slot_minutes: int = 15) -> Provider:
    return Provider(
        id=PROVIDER_A,
        clinic_id=CLINIC,
        department_id=DEPT_INTERNAL,
        name="김해원",
        slot_minutes=slot_minutes,
    )


def schedule(weekday: int, start: time, end: time, n: int = 100) -> ProviderSchedule:
    return ProviderSchedule(
        id=uid(n), provider_id=PROVIDER_A, weekday=weekday, starts_at=start, ends_at=end
    )


def test_each_interval_becomes_one_slot():
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(9, 0), time(13, 0))],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
    )
    assert len(drafts) == 16
    assert drafts[0].starts_at == datetime(2026, 12, 7, 9, 0, tzinfo=KST)


def test_the_last_slot_does_not_run_past_closing_time():
    """09:00-13:10 을 20분으로 자르면 12.5칸. 꼬리 10분은 버립니다."""
    drafts = materialize_slots(
        provider(20),
        [schedule(0, time(9, 0), time(13, 10))],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
    )
    assert len(drafts) == 12
    assert drafts[-1].ends_at == datetime(2026, 12, 7, 13, 0, tzinfo=KST)


def test_lunch_is_a_gap_between_two_schedule_rows():
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(9, 0), time(13, 0), 100), schedule(0, time(14, 0), time(18, 0), 101)],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
    )
    starts = {d.starts_at.time() for d in drafts}
    assert time(12, 45) in starts
    assert time(14, 0) in starts
    for t in (time(13, 0), time(13, 15), time(13, 30), time(13, 45)):
        assert t not in starts


def test_slots_come_back_sorted_and_without_duplicates():
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(14, 0), time(18, 0), 101), schedule(0, time(9, 0), time(13, 0), 100)],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
    )
    starts = [d.starts_at for d in drafts]
    assert starts == sorted(starts)
    assert len(set(starts)) == len(starts)


def test_a_weekday_with_no_schedule_row_produces_nothing():
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(9, 0), time(13, 0))],
        since=SUNDAY,
        until=SUNDAY,
        tz="Asia/Seoul",
    )
    assert drafts == []


def test_the_until_date_is_included():
    drafts = materialize_slots(
        provider(15),
        [schedule(wd, time(9, 0), time(10, 0), 100 + wd) for wd in range(0, 5)],
        since=MONDAY,
        until=date(2026, 12, 11),
        tz="Asia/Seoul",
    )
    days = {d.starts_at.date() for d in drafts}
    assert date(2026, 12, 11) in days
    assert len(days) == 5


def test_a_clinic_wide_closure_wipes_the_day():
    closure = Closure(
        id=uid(200),
        clinic_id=CLINIC,
        provider_id=None,
        starts_at=datetime(2026, 12, 7, 0, 0, tzinfo=KST),
        ends_at=datetime(2026, 12, 8, 0, 0, tzinfo=KST),
        reason="휴진",
    )
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(9, 0), time(13, 0))],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
        closures=[closure],
    )
    assert drafts == []


def test_another_providers_closure_does_not_touch_this_one():
    closure = Closure(
        id=uid(201),
        clinic_id=CLINIC,
        provider_id=PROVIDER_B,
        starts_at=datetime(2026, 12, 7, 0, 0, tzinfo=KST),
        ends_at=datetime(2026, 12, 8, 0, 0, tzinfo=KST),
        reason="학회",
    )
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(9, 0), time(13, 0))],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
        closures=[closure],
    )
    assert len(drafts) == 16


def test_a_slot_only_half_covered_by_a_closure_is_still_dropped():
    """09:00-09:10 휴진이면 09:00 슬롯(15분)은 만들지 않습니다. 반만 진료할 수는 없습니다."""
    closure = Closure(
        id=uid(202),
        clinic_id=CLINIC,
        provider_id=PROVIDER_A,
        starts_at=datetime(2026, 12, 7, 9, 0, tzinfo=KST),
        ends_at=datetime(2026, 12, 7, 9, 10, tzinfo=KST),
    )
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(9, 0), time(13, 0))],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
        closures=[closure],
    )
    assert len(drafts) == 15
    assert drafts[0].starts_at.time() == time(9, 15)


def test_slots_are_timezone_aware():
    drafts = materialize_slots(
        provider(15),
        [schedule(0, time(9, 0), time(10, 0))],
        since=MONDAY,
        until=MONDAY,
        tz="Asia/Seoul",
    )
    assert drafts[0].starts_at.utcoffset() is not None


def test_is_closed_reads_a_null_provider_as_the_whole_clinic():
    closure = Closure(
        id=uid(203),
        clinic_id=CLINIC,
        provider_id=None,
        starts_at=datetime(2026, 12, 7, 0, 0, tzinfo=KST),
        ends_at=datetime(2026, 12, 8, 0, 0, tzinfo=KST),
    )
    assert is_closed(
        [closure], provider_id=PROVIDER_B, at=datetime(2026, 12, 7, 11, 0, tzinfo=KST)
    )


@pytest.mark.skip(reason="설계 미결 — docs/open-questions.md 1번")
def test_a_first_visit_needs_a_longer_appointment():
    """초진 진료시간이 재진보다 길다면, 지금 스키마(appointments.slot_id 하나)로는
    표현이 안 됩니다. 연속 슬롯 묶음으로 갈지, 초진 전용 근무구간을 둘지 미결입니다.
    """
