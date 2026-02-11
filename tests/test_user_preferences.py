import os
from fastapi.testclient import TestClient


def test_user_preferences_anonymous_returns_404():
    os.environ["VS_DB_MODE"] = "sqlite"
    # import app after env is set
    from vanguard_signal.api.app import app

    client = TestClient(app)
    r = client.get("/api/user/preferences")
    assert r.status_code == 404
