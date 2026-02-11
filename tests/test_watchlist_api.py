import os
import json
from fastapi.testclient import TestClient


def test_watchlist_get_and_modify(tmp_path):
    watchlist_file = tmp_path / "watchlist.json"
    # ensure env var is set before importing app
    os.environ["VS_WATCHLIST_PATH"] = str(watchlist_file)
    os.environ["VS_DB_MODE"] = "sqlite"

    from vanguard_signal.api.app import app

    client = TestClient(app)

    # GET initial watchlist
    r = client.get("/api/watchlist")
    assert r.status_code == 200
    j = r.json()
    assert "categories" in j and "total_keywords" in j

    # Add a keyword
    payload = {"keyword": "Unit Test Keyword", "category": "tests"}
    r = client.post("/api/watchlist/keywords", json=payload)
    assert r.status_code == 201
    added = r.json()
    assert added["status"] == "added"

    # Flat list should include the new keyword
    r = client.get("/api/watchlist/flat")
    assert r.status_code == 200
    flat = r.json()
    assert "Unit Test Keyword" in flat.get("keywords", [])

    # Remove the keyword
    r = client.delete("/api/watchlist/keywords", params={"keyword": "Unit Test Keyword"})
    assert r.status_code == 200
    assert r.json().get("status") == "removed"

    # Ensure it's no longer present
    r = client.get("/api/watchlist/flat")
    assert "Unit Test Keyword" not in r.json().get("keywords", [])
