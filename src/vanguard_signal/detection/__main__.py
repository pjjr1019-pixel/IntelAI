"""
__main__.py — CLI entry point for the anomaly detection engine.

Usage:
    python -m vanguard_signal.detection                     # run once (daily)
    python -m vanguard_signal.detection --bucket hour       # hourly buckets
    python -m vanguard_signal.detection --threshold 0.5     # lower sensitivity
    python -m vanguard_signal.detection --loop --interval 3600  # continuous

This can run standalone or be triggered by the ingestion scheduler
after each data pull cycle completes.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vanguard Signal — Anomaly Detection Engine",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        default="day",
        choices=["hour", "day", "week", "month"],
        help="Time bucket granularity (default: day)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Ensemble score threshold for flagging anomalies (default: 0.6)",
    )
    parser.add_argument(
        "--min-points",
        type=int,
        default=7,
        help="Minimum data points per entity before detection runs (default: 7)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously instead of once",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Seconds between detection cycles in loop mode (default: 3600)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    _configure_logging(args.log_level)

    from vanguard_signal.detection.pipeline import run_detection_cycle
    from vanguard_signal.schema.enums import TimeBucket

    bucket_map = {
        "hour": TimeBucket.HOUR,
        "day": TimeBucket.DAY,
        "week": TimeBucket.WEEK,
        "month": TimeBucket.MONTH,
    }
    bucket_size = bucket_map[args.bucket]

    if args.loop:
        asyncio.run(
            _run_loop(
                bucket_size=bucket_size,
                threshold=args.threshold,
                min_points=args.min_points,
                interval=args.interval,
            )
        )
    else:
        result = asyncio.run(
            run_detection_cycle(
                bucket_size=bucket_size,
                min_series_length=args.min_points,
                ensemble_threshold=args.threshold,
            )
        )
        print(f"\nDetection complete: {result}")


async def _run_loop(
    bucket_size: "TimeBucket",
    threshold: float,
    min_points: int,
    interval: int,
) -> None:
    """Continuous detection loop."""
    from vanguard_signal.detection.pipeline import run_detection_cycle

    logger = logging.getLogger(__name__)
    cycle = 0

    while True:
        cycle += 1
        logger.info("── Detection cycle %d at %s ──", cycle, datetime.now(timezone.utc))

        try:
            result = await run_detection_cycle(
                bucket_size=bucket_size,
                min_series_length=min_points,
                ensemble_threshold=threshold,
            )
            logger.info("Cycle %d result: %s", cycle, result)
        except Exception as exc:
            logger.critical("Detection cycle %d failed: %s", cycle, exc, exc_info=True)

        logger.info("Sleeping %ds until next detection cycle…", interval)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    main()
