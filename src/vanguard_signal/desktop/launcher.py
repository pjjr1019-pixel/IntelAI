"""
launcher.py — Desktop entry point for Vanguard Signal.

This is the main script that PyInstaller bundles into the exe.
It:
  1. Sets environment variables for desktop/SQLite mode
  2. Starts the FastAPI server in a background thread
  3. Opens the user's default browser to the dashboard
  4. Creates a small system tray icon (if pystray is installed)
  5. Keeps running until the user closes the tray icon or presses Ctrl+C

Double-click VanguardSignal.exe to launch.
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib import request as urlrequest

# ── Resolve paths (works both dev and frozen-exe) ─────────────────────


def _get_base_dir() -> Path:
    """Return the base directory — handles PyInstaller _MEIPASS."""
    if getattr(sys, "frozen", False):
        # Running as exe — _MEIPASS is the temp unpack dir
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3]  # repo root


BASE_DIR = _get_base_dir()
DATA_DIR = Path(os.getenv("VS_DATA_DIR", str(BASE_DIR / "data")))
STATIC_DIR = BASE_DIR / "dashboard_static"
LOG_FILE = DATA_DIR / "vanguard.log"

# ── Force desktop settings before any vanguard imports ────────────────

os.environ.setdefault("VS_DB_MODE", "sqlite")
os.environ.setdefault("VS_SQLITE_PATH", str(DATA_DIR / "vanguard.db"))
os.environ.setdefault("VS_ENV", "development")
os.environ.setdefault("VS_LOG_LEVEL", "INFO")

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("vanguard.desktop")


# ── Port helpers ──────────────────────────────────────────────────────


def _find_free_port(start: int = 8000, end: int = 8100) -> int:
    """Find the first available TCP port in range."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in {start}-{end}")


def _wait_for_server(port: int, timeout: float = 30.0) -> bool:
    """Block until the server accepts connections (or timeout)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.25)
    return False


# ── Start uvicorn in a daemon thread ─────────────────────────────────

_server_thread: threading.Thread | None = None


def _run_server(port: int) -> None:
    """Run uvicorn synchronously — called inside a daemon thread."""
    import uvicorn

    uvicorn.run(
        "vanguard_signal.api.app:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        # In frozen mode we can't use reload
        reload=False,
    )


def start_server(port: int) -> None:
    global _server_thread
    _server_thread = threading.Thread(
        target=_run_server, args=(port,), daemon=True, name="uvicorn"
    )
    _server_thread.start()
    logger.info("Uvicorn starting on http://127.0.0.1:%d …", port)


# ── System tray (optional — graceful degradation) ────────────────────


def _run_tray(port: int) -> None:
    """Show a system-tray icon with Open / Quit options."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        logger.info(
            "pystray / Pillow not installed — running without tray icon. "
            "Press Ctrl+C to stop."
        )
        # Just block the main thread
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return

    # Create a simple icon — small blue shield
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Shield shape
    draw.rounded_rectangle(
        [8, 4, 56, 52], radius=8, fill=(76, 110, 245, 255)
    )
    draw.polygon([(32, 58), (12, 42), (52, 42)], fill=(76, 110, 245, 255))
    draw.text((22, 14), "VS", fill="white")

    url = f"http://127.0.0.1:{port}"

    def on_open(icon, item):
        webbrowser.open(url)

    def on_quit(icon, item):
        icon.stop()

    icon = pystray.Icon(
        "VanguardSignal",
        img,
        "Vanguard Signal",
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", on_open, default=True),
            pystray.MenuItem(f"Running on port {port}", lambda *a: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", on_quit),
        ),
    )

    logger.info("System tray icon created.")
    icon.run()  # blocks until Quit is chosen


# ── Auto-ingest on startup ────────────────────────────────────────────


def _auto_ingest(port: int) -> None:
    """
    Fire a POST /api/detection/full after launch so the dashboard
    has data immediately instead of showing empty.  Runs in a daemon
    thread — failures are logged but never fatal.
    """
    try:
        import json as _json

        url = f"http://127.0.0.1:{port}/api/detection/full"
        req = urlrequest.Request(url, method="POST", data=b"", headers={
            "Content-Type": "application/json",
        })
        logger.info("Auto-ingest: triggering full pipeline…")
        with urlrequest.urlopen(req, timeout=300) as resp:
            body = _json.loads(resp.read())
            total_events = body.get("ingestion", {}).get("total_events", 0)
            logger.info(
                "Auto-ingest complete: %d events ingested",
                total_events,
            )
    except Exception as exc:
        logger.warning("Auto-ingest failed (non-fatal): %s", exc)


