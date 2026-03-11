"""Migracja danych z excel_drafts (JSONB) → tabele produkcyjne FK.

Parsuje monolityczne klucze (np. "Podstawowa - B MAŁE Diesel (ON)")
na samar_class_id + fuel_type_id i wstawia dane do:
  - samar_class_depreciation_rates  (year 0-7, base + options %)
  - samar_class_mileage_corrections (under/over threshold %)

Operacja INSERT-only — nie modyfikuje excel_drafts.
Domyślnie dry-run. Użyj --execute aby wstawić.
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Fuel type mapping (monolith suffix → integer ID) ──────────
FUEL_TYPE_MAP: dict[str, int] = {
    "Elektryczny (BEV)": 1,
    "Wodór (FCEV)": 2,
    "Hybryda (HEV)": 3,
    "Benzyna mHEV (PB-mHEV)": 4,
    "Diesel mHEV (ON-mHEV)": 5,
    "Plug-in Hybrid (PHEV)": 6,
    "Benzyna (PB)": 7,
    "Diesel (ON)": 8,
    "LPG": 9,
}

# Sorted by length desc → longest match first (greedy)
_FUEL_SUFFIXES = sorted(FUEL_TYPE_MAP.keys(), key=len, reverse=True)


def _parse_monolith(
    monolith: str,
    class_name_to_id: dict[str, int],
) -> tuple[int, int] | None:
    """Parse 'Klasa SAMAR FuelType' → (samar_class_id, fuel_type_id).

    Returns None if parsing fails (logs warning).
    """
    text = monolith.strip()

    fuel_type_id: int | None = None
    class_part: str = ""

    for suffix in _FUEL_SUFFIXES:
        if text.endswith(suffix):
            fuel_type_id = FUEL_TYPE_MAP[suffix]
            class_part = text[: -len(suffix)].strip()
            break

    if fuel_type_id is None:
        logger.warning("Nie rozpoznano silnika w: %r", monolith)
        return None

    samar_class_id = class_name_to_id.get(class_part)
    if samar_class_id is None:
        logger.warning(
            "Nie znaleziono klasy SAMAR dla: %r (z monolitu %r)",
            class_part,
            monolith,
        )
        return None

    return samar_class_id, fuel_type_id


def _load_samar_classes(supabase: Any) -> dict[str, int]:
    """Pobiera {name → id} z samar_classes."""
    res = supabase.table("samar_classes").select("id, name").execute()
    mapping: dict[str, int] = {}
    for row in res.data or []:
        mapping[row["name"]] = int(row["id"])
    logger.info("Załadowano %d klas SAMAR", len(mapping))
    return mapping


def _load_sheet(supabase: Any, sheet_name: str) -> list[dict[str, Any]]:
    """Pobiera data_rows z excel_drafts dla danego arkusza."""
    res = (
        supabase.table("excel_drafts")
        .select("data_rows")
        .eq("sheet_name", sheet_name)
        .limit(1)
        .execute()
    )
    if not res.data:
        logger.error("Nie znaleziono arkusza: %s", sheet_name)
        return []
    rows = res.data[0].get("data_rows", [])
    logger.info("Arkusz %s: %d wierszy", sheet_name, len(rows))
    return rows


def _safe_float(val: Any) -> float:
    """Bezpieczna konwersja na float, domyślnie 0.0."""
    if val is None or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def migrate(*, dry_run: bool = True) -> None:
    """Główna logika migracji."""
    from core.database import supabase

    class_map = _load_samar_classes(supabase)

    # ── Load all 4 sheets ──
    wr_klasa_rows = _load_sheet(supabase, "TAB.WR KLASA")
    okres_rows = _load_sheet(supabase, "TAB. OKRES FINAL")
    dopos_rows = _load_sheet(supabase, "TAB. DOPOSAŻENIA")
    przebieg_rows = _load_sheet(supabase, "TAB. PRZEBIEG")

    # Index TAB. OKRES FINAL & DOPOSAŻENIA by monolith key for fast lookup
    okres_by_key: dict[str, dict[str, Any]] = {
        r["col_1"]: r for r in okres_rows
    }
    dopos_by_key: dict[str, dict[str, Any]] = {
        r["col_1"]: r for r in dopos_rows
    }
    przebieg_by_key: dict[str, dict[str, Any]] = {
        r["col_1"]: r for r in przebieg_rows
    }

    depreciation_inserts: list[dict[str, Any]] = []
    mileage_inserts: list[dict[str, Any]] = []

    parsed_count = 0
    skip_count = 0

    # ── Build depreciation rows (year 0-7) for each monolith ──
    for wr_row in wr_klasa_rows:
        monolith = wr_row.get("col_1", "")
        parsed = _parse_monolith(monolith, class_map)
        if parsed is None:
            skip_count += 1
            continue

        samar_class_id, fuel_type_id = parsed
        parsed_count += 1

        base_wr = _safe_float(wr_row.get("col_2"))
        okres_row = okres_by_key.get(monolith, {})
        dopos_row = dopos_by_key.get(monolith, {})

        # Year 0: base_depreciation = WR KLASA, options = DOPOSAŻENIA col_2
        depreciation_inserts.append(
            {
                "samar_class_id": samar_class_id,
                "fuel_type_id": fuel_type_id,
                "year": 0,
                "base_depreciation_percent": base_wr,
                "options_depreciation_percent": _safe_float(
                    dopos_row.get("col_2")
                ),
            }
        )

        # Years 1-7: depreciation from OKRES FINAL, options from DOPOSAŻENIA
        for yr in range(1, 8):
            col_key = f"col_{yr + 1}"  # col_2=yr0, col_3=yr1, ...
            # OKRES FINAL: col_2=35k, col_3=35k, col_4=70k... but it's
            # indexed the same way — col_2 is year 0(?), col_3 is year 1 etc.
            # Actually from data: headers are 35, 35, 70, 105, 140, 175, 210, 245
            # So col_2 = half-year 1, col_3 = half-year 2 ...
            # But structurally it's col_2..col_9 mapping to year 0..7
            okres_col = f"col_{yr + 1}"
            dopos_col = f"col_{yr + 1}"

            depreciation_inserts.append(
                {
                    "samar_class_id": samar_class_id,
                    "fuel_type_id": fuel_type_id,
                    "year": yr,
                    "base_depreciation_percent": _safe_float(
                        okres_row.get(okres_col)
                    ),
                    "options_depreciation_percent": _safe_float(
                        dopos_row.get(dopos_col)
                    ),
                }
            )

        # ── Mileage corrections ──
        przebieg_row = przebieg_by_key.get(monolith, {})
        if przebieg_row:
            mileage_inserts.append(
                {
                    "samar_class_id": samar_class_id,
                    "fuel_type_id": fuel_type_id,
                    "under_threshold_percent": _safe_float(
                        przebieg_row.get("col_2")
                    ),
                    "over_threshold_percent": _safe_float(
                        przebieg_row.get("col_3")
                    ),
                }
            )

    logger.info(
        "Parsowanie: %d sparsowano, %d pominięto",
        parsed_count,
        skip_count,
    )
    logger.info(
        "Do wstawienia: %d wierszy deprecjacji, %d wierszy przebiegu",
        len(depreciation_inserts),
        len(mileage_inserts),
    )

    if dry_run:
        logger.info("=== DRY RUN — nic nie wstawiono ===")
        # Show sample
        if depreciation_inserts:
            sample = depreciation_inserts[0]
            logger.info("Przykład deprecjacji: %s", sample)
        if mileage_inserts:
            sample = mileage_inserts[0]
            logger.info("Przykład przebiegu: %s", sample)
        return

    # ── INSERT in batches ──
    logger.info("Wstawianie deprecjacji (%d)...", len(depreciation_inserts))
    batch_size = 100
    for i in range(0, len(depreciation_inserts), batch_size):
        batch = depreciation_inserts[i : i + batch_size]
        supabase.table("samar_class_depreciation_rates").insert(batch).execute()
        logger.info("  batch %d/%d", i // batch_size + 1, -(-len(depreciation_inserts) // batch_size))

    logger.info("Wstawianie przebiegu (%d)...", len(mileage_inserts))
    for i in range(0, len(mileage_inserts), batch_size):
        batch = mileage_inserts[i : i + batch_size]
        supabase.table("samar_class_mileage_corrections").insert(batch).execute()
        logger.info("  batch %d/%d", i // batch_size + 1, -(-len(mileage_inserts) // batch_size))

    logger.info("✅ Migracja zakończona!")

    # ── Verification ──
    depr_count = (
        supabase.table("samar_class_depreciation_rates")
        .select("id", count="exact")
        .execute()
    )
    mileage_count = (
        supabase.table("samar_class_mileage_corrections")
        .select("id", count="exact")
        .execute()
    )
    logger.info(
        "Weryfikacja: deprecjacja=%d, przebieg=%d",
        depr_count.count or 0,
        mileage_count.count or 0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migracja excel_drafts → tabele produkcyjne"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Wykonaj INSERT-y (domyślnie dry-run)",
    )
    args = parser.parse_args()
    migrate(dry_run=not args.execute)
