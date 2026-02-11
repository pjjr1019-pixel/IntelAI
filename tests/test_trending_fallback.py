import os
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "0") != "1",
    reason="Run live connector tests only when RUN_LIVE_TESTS=1",
)


def test_trending_history_live_fallback_returns_data():
    os.environ["VS_DB_MODE"] = "sqlite"
    # import app after env is set
    from vanguard_signal.api.app import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    r = client.get("/api/trending/history/test-keyword?time_range=7d", timeout=60)
    assert r.status_code == 200
    j = r.json()
    assert "data_points" in j
    assert isinstance(j["data_points"], list)
    assert len(j["data_points"]) > 0
