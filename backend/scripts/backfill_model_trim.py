"""Backfill: normalize vehicle_synthesis.model + trim_level + body_style for existing rows.

Usage:
    poetry run python scripts/backfill_model_trim.py            # dry-run (default)
    poetry run python scripts/backfill_model_trim.py --apply    # actually update DB

The script:
  1. Fetches all rows from vehicle_synthesis.
  2. Runs normalize_model_trim_body() on each.
  3. Prints a diff table (only rows that would change).
  4. With --apply: updates the brand/model plain columns and the
     synthesis_data->card_summary->trim_level + body_style JSON paths.

We DO NOT touch synthesis_data->mapped_ai_data — it's kept as the original
source-of-truth audit trail. Only the public-facing fields are normalized.
"""

from __future__ import annotations

import argparse
import os
import sys
import json
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import supabase
from core.model_normalizer import normalize_model_trim_body
from core.extraction_pipeline.utils import normalize_brand


def _fetch_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_size = 200
    offset = 0
    while True:
        resp = (
            supabase.table("vehicle_synthesis")
            .select("id,brand,model,synthesis_data")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def _diff_row(row: dict[str, Any]) -> tuple[bool, dict[str, Any]] | None:
    raw_brand = row.get("brand")
    raw_model = row.get("model")
    syn = row.get("synthesis_data") or {}
    cs = syn.get("card_summary") or {}
    raw_trim = cs.get("trim_level")
    raw_body = cs.get("body_style")

    new_brand = normalize_brand(raw_brand) if raw_brand else None
    new_model, new_trim, new_body = normalize_model_trim_body(
        raw_model=raw_model,
        brand=new_brand or raw_brand,
        raw_trim=raw_trim,
        raw_body=raw_body,
    )

    changed = (
        (new_brand or "") != (raw_brand or "")
        or (new_model or "") != (raw_model or "")
        or (new_trim or "") != (raw_trim or "")
        or (new_body or "") != (raw_body or "")
    )
    if not changed:
        return None

    return True, {
        "id": row["id"],
        "raw_brand": raw_brand,
        "new_brand": new_brand,
        "raw_model": raw_model,
        "new_model": new_model,
        "raw_trim": raw_trim,
        "new_trim": new_trim,
        "raw_body": raw_body,
        "new_body": new_body,
    }


def _print_diffs(diffs: list[dict[str, Any]]) -> None:
    print(f"\n{'=' * 100}")
    print(f"  FIELD      | {'OLD':<48} | {'NEW':<32}")
    print(f"{'-' * 100}")
    for d in diffs:
        print(f"\n  ROW {d['id']}")
        for field in ("brand", "model", "trim", "body"):
            raw = d[f"raw_{field}"]
            new = d[f"new_{field}"]
            mark = " " if (raw or "") == (new or "") else "*"
            print(f"  {mark} {field:<9} | {str(raw or ''):<48.48} | {str(new or ''):<32.32}")
    print(f"\n{'=' * 100}\n")


def _apply_updates(diffs: list[dict[str, Any]]) -> None:
    for d in diffs:
        # Re-fetch synthesis_data (full payload), patch the JSON paths, write back.
        cur = (
            supabase.table("vehicle_synthesis")
            .select("synthesis_data")
            .eq("id", d["id"])
            .single()
            .execute()
        )
        syn: dict[str, Any] = (cur.data or {}).get("synthesis_data") or {}
        cs = syn.get("card_summary") or {}
        cs["trim_level"] = d["new_trim"]
        cs["body_style"] = d["new_body"]
        syn["card_summary"] = cs

        supabase.table("vehicle_synthesis").update({
            "brand": d["new_brand"],
            "model": d["new_model"],
            "synthesis_data": syn,
        }).eq("id", d["id"]).execute()
        print(f"  ✓ updated {d['id']}: {d['raw_model']!r} → {d['new_model']!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill normalized model/trim/body")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates to DB (default: dry-run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of rows changed (0 = all)",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip y/n confirmation when --apply is set",
    )
    args = parser.parse_args()

    print("Fetching rows from vehicle_synthesis...")
    rows = _fetch_rows()
    print(f"  found {len(rows)} rows")

    diffs: list[dict[str, Any]] = []
    for row in rows:
        result = _diff_row(row)
        if result is None:
            continue
        diffs.append(result[1])
        if args.limit and len(diffs) >= args.limit:
            break

    if not diffs:
        print("\nNo changes needed — all rows are already clean.")
        return 0

    _print_diffs(diffs)
    print(f"  Total rows that would change: {len(diffs)} / {len(rows)}")

    if not args.apply:
        print("\n[DRY-RUN] Re-run with --apply to commit these changes.")
        return 0

    if not args.no_confirm:
        ans = input("\nApply these updates to the DB? [y/N] ").strip().lower()
        if ans != "y":
            print("Aborted.")
            return 1

    print("\nApplying updates...")
    _apply_updates(diffs)
    print(f"\nDone. Updated {len(diffs)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
