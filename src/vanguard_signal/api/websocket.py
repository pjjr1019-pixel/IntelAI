"""
websocket.py — WebSocket real-time alert push.

Provides a WebSocket endpoint at /ws that broadcasts new alerts
to connected dashboard clients in real-time.

Architecture:
  - ConnectionManager tracks all active WebSocket connections
  - When a new alert is created, call `broadcast_alert()` to push
  - Clients receive JSON with alert data + type tag
  - Supports per-severity filtering (clients subscribe to levels)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

import jwt

# Import config to load .env file
from vanguard_signal import config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(
        self,
        ws: WebSocket,
        severity_filter: set[str] | None = None,
    ) -> None:
        """Add a WebSocket connection to the manager (already accepted)."""
        async with self._lock:
            self._connections[ws] = severity_filter or {"low", "medium", "high", "critical"}
        logger.info(
            "WebSocket connected (%d total). Filter: %s",
            self.active_count,
            severity_filter,
        )

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a disconnected client."""
        async with self._lock:
            self._connections.pop(ws, None)
        logger.info("WebSocket disconnected (%d remaining)", self.active_count)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Send a message to all connected clients whose severity filter
        matches the message severity.
        """
        severity = message.get("severity", "medium")
        dead: list[WebSocket] = []

        async with self._lock:
            targets = list(self._connections.items())

        for ws, filters in targets:
            if severity not in filters:
                continue
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)

    async def send_personal(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Send a message to a specific client."""
        try:
            await ws.send_json(message)
        except Exception:
            await self.disconnect(ws)


# Singleton manager — imported by other modules to broadcast
manager = ConnectionManager()


