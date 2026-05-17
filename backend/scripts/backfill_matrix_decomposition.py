"""Backfill cost-decomposition columns on vehicle_matrix_cache.

After migration 20260516210000_extend_matrix_cache_with_breakdown.sql adds the
`utrata_wartosci_pln`, `koszty_serwisowe_pln`, `koszt_opon_pln`,
`ubezpieczenie_pln`, `wr_pct` columns, existing rows stay NULL until the next
refresh. This script finds every kalkulacja_id whose cache still has NULL
decomposition and re-runs `process_single_kalkulacja_matrix_task` so the new
columns get populated. The upsert is idempotent
(on_conflict=kalkulacja_id,duration_months,annual_mileage).

Usage:
    python -m backend.scripts.backfill_matrix_decomposition --limit 50 --dry-run
    python -m backend.scripts.backfill_matrix_decomposition --limit 50
    python -m backend.scripts.backfill_matrix_decomposition           # all
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Iterator

from supabase import Client

from backend.core.matrix_cache_job import (
    _get_admin_supabase,
    process_single_kalkulacja_matrix_task,
)

logger = logging.getLogger("backfill_matrix_decomposition")


def _iter_pending_kalkulacja_ids(client: Client, page_size: int = 1000) -> Iterator[str]:
    """Yield distinct kalkulacja_id whose cache rows still lack decomposition."""
    seen: set[str] = set()
    offset = 0
    while True:
        res = (
            client.table("vehicle_matrix_cache")
            .select("kalkulacja_id")
            .is_("utrata_wartosci_pln", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return
        for r in rows:
            kid = r.get("kalkulacja_id")
            if kid and kid not in seen:
                seen.add(kid)
                yield kid
        if len(rows) < page_size:
            return
        offset += page_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N kalkulacja_ids (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print kalkulacja_ids that would be refreshed.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between kalkulacje (default: 0).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    client = _get_admin_supabase()
    ids = list(_iter_pending_kalkulacja_ids(client))
    total = len(ids)
    if args.limit is not None:
        ids = ids[: args.limit]

    logger.info(
        "Pending kalkulacje with NULL decomposition: %d (processing %d)",
        total,
        len(ids),
    )

    if args.dry_run:
        for kid in ids:
            print(kid)
        return 0

    ok = 0
    fail = 0
    for i, kid in enumerate(ids, 1):
        try:
            process_single_kalkulacja_matrix_task(
                kalkulacja_id=kid,
                trace_id=f"backfill-decomposition-{i}",
            )
            ok += 1
        except Exception as exc:  # noqa: BLE001 — log and keep going
            fail += 1
            logger.error("Failed kalkulacja %s: %s", kid, exc)
        if i % 25 == 0:
            logger.info("Progress: %d/%d (ok=%d fail=%d)", i, len(ids), ok, fail)
        if args.sleep > 0:
            time.sleep(args.sleep)

    logger.info("Backfill complete: ok=%d fail=%d total=%d", ok, fail, len(ids))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