# ── WebSocket listener for desktop notifications ─────────────────────


def _ws_notification_listener(port: int) -> None:
    """
    Connect to the local WS endpoint and show Windows toast
    notifications for high/critical alerts. Reconnects on failure.
    """
    try:
        from vanguard_signal.desktop.notifier import notify_alert, is_available
    except ImportError:
        logger.debug("Notifier unavailable — skipping WS listener")
        return

    if not is_available():
        logger.info("Desktop notifications unavailable (winotify missing)")
        return

    import json as _json

    logger.info("Desktop notification listener starting…")

    while True:
        try:
            import websocket  # websocket-client (bundled with many Python distros)
            ws_url = f"ws://127.0.0.1:{port}/ws?severities=high,critical"
            ws = websocket.create_connection(ws_url, timeout=10)
            logger.info("Notification listener connected to WS")

            while True:
                raw = ws.recv()
                if not raw:
                    break
                try:
                    msg = _json.loads(raw)
                    if msg.get("type") == "alert":
                        notify_alert(msg.get("data", {}), port=port)
                except _json.JSONDecodeError:
                    pass

        except ImportError:
            # websocket-client not installed — use simple polling fallback
            logger.info("websocket-client not installed — using polling for notifications")
            _poll_notification_fallback(port)
            return
        except Exception as exc:
            logger.debug("WS notification listener error: %s — reconnecting in 5s", exc)
            time.sleep(5)


def _poll_notification_fallback(port: int) -> None:
    """
    Fallback: poll /api/dashboard/overview every 60s and notify
    if active critical/high alerts increase.
    """
    import json as _json
    from vanguard_signal.desktop.notifier import notify_alert, is_available

    if not is_available():
        return

    last_active = 0

    while True:
        try:
            url = f"http://127.0.0.1:{port}/api/dashboard/overview"
            req = urlrequest.Request(url, headers={"Accept": "application/json"})
            with urlrequest.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
                active = data.get("active_alerts", 0)
                if active > last_active and last_active > 0:
                    notify_alert({
                        "severity": "high",
                        "primary_entity": "Multiple",
                        "confidence_score": 0.0,
                        "summary": f"{active - last_active} new active alert(s) detected",
                        "id": "",
                    }, port=port)
                last_active = active
        except Exception:
            pass
        time.sleep(60)


# ── Main ──────────────────────────────────────────────────────────────


def main() -> None:
    print(r"""
 ╦  ╦┌─┐┌┐┌┌─┐┬ ┬┌─┐┬─┐┌┬┐  ╔═╗┬┌─┐┌┐┌┌─┐┬
 ╚╗╔╝├─┤│││├─┤│ │├─┤├┬┘ ││  ╚═╗││ ┬│││├─┤│
  ╚╝ ┴ ┴┘└┘┴ ┴└─┘┴ ┴┴└──┴┘  ╚═╝┴└─┘┘└┘┴ ┴┴─┘
  Pre-Event Anomaly Detection Engine  v0.1.0
    """)

    port = _find_free_port()
    logger.info("Database: %s", "SQLite (desktop)" if os.environ.get("VS_DB_MODE") == "sqlite" else "PostgreSQL")
    logger.info("Data dir: %s", DATA_DIR)
    logger.info("Port: %d", port)

    start_server(port)

    url = f"http://127.0.0.1:{port}"

    if _wait_for_server(port):
        logger.info("Server is ready!")
        webbrowser.open(url)

        # Kick off auto-ingest in background (populates dash with data)
        threading.Thread(
            target=_auto_ingest, args=(port,), daemon=True, name="auto-ingest"
        ).start()

        # Start desktop notification listener in background
        threading.Thread(
            target=_ws_notification_listener, args=(port,), daemon=True, name="notifier"
        ).start()
    else:
        logger.error("Server did not start within 30s. Check logs at %s", LOG_FILE)
        sys.exit(1)

    # Run system tray (blocks until quit) or fallback to Ctrl+C wait
    _run_tray(port)

    logger.info("Shutting down…")


if __name__ == "__main__":
    main()
