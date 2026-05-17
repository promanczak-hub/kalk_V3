"""Re-run pipeline_price_validator on an existing vehicle_synthesis row.

Use case: deterministic backfill after extending the validator with new
self-heal logic (e.g. derived base_price for offers like Audi GOA-26-103543
where the LLM couldn't find the base price literally in the PDF).

Default: dry-run. Pass --apply to actually persist changes.

Examples:
    python scripts/revalidate_card_summary.py
    python scripts/revalidate_card_summary.py --offer GOA-26-103543 --apply
"""

import argparse
import copy
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import supabase
from core.pipeline_price_validator import validate_and_flag_prices

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def _print_card_summary_state(label: str, cs: dict) -> None:
    print(f"\n========== {label} ==========")
    print(f"  base_price    = {cs.get('base_price')!r}")
    print(f"  options_price = {cs.get('options_price')!r}")
    print(f"  total_price   = {cs.get('total_price')!r}")
    print(f"  _base_derived = {cs.get('_base_derived')!r}")
    print(f"  _price_domain = {cs.get('_price_domain')!r}")
    val = cs.get("_validation") or {}
    warnings = val.get("warnings", [])
    parsed = val.get("parsed_prices", {})
    print(f"  parsed_prices = {parsed}")
    print(f"  is_valid      = {val.get('is_valid')}")
    print(f"  warnings ({len(warnings)}):")
    for w in warnings:
        print(f"    - [{w.get('severity')}] {w.get('rule')}: {w.get('message')}")


def revalidate(offer_number: str, apply_changes: bool) -> int:
    logger.info("Fetching vehicle_synthesis row for offer_number=%s", offer_number)
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, offer_number, brand, model, verification_status, synthesis_data")
        .eq("offer_number", offer_number)
        .execute()
    )
    rows = res.data or []
    if not rows:
        logger.error("No row found for offer_number=%s", offer_number)
        return 1
    if len(rows) > 1:
        logger.warning(
            "Multiple rows found (%d) for offer_number=%s — using the first",
            len(rows), offer_number,
        )

    row = rows[0]
    vid = row["id"]
    synthesis_data = row.get("synthesis_data") or {}
    card_summary_before = synthesis_data.get("card_summary")

    if not isinstance(card_summary_before, dict):
        logger.error(
            "Row %s has no card_summary dict in synthesis_data — nothing to revalidate",
            vid,
        )
        return 2

    logger.info(
        "Row id=%s brand=%s model=%s verification_status=%s",
        vid,
        row.get("brand"),
        row.get("model"),
        row.get("verification_status"),
    )

    before_snapshot = copy.deepcopy(card_summary_before)
    new_synthesis_data = copy.deepcopy(synthesis_data)

    validate_and_flag_prices(new_synthesis_data)
    new_card_summary = new_synthesis_data.get("card_summary") or {}

    _print_card_summary_state("BEFORE", before_snapshot)
    _print_card_summary_state("AFTER", new_card_summary)

    if new_card_summary == before_snapshot:
        logger.info("Validator did not change card_summary — nothing to apply.")
        return 0

    if not apply_changes:
        print("\n[DRY-RUN] No DB write. Re-run with --apply to persist.")
        return 0

    logger.info("Applying changes to row id=%s (offer=%s)...", vid, offer_number)
    update_res = (
        supabase.table("vehicle_synthesis")
        .update({"synthesis_data": new_synthesis_data})
        .eq("id", vid)
        .execute()
    )
    if not update_res.data:
        logger.error("Update returned no data — possible failure: %s", update_res)
        return 3

    logger.info("Done. Updated row id=%s (verification_status untouched).", vid)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offer",
        default="GOA-26-103543",
        help="offer_number of the row to revalidate (default: GOA-26-103543)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes (otherwise dry-run, default).",
    )
    args = parser.parse_args()
    return revalidate(args.offer, args.apply)


if __name__ == "__main__":
    sys.exit(main())
