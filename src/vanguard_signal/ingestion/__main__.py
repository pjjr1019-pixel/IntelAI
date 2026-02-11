"""
__main__.py — CLI entry point for the ingestion engine.

Usage:
    python -m vanguard_signal.ingestion                    # run forever
    python -m vanguard_signal.ingestion --once             # single cycle
    python -m vanguard_signal.ingestion --cycles 5         # 5 cycles then stop
    python -m vanguard_signal.ingestion --interval 600     # every 10 minutes

This lets you start ingestion standalone (for testing or cron jobs)
without needing the full FastAPI server running.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vanguard Signal — Ingestion Engine",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single ingestion cycle and exit",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Run N cycles then exit (default: run forever)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Seconds between cycles (default: VS_INGEST_INTERVAL or 3600)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    _configure_logging(args.log_level)

    from vanguard_signal.ingestion.scheduler import (
        run_ingestion_cycle,
        start_scheduler,
    )

    if args.once:
        asyncio.run(run_ingestion_cycle())
    else:
        asyncio.run(
            start_scheduler(
                interval_seconds=args.interval,
                max_cycles=args.cycles,
            )
        )


if __name__ == "__main__":
    main()
