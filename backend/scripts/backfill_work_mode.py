"""Detect work mode for offers stored before the column existed.

Detection is deterministic and local — no LLM, no network, no cost — so this is
safe to re-run. Offers that already have a mode are left alone; pass --force to
recompute them after editing the keyword sets in aje.discovery.work_mode.

    cd backend && uv run python -m scripts.backfill_work_mode [--force] [--dry-run]
"""
import argparse
from collections import Counter

from sqlalchemy import select

from aje.db import get_session
from aje.discovery.work_mode import detect_work_mode
from aje.models import Offer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force", action="store_true", help="recompute offers that already have one"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report the outcome, write nothing"
    )
    args = parser.parse_args()

    session = get_session()
    try:
        offers = list(session.execute(select(Offer)).scalars())
        counts: Counter[str] = Counter()
        changed = 0

        for offer in offers:
            if offer.work_mode is not None and not args.force:
                counts["skipped (already set)"] += 1
                continue
            detected = detect_work_mode(
                title=offer.title,
                location=offer.location,
                description=offer.description,
            )
            counts[detected or "unstated"] += 1
            if detected != offer.work_mode:
                offer.work_mode = detected
                changed += 1

        if args.dry_run:
            session.rollback()
        else:
            session.commit()

        print(f"{len(offers)} offers examined, {changed} updated"
              f"{' (dry run, nothing written)' if args.dry_run else ''}")
        for label, count in counts.most_common():
            print(f"  {label:24} {count}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
