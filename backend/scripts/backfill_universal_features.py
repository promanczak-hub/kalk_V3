"""Backfill universal features for vehicles that have card_summary but
no `vehicle_feature_evidence` rows yet.

Background:
    The extraction pipeline calls `enrich_vehicle_features` in phase_2_mapping
    before flipping `verification_status` to 'completed'. Older vehicles
    completed before that step landed (or whose enrich step crashed) are
    stuck with `card_summary.standard_equipment` populated but no resolved
    universal features — so the "Cechy użytkowe pojazdu" card is empty.

This script:
    1. Selects vehicles with `verification_status = 'completed'` AND no
       evidence rows in `reverse_search.vehicle_feature_evidence`.
    2. Calls `enrich_vehicle_features` for each (LLM-based matcher +
       resolver) — same path the live pipeline uses.
    3. Sleeps 2s between vehicles to stay below LLM rate limits.

Usage:
    cd backend
    python scripts/backfill_universal_features.py             # all stuck
    python scripts/backfill_universal_features.py --limit 5   # first 5
    python scripts/backfill_universal_features.py --vehicle-id <uuid>
    python scripts/backfill_universal_features.py --reenrich --since 2026-04-15
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import supabase
from core.feature_enrichment import enrich_vehicle_features


def _stuck_vehicle_ids(
    limit: int | None,
    reenrich: bool = False,
    since: str | None = None,
) -> list[str]:
    """Return ids of completed vehicles to enrich.

    Default behaviour: only vehicles with no evidence rows yet ("stuck").
    `reenrich=True` skips the no-evidence filter, so already-enriched vehicles
    are re-processed too (used after fixing a feature_key mapping bug to add
    missing evidence — `enrich_vehicle_features` upserts, so this is safe).
    `since` (ISO date string) further restricts to vehicles created on/after
    that date.
    """
    query = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, synthesis_data, created_at")
        .eq("verification_status", "completed")
    )
    if since:
        query = query.gte("created_at", since)
    completed = (query.execute()).data or []

    if reenrich:
        enriched_ids: set[str] = set()
    else:
        ev_resp = (
            supabase.schema("reverse_search")
            .table("vehicle_feature_evidence")
            .select("source_vehicle_id")
            .execute()
        )
        enriched_ids = {row["source_vehicle_id"] for row in (ev_resp.data or [])}

    selected: list[tuple[str, str, str]] = []
    for v in completed:
        vid = v["id"]
        if vid in enriched_ids:
            continue
        synth = v.get("synthesis_data") or {}
        cs = synth.get("card_summary") or {}
        if not isinstance(cs, dict) or not cs:
            continue
        selected.append((vid, v.get("brand") or "?", v.get("model") or "?"))

    if limit is not None:
        selected = selected[:limit]
    label = "to re-enrich" if reenrich else "without evidence"
    print(f"Found {len(selected)} completed vehicles {label}.")
    for vid, brand, model in selected:
        print(f"  {vid}  {brand} {model}")
    return [vid for vid, _, _ in selected]


async def _enrich_one(vehicle_id: str) -> dict:
    resp = (
        supabase.table("vehicle_synthesis")
        .select("synthesis_data")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return {"error": "not found"}
    synth = resp.data[0].get("synthesis_data")
    if not isinstance(synth, dict):
        return {"error": "no synthesis_data"}
    return await enrich_vehicle_features(vehicle_id, synth)


async def _main(vehicle_ids: list[str]) -> None:
    total = len(vehicle_ids)
    if total == 0:
        return

    ok = 0
    failed = 0
    total_evidence = 0
    for i, vid in enumerate(vehicle_ids, 1):
        print(f"[{i}/{total}] Enriching {vid}...")
        try:
            result = await _enrich_one(vid)
            ev_n = result.get("evidence_created", 0)
            errs = result.get("errors") or []
            total_evidence += ev_n
            if errs:
                print(f"  WARN evidence={ev_n} errors={len(errs)}: {errs[:2]}")
            else:
                print(f"  OK evidence={ev_n}")
            ok += 1
        except Exception as exc:
            print(f"  FAIL: {type(exc).__name__}: {exc}")
            failed += 1
        # Stay under LLM RPS
        if i < total:
            time.sleep(2)

    print(
        f"\nDone. ok={ok} failed={failed} total_evidence_created={total_evidence}"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--limit", type=int, default=None,
        help="Process at most N vehicles (default: all).",
    )
    p.add_argument(
        "--vehicle-id", default=None,
        help="Enrich a single vehicle by id (overrides --limit / discovery).",
    )
    p.add_argument(
        "--reenrich", action="store_true",
        help="Skip the no-evidence filter so already-enriched vehicles are re-processed."
        " enrich_vehicle_features upserts, so this is idempotent.",
    )
    p.add_argument(
        "--since", default=None,
        help="ISO date (YYYY-MM-DD); restrict to vehicles created on/after this date.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.vehicle_id:
        ids = [args.vehicle_id]
    else:
        ids = _stuck_vehicle_ids(
            args.limit, reenrich=args.reenrich, since=args.since
        )
    asyncio.run(_main(ids))
