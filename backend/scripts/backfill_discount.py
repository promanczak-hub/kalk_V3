"""Backfill: deterministyczne wypełnienie `card_summary.discount` dla istniejących wpisów.

Wzorowane na backfill_model_trim.py.

Usage:
    python scripts/backfill_discount.py                 # dry-run (default)
    python scripts/backfill_discount.py --apply         # zastosuj zmiany w DB
    python scripts/backfill_discount.py --apply --overwrite  # nadpisz nawet explicit_amount
    python scripts/backfill_discount.py --limit 50      # tylko pierwsze 50 wierszy
    python scripts/backfill_discount.py --vehicle-id X  # pojedynczy pojazd

Działa BEZ wywołań LLM — tylko regex + heurystyki słownikowe.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import supabase
from core.discount_backfill import apply_backfill_to_card_summary


def _fetch_rows(vehicle_id: str | None, limit: int) -> list[dict[str, Any]]:
    query = supabase.table("vehicle_synthesis").select("id,brand,model,synthesis_data")
    if vehicle_id:
        query = query.eq("id", vehicle_id)
    if limit > 0:
        query = query.limit(limit)
    resp = query.execute()
    return resp.data or []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Zastosuj zmiany w DB (domyślnie dry-run)")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Nadpisz nawet wpisy gdzie LLM już wypełnił explicit_amount/percentage",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit wierszy (0 = wszystkie)")
    parser.add_argument("--vehicle-id", type=str, default=None, help="Pojedynczy pojazd")
    args = parser.parse_args()

    rows = _fetch_rows(args.vehicle_id, args.limit)
    print(f"Pobrano {len(rows)} wierszy z vehicle_synthesis.")

    updated = skipped = errors = 0
    for row in rows:
        try:
            synthesis = row.get("synthesis_data") or {}
            card_summary = synthesis.get("card_summary")
            if not isinstance(card_summary, dict):
                skipped += 1
                continue

            digital_twin = synthesis.get("digital_twin")
            changed = apply_backfill_to_card_summary(
                card_summary, digital_twin, overwrite_existing=args.overwrite
            )

            if not changed:
                skipped += 1
                continue

            disc = card_summary.get("discount") or {}
            label = f"{row.get('brand')} {row.get('model')} ({row['id']})"
            print(
                f"  ✓ {label}: method={disc.get('extraction_method')}, "
                f"pct={disc.get('computed_pct')}, "
                f"pln={disc.get('explicit_rabat_pln')}, "
                f"non_disc={disc.get('non_discountable_total_net')}, "
                f"conf={disc.get('confidence')}"
            )

            if args.apply:
                synthesis["card_summary"] = card_summary
                supabase.table("vehicle_synthesis").update(
                    {"synthesis_data": synthesis}
                ).eq("id", row["id"]).execute()

            updated += 1
        except Exception as e:
            print(f"  ✗ ERROR {row.get('id')}: {e}")
            errors += 1

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] updated={updated} skipped={skipped} errors={errors} (total={len(rows)})")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