@router.websocket("/api/ws")
async def websocket_endpoint(
    ws: WebSocket,
    severities: str = Query("low,medium,high,critical"),
    token: str = Query(""),
) -> None:
    """
    WebSocket endpoint for real-time alert streaming.

    Query params:
      severities — comma-separated severity levels to receive
      token      — JWT bearer token for authentication (optional in dev)
    """
    logger.info("WebSocket endpoint called")
    
    # Handle CORS for WebSocket connections
    origin = ws.headers.get("origin", "")
    logger.info(f"WebSocket connection attempt from origin: {origin}")
    
    # Check CORS
    env = os.getenv("VS_ENV", "development")
    if env == "development":
        logger.info(f"Development mode: allowing any origin (received: {origin})")
    elif origin and origin not in allowed_origins:
        logger.error(f"CORS: Origin {origin} not allowed")
        await ws.close(code=4003, reason="CORS not allowed")
        return
    else:
        logger.info(f"CORS: Origin {origin} allowed")

    logger.info(f"WebSocket headers: {dict(ws.headers)}")
    logger.info(f"WebSocket query params: severities={severities}, token={token}")

    try:
        await ws.accept()
        logger.info("WebSocket connection accepted")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection: {e}")
        return

    # Authenticate (skip in dev if no token provided)
    env = os.getenv("VS_ENV", "development")
    logger.info(f"Environment: {env}, token provided: {bool(token)}")
    if token:
        try:
            from vanguard_signal.config import settings as _cfg
            jwt.decode(token, _cfg.jwt.secret, algorithms=[_cfg.jwt.algorithm])
            logger.info("Token authentication successful")
        except jwt.InvalidTokenError as e:
            logger.error(f"Token authentication failed: {e}")
            await ws.close(code=4001, reason="Invalid token")
            return
    elif env != "development":
        logger.info("Authentication required but no token provided")
        await ws.close(code=4001, reason="Authentication required")
        return
    else:
        logger.info("Development mode: allowing connection without token")

    severity_set = set(s.strip().lower() for s in severities.split(","))
    logger.info(f"Connecting with severities: {severity_set}")
    await manager.connect(ws, severity_set)
    logger.info(f"WebSocket connected successfully, active connections: {manager.active_count}")

    try:
        while True:
            # Keep connection alive; also accept commands from client
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                cmd = msg.get("command", "")

                if cmd == "ping":
                    await manager.send_personal(ws, {
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "active_connections": manager.active_count,
                    })
                elif cmd == "subscribe":
                    # Update severity filter
                    new_filters = set(msg.get("severities", []))
                    if new_filters:
                        async with manager._lock:
                            manager._connections[ws] = new_filters
                        await manager.send_personal(ws, {
                            "type": "subscribed",
                            "severities": list(new_filters),
                        })
                elif cmd == "status":
                    await manager.send_personal(ws, {
                        "type": "status",
                        "active_connections": manager.active_count,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except json.JSONDecodeError:
                pass  # Ignore malformed client messages

    except WebSocketDisconnect:
        await manager.disconnect(ws)


@router.websocket("/ws/trends")
async def trends_websocket_endpoint(
    ws: WebSocket,
    geo: str = Query("US", description="ISO country code for trends"),
    token: str = Query(""),
) -> None:
    """
    WebSocket endpoint for real-time trend streaming.

    Pushes live Google Trends data every 30 seconds to connected clients.

    Query params:
      geo   — ISO country code (US, GB, DE, etc.)
      token — JWT bearer token for authentication (optional in dev)
    """
    logger.info("WebSocket endpoint called with geo=%s, token=%s", geo, token)
    
    # Authenticate (skip in dev if no token provided)
    env_check = os.getenv("VS_ENV", "development")
    logger.info("WebSocket auth check: token='%s', env='%s'", token, env_check)
    
    if token:
        try:
            from vanguard_signal.config import settings as _cfg
            jwt.decode(token, _cfg.jwt.secret, algorithms=[_cfg.jwt.algorithm])
            logger.info("WebSocket authenticated with token")
        except jwt.InvalidTokenError:
            logger.error("WebSocket invalid token")
            await ws.close(code=4001, reason="Invalid token")
            return
    elif env_check != "development":
        logger.error("WebSocket auth required but not in development mode")
        await ws.close(code=4001, reason="Authentication required")
        return
    
    logger.info("WebSocket authentication passed")

    await ws.accept()
    logger.info("Trends WebSocket client connected for geo=%s", geo)

    # Send a connection confirmation message
    try:
        await ws.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "WebSocket connected successfully"
        })
        logger.info("Sent connection confirmation message")
    except Exception as e:
        logger.error("Failed to send connection confirmation: %s", e)
        return

    # Import here to avoid importing inside the loop
    from vanguard_signal.api.routes.live_trending import _get_live_trending_internal

    try:
        while True:
            # Fetch latest trends data
            try:
                logger.info("WebSocket: Starting to fetch trends data for geo=%s", geo)
                trends_data = await _get_live_trending_internal(geo=geo, enrich=False)
                
                logger.info("Fetched trends data: %d trends for geo=%s", len(trends_data.trends), geo)
                
                # Create a lighter version for WebSocket to avoid large messages
                light_trends = []
                for trend in trends_data.trends:
                    light_trends.append({
                        "rank": trend.rank,
                        "keyword": trend.keyword,
                        "approx_traffic": trend.approx_traffic,
                        "traffic_value": trend.traffic_value,
                        "sparkline": [],  # Empty to reduce size
                        "current_interest": trend.current_interest,
                        "peak_interest": trend.peak_interest,
                        "velocity": trend.velocity,
                        "acceleration": trend.acceleration,
                        "pct_change_24h": trend.pct_change_24h,
                        "direction": trend.direction,
                        "news": [],  # Empty to reduce size
                        "published_at": trend.published_at,
                        "geo": trend.geo,
                    })
                
                message = {
                    "type": "trends_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "geo": geo,
                    "data": {
                        "trends": light_trends,
                        "total": trends_data.total,
                        "geo": trends_data.geo,
                        "generated_at": trends_data.generated_at,
                        "cached": trends_data.cached,
                    },
                }
                logger.info("WebSocket: Sending message with %d bytes", len(str(message)))
                try:
                    await ws.send_json(message)
                    logger.info("Sent trends update to WebSocket client for geo=%s", geo)
                except Exception as send_exc:
                    logger.error("Failed to send trends update to WebSocket: %s", send_exc)
                    break

            except Exception as exc:
                logger.error("Failed to fetch trends for WebSocket: %s", exc)
                import traceback
                logger.error("Traceback: %s", traceback.format_exc())
                
                # Send error message but don't break the connection
                try:
                    await ws.send_json({
                        "type": "error",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "message": f"Failed to fetch trends data: {str(exc)}",
                    })
                    logger.info("Sent error message to WebSocket client")
                except Exception as send_exc:
                    logger.error("Failed to send error message to WebSocket: %s", send_exc)
                    break  # Break the loop if we can't send messages

            # Push updates every 30 seconds
            await asyncio.sleep(30)

    except WebSocketDisconnect:
        logger.info("Trends WebSocket client disconnected")
    except Exception as exc:
        logger.error("Trends WebSocket error: %s", exc)


@router.get("/ws/test")
async def test_endpoint():
    """Test endpoint to check environment variables."""
    import os
    from vanguard_signal import config
    return {
        "VS_ENV": os.getenv("VS_ENV", "NOT_SET"),
        "config_env": config.settings.env,
        "message": "WebSocket router is loaded"
    }
