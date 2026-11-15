"""예약 코어. 이 파일이 M1 의 정의입니다.

전부 빨간불입니다. 구현이 없으니까요. 테스트 본문은 최종 형태입니다.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.domain.errors import DomainError, SlotInPast, SlotNotFound, SlotTaken
from app.domain.models import AppointmentStatus, VisitType
from app.domain.scheduling import MAX_SUGGESTIONS, book, cancel, find_slots, reschedule
from tests.conftest import CLINIC, DEPT_PEDS, PATIENT, SLOT_A, SLOT_B, SLOT_C, run, uid

KEY = "call-0001:book"


# --- 후보 찾기 ---------------------------------------------------------------


def test_suggests_at_most_three(slots, now):
    """전화로 후보를 열 개 읽어줄 수는 없습니다. 음성 채널의 제약입니다."""
    found = run(find_slots(slots, CLINIC, now=now, visit=VisitType.RETURN))
    assert len(found) <= MAX_SUGGESTIONS


def test_never_suggests_a_slot_in_the_past(slots, now):
    found = run(find_slots(slots, CLINIC, now=now, visit=VisitType.RETURN))
    assert all(s.starts_at > now for s in found)


def test_a_slot_starting_exactly_now_is_not_suggested(slots, now):
    """경계. 지금 시작하는 진료를 지금 예약하라고 말할 수 없습니다."""
    found = run(find_slots(slots, CLINIC, now=now, visit=VisitType.RETURN))
    assert all(s.starts_at != now for s in found)


def test_only_open_slots_are_suggested(slots, now):
    found = run(find_slots(slots, CLINIC, now=now, visit=VisitType.RETURN))
    assert all(s.open for s in found)


def test_no_candidates_is_an_empty_list_not_an_error(slots, now):
    """자리가 없다는 것도 정상 응답입니다. 예외로 올리면 에이전트가 사과부터 합니다."""
    found = run(find_slots(slots, CLINIC, now=now + timedelta(days=3650), visit=VisitType.RETURN))
    assert found == []


def test_a_department_filter_narrows_the_result(slots, now):
    found = run(find_slots(slots, CLINIC, now=now, visit=VisitType.FIRST, department_id=DEPT_PEDS))
    assert found is not None


# --- 예약 -------------------------------------------------------------------


def test_booking_a_free_slot_returns_a_booked_appointment(slots, appointments, now):
    appt = run(
        book(
            slots,
            appointments,
            CLINIC,
            slot_id=SLOT_A,
            patient_id=PATIENT,
            visit=VisitType.FIRST,
            idempotency_key=KEY,
            now=now,
        )
    )
    assert appt.status is AppointmentStatus.BOOKED
    assert appt.slot_id == SLOT_A


def test_the_same_idempotency_key_returns_the_original_appointment(slots, appointments, now):
    """통화는 끊기고 재시도는 일어납니다. 두 건 잡히면 안 됩니다."""

    def once():
        return run(
            book(
                slots,
                appointments,
                CLINIC,
                slot_id=SLOT_A,
                patient_id=PATIENT,
                visit=VisitType.FIRST,
                idempotency_key=KEY,
                now=now,
            )
        )

    assert once().id == once().id


def test_a_different_key_on_a_taken_slot_is_rejected(slots, appointments, now):
    with pytest.raises(SlotTaken):
        run(
            book(
                slots,
                appointments,
                CLINIC,
                slot_id=SLOT_A,
                patient_id=PATIENT,
                visit=VisitType.RETURN,
                idempotency_key="call-0002:book",
                now=now,
            )
        )


def test_booking_a_past_slot_is_rejected(slots, appointments, now):
    with pytest.raises(SlotInPast):
        run(
            book(
                slots,
                appointments,
                CLINIC,
                slot_id=SLOT_A,
                patient_id=PATIENT,
                visit=VisitType.RETURN,
                idempotency_key=KEY,
                now=now + timedelta(days=30),
            )
        )


def test_booking_a_slot_that_does_not_exist_is_rejected(slots, appointments, now):
    """모델이 slot_id 를 지어낼 수 있습니다. 코어가 막습니다."""
    with pytest.raises(SlotNotFound):
        run(
            book(
                slots,
                appointments,
                CLINIC,
                slot_id=uid(999999),
                patient_id=PATIENT,
                visit=VisitType.RETURN,
                idempotency_key=KEY,
                now=now,
            )
        )


@pytest.mark.db
def test_two_simultaneous_bookings_and_only_one_wins(pg_dsn):
    """같은 슬롯을 두 통화가 동시에 잡으려 할 때.

    애플리케이션 락이 아니라 appointments_active_slot 유니크 인덱스가 판정합니다.
    그래서 이 테스트는 실제 Postgres 가 있어야 의미가 있습니다.
    """
    raise NotImplementedError("M1")


# --- 취소 -------------------------------------------------------------------


def test_cancelling_reopens_the_slot(slots, appointments, now):
    appt = run(cancel(slots, appointments, appointment_id=uid(50), now=now))
    assert appt.status is AppointmentStatus.CANCELLED
    reopened = run(find_slots(slots, CLINIC, now=now, visit=VisitType.RETURN))
    assert any(s.id == appt.slot_id for s in reopened)


def test_cancelling_twice_is_idempotent(slots, appointments, now):
    first = run(cancel(slots, appointments, appointment_id=uid(50), now=now))
    second = run(cancel(slots, appointments, appointment_id=uid(50), now=now))
    assert first.id == second.id


def test_a_completed_visit_cannot_be_cancelled(slots, appointments, now):
    with pytest.raises(DomainError):
        run(cancel(slots, appointments, appointment_id=uid(51), now=now))


# --- 변경 -------------------------------------------------------------------


def test_rescheduling_releases_the_old_slot(slots, appointments, now):
    appt = run(
        reschedule(
            slots,
            appointments,
            appointment_id=uid(50),
            new_slot_id=SLOT_B,
            idempotency_key="call-0003:move",
            now=now,
        )
    )
    assert appt.slot_id == SLOT_B
    freed = run(find_slots(slots, CLINIC, now=now, visit=VisitType.RETURN))
    assert any(s.id == SLOT_A for s in freed)


def test_a_failed_reschedule_keeps_the_original_appointment(slots, appointments, now):
    """먼저 취소하고 다음에 잡는 순서는 금지입니다.

    중간에 실패하면 환자는 예약을 잃습니다. 한 트랜잭션이어야 합니다.

    목적지는 SLOT_C 입니다 — 시드에서 이미 예약이 붙어 있는 슬롯이라 점유가
    반드시 실패합니다. SLOT_B 는 비어 있어서(변경 성공 테스트의 목적지)
    여기 쓰면 실패 경로를 타지 않습니다.
    """
    with pytest.raises(SlotTaken):
        run(
            reschedule(
                slots,
                appointments,
                appointment_id=uid(50),
                new_slot_id=SLOT_C,
                idempotency_key="call-0004:move",
                now=now,
            )
        )
    still = run(find_slots(slots, CLINIC, now=now, visit=VisitType.RETURN))
    assert all(s.id != SLOT_A for s in still), "실패한 변경이 원래 슬롯을 열어버렸습니다"


def test_rescheduling_to_the_same_slot_does_nothing(slots, appointments, now):
    appt = run(
        reschedule(
            slots,
            appointments,
            appointment_id=uid(50),
            new_slot_id=SLOT_A,
            idempotency_key="call-0005:move",
            now=now,
        )
    )
    assert appt.slot_id == SLOT_A
    assert appt.status is AppointmentStatus.BOOKED
