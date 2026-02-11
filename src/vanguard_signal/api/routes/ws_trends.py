"""
ws_trends.py — WebSocket endpoints for real-time trends.

This lightweight router exposes a websocket at `/ws/trends` that
pushes `LiveTrendingResponse` updates periodically.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from vanguard_signal.api.routes.live_trending import _get_live_trending_internal, LiveTrendingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/trends")
async def websocket_trends(websocket: WebSocket):
    """Simple websocket that periodically pushes live trends.

    Query params:
      - geo: ISO country code (default: US)
      - enrich: true/false (default: false)
      - interval: seconds between pushes (clamped 5..60, default: 10)
    """
    await websocket.accept()
    params = websocket.query_params
    geo = params.get("geo", "US")
    enrich = params.get("enrich", "false").lower() in ("1", "true", "yes")
    try:
        interval = int(params.get("interval", "10"))
    except Exception:
        interval = 10

    # Clamp interval to reasonable bounds to avoid abuse
    interval = max(5, min(60, interval))

    logger.info(f"WebSocket client connected for trends geo={geo} enrich={enrich} interval={interval}s")

    try:
        while True:
            try:
                # Fetch the latest trends (uses internal cache)
                resp: LiveTrendingResponse = await _get_live_trending_internal(geo=geo, enrich=enrich)
                payload = {"type": "trends_update", "data": resp.model_dump()}
                await websocket.send_json(payload)
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected (trends)")
                break
            except asyncio.CancelledError:
                logger.info("WebSocket handler cancelled (trends)")
                break
            except Exception as exc:
                # Log and break on unexpected send failures to avoid tight error loops
                logger.exception("WebSocket send error (trends): %s", exc)
                try:
                    await websocket.close()
                except Exception:
                    pass
                break

            # Respect client-requested interval
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
