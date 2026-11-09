import pytest

pytest.importorskip("fastapi", reason="make install 전에는 건너뜁니다")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health_reports_the_latency_budget():
    body = TestClient(app).get("/health").json()
    assert body["status"] == "ok"
    assert body["latency_budget_ms"] == 800


def test_health_admits_the_vendors_are_undecided():
    body = TestClient(app).get("/health").json()
    assert body["vendors"]["stt"] == "undecided"
