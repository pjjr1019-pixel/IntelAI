import os
from fastapi.testclient import TestClient


def test_trending_history_fallback_mock(monkeypatch):
    os.environ["VS_DB_MODE"] = "sqlite"

    # Create a fake connector class to patch into the module
    class FakeConnector:
        def __init__(self):
            self._geo = ""
            self._timeframe = "now 7-d"
            self._delay = 0.0

        async def fetch_raw(self, keywords):
            # Return a simple payload with two points
            payload = {
                "interest_over_time": {
                    "2026-02-10T00:00:00+00:00": {keywords[0]: 10},
                    "2026-02-11T00:00:00+00:00": {keywords[0]: 20},
                }
            }
            return payload, 0.01

    # Patch the class in the connectors module so the route will instantiate FakeConnector
    import importlib
    mod = importlib.import_module("vanguard_signal.ingestion.connectors.google_trends")
    monkeypatch.setattr(mod, "GoogleTrendsConnector", FakeConnector)

    # Import app after monkeypatch so route uses the fake connector
    from vanguard_signal.api.app import app

    client = TestClient(app)

    r = client.get("/api/trending/history/test-keyword?time_range=7d", timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert j["keyword"] == "test-keyword"
    assert "data_points" in j
    assert len(j["data_points"]) == 2
    # velocities: first None, second should be numeric
    assert j["data_points"][0]["velocity"] is None
    assert isinstance(j["data_points"][1]["velocity"], float)
