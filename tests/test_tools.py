"""툴 명세 자체에 대한 테스트.

툴을 늘리거나 설명을 흐리게 고치면 여기서 걸립니다.
"""

from app.agent.tools import TOOLS


def test_there_are_exactly_four_tools():
    assert len(TOOLS) == 4


def test_tool_names_are_unique():
    names = [t.name for t in TOOLS]
    assert len(set(names)) == len(names)


def test_every_tool_has_a_description():
    for t in TOOLS:
        assert len(t.description) > 30, t.name


def test_required_params_are_declared_in_parameters():
    for t in TOOLS:
        for key in t.required:
            assert key in t.parameters, f"{t.name}: {key}"


def test_booking_requires_a_slot_id_it_did_not_invent():
    book = next(t for t in TOOLS if t.name == "book_appointment")
    assert "slot_id" in book.required
    assert "find_slots" in book.parameters["slot_id"]["description"]


def test_escalation_names_the_out_of_scope_topics():
    esc = next(t for t in TOOLS if t.name == "escalate_to_human")
    for topic in ("증상", "진단", "복약", "보험"):
        assert topic in esc.description
