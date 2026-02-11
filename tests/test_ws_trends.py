import pytest

from fastapi.testclient import TestClient


def test_ws_trends_push(monkeypatch):
    # Replace the real fetcher with a lightweight fake to avoid network calls
    from vanguard_signal.api.routes.live_trending import LiveTrendingResponse, LiveTrendingEntity

    async def _fake_get(geo: str = "US", enrich: bool = False):
        return LiveTrendingResponse(
            trends=[
                LiveTrendingEntity(
                    rank=1,
                    keyword="test-keyword",
                    approx_traffic="10+",
                    traffic_value=10,
                    sparkline=[],
                    current_interest=0.0,
                    peak_interest=0.0,
                    velocity=0.0,
                    acceleration=0.0,
                    pct_change_24h=0.0,
                    direction="flat",
                    news=[],
                    published_at="",
                    geo=geo,
                )
            ],
            total=1,
            geo=geo,
            generated_at="now",
        )

    monkeypatch.setattr(
        "vanguard_signal.api.routes.live_trending._get_live_trending_internal",
        _fake_get,
    )

    from vanguard_signal.api.app import app

    with TestClient(app) as client:
        with client.websocket_connect("/ws/trends?geo=US&interval=5") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "trends_update"
            assert msg["data"]["total"] == 1
