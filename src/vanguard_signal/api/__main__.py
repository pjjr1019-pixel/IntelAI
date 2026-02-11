"""
__main__.py — Launch the Vanguard Signal API server.

Usage:
    python -m vanguard_signal.api               # dev mode with reload
    python -m vanguard_signal.api --port 8080   # custom port
    python -m vanguard_signal.api --prod        # production (no reload)
"""

from __future__ import annotations

import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Vanguard Signal API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--prod", action="store_true", help="Production mode (no reload)")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers (prod)")
    parser.add_argument("--fast", action="store_true", help="Fast startup mode (skip some checks)")
    args = parser.parse_args()

    # Set environment variable for fast mode
    if args.fast:
        import os
        os.environ["VANGUARD_FAST_STARTUP"] = "1"

    uvicorn.run(
        "vanguard_signal.api.app:app",
        host=args.host,
        port=args.port,
        reload=not args.prod,
        workers=args.workers if args.prod else 1,
        log_level="warning" if args.fast else "info",  # Reduce logging in fast mode
        access_log=False if args.fast else True,  # Disable access logs in fast mode
    )


if __name__ == "__main__":
    main()
