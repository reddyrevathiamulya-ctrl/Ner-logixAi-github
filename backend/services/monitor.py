from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timezone

from backend.services.data_sources import collect_hazard_data

DEFAULT_INTERVAL_MINUTES = 5
logger = logging.getLogger("ner-logixai.monitor")


def run_collection() -> dict:
    started_at = datetime.now(timezone.utc)
    try:
        result = collect_hazard_data()
        logger.info(
            "Collection completed in %.1fs: flood=%d landslide=%d weather=%d rainfall=%d",
            (datetime.now(timezone.utc) - started_at).total_seconds(),
            result["flood"]["observation_count"],
            result["landslide"]["observation_count"],
            len(result["weather"]),
            len(result["rainfall"]),
        )
        return result
    except Exception:
        logger.exception("Collection failed; existing cached data was preserved")
        return {}


def run_forever(interval_minutes: int = DEFAULT_INTERVAL_MINUTES) -> None:
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be at least 1")

    logger.info("Starting NER-LogixAI monitor with %d-minute interval", interval_minutes)
    while True:
        run_collection()
        time.sleep(interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NER-LogixAI data monitoring")
    parser.add_argument(
        "--once",
        action="store_true",
        help="collect once and exit",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=DEFAULT_INTERVAL_MINUTES,
        help="minutes between checks (default: 5)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.once:
        run_collection()
    else:
        run_forever(args.interval_minutes)


if __name__ == "__main__":
    main()
