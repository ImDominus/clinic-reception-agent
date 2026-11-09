"""환자 식별과 초진/재진 판정."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.errors import PatientNotIdentified
from app.domain.models import VisitType
from app.domain.patients import identify
from tests.conftest import CLINIC, run

PHONE = "01000000001"
ADULT = date(1984, 3, 12)
CHILD = date(2019, 7, 2)


def test_a_missing_birth_date_is_refused(patients):
    """번호만으로 사람을 특정하지 않습니다. 가족이 번호를 공유합니다."""
    with pytest.raises(PatientNotIdentified):
        run(identify(patients, CLINIC, phone=PHONE, birth_date=None))


def test_a_missing_phone_is_refused(patients):
    with pytest.raises(PatientNotIdentified):
        run(identify(patients, CLINIC, phone=None, birth_date=ADULT))


def test_an_unknown_caller_is_a_first_visit(patients):
    ident = run(identify(patients, CLINIC, phone="01099999999", birth_date=ADULT))
    assert ident.visit is VisitType.FIRST
    assert ident.patient is None


def test_a_patient_with_a_completed_visit_is_a_return_visit(patients):
    ident = run(identify(patients, CLINIC, phone=PHONE, birth_date=ADULT))
    assert ident.visit is VisitType.RETURN
    assert ident.patient is not None


def test_a_patient_whose_visits_were_all_cancelled_is_still_a_first_visit(patients):
    """기록은 있지만 온 적이 없습니다. 초진입니다."""
    ident = run(identify(patients, CLINIC, phone="01000000002", birth_date=date(1991, 11, 30)))
    assert ident.visit is VisitType.FIRST
    assert ident.patient is not None


def test_the_same_phone_with_a_different_birth_date_is_a_different_person(patients):
    adult = run(identify(patients, CLINIC, phone=PHONE, birth_date=ADULT))
    child = run(identify(patients, CLINIC, phone=PHONE, birth_date=CHILD))
    assert adult.patient is not None and child.patient is not None
    assert adult.patient.id != child.patient.id
