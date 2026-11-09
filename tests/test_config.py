from app.config import Settings


def test_defaults_point_at_the_local_dev_database():
    s = Settings()
    assert "localhost:5433" in s.database_url
    assert s.clinic_tz == "Asia/Seoul"


def test_vendors_start_undecided():
    s = Settings()
    assert (s.stt_provider, s.tts_provider, s.llm_provider) == ("", "", "")


def test_env_overrides_defaults():
    s = Settings.from_env({"CLINIC_TZ": "UTC", "LATENCY_BUDGET_MS": "500"})
    assert s.clinic_tz == "UTC"
    assert s.latency_budget_ms == 500


def test_latency_budget_is_800ms_by_default():
    """docs/architecture.md 2절의 목표치. 바꾸려면 근거를 같이 바꿔야 합니다."""
    assert Settings().latency_budget_ms == 800
