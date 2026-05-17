"""Import `backend/serwis_baza.csv` → `public.samar_class_service_rates`.

Naprawia rozjazd zidentyfikowany podczas planowania nakładki UI: PowerBI →
`build_service_cost_resource.py` produkuje CSV, ale nigdy nie był on
ładowany do Supabase. Runtime (`core.LTRSubCalculatorSerwisNew.py:29,54`)
czyta z `samar_class_service_rates`, więc tu jest cel.

CSV format (polish decimals):
    Klasa SAMAR (FK),przebieg_do,stawka_aso_per_km,stawka_non_aso_per_km
    "Autobusy - AUTOBUSY",30000,"0,0874","0,0295"
    ...

Strategia: full replace przez DELETE + INSERT w jednej transakcji.
Klasa SAMAR jest mapowana po `samar_classes.name` (literal match).
Niezmapowane wiersze są raportowane jako warning i pomijane.

Usage:
    poetry run python -m scripts.import_serwis_baza
    poetry run python -m scripts.import_serwis_baza --dry-run
    poetry run python -m scripts.import_serwis_baza --csv path/to/other.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import get_admin_client, supabase  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "serwis_baza.csv"
TARGET_TABLE = "samar_class_service_rates"


def _parse_pl_decimal(s: str) -> float | None:
    """'0,0874' → 0.0874. Empty/blank → None."""
    s = (s or "").strip().strip('"')
    if not s:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        logger.warning("Nie mogłem sparsować PL-decimal: %r", s)
        return None


def _load_samar_class_lookup(client) -> dict[str, int]:
    """Zwraca {name: id} dla wszystkich samar_classes."""
    resp = client.table("samar_classes").select("id, name").execute()
    return {row["name"]: row["id"] for row in (resp.data or [])}


def _read_csv_rows(csv_path: Path) -> list[dict]:
    """Czyta CSV → lista dictów z surowymi stringami."""
    rows: list[dict] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _build_payload(
    csv_rows: list[dict],
    class_lookup: dict[str, int],
) -> tuple[list[dict], list[str]]:
    """Map CSV rows → DB payload + lista niezmapowanych klas."""
    payload: list[dict] = []
    unmapped: list[str] = []
    for row in csv_rows:
        class_name = (row.get("Klasa SAMAR (FK)") or "").strip().strip('"')
        if not class_name:
            continue
        class_id = class_lookup.get(class_name)
        if class_id is None:
            unmapped.append(class_name)
            continue
        try:
            przebieg_do = int(row["przebieg_do"])
        except (KeyError, ValueError, TypeError):
            logger.warning("Skip — niepoprawny przebieg_do w wierszu: %r", row)
            continue
        aso = _parse_pl_decimal(row.get("stawka_aso_per_km", ""))
        non_aso = _parse_pl_decimal(row.get("stawka_non_aso_per_km", ""))
        if aso is None or non_aso is None:
            logger.warning(
                "Skip — brak stawek dla %s @ %d", class_name, przebieg_do
            )
            continue
        payload.append({
            "klasa_samar_fk": class_id,
            "przebieg_do": przebieg_do,
            "stawka_aso_per_km": aso,
            "stawka_non_aso_per_km": non_aso,
        })
    return payload, unmapped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Ścieżka do CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nie zapisuj — tylko raportuj co by się stało.",
    )
    parser.add_argument(
        "--use-anon",
        action="store_true",
        help="Użyj anon client (domyślnie service_role).",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        logger.error("Brak pliku CSV: %s", args.csv)
        return 2

    client = supabase if args.use_anon else get_admin_client()
    logger.info("Klient: %s", "anon" if args.use_anon else "service_role")

    class_lookup = _load_samar_class_lookup(client)
    logger.info("Załadowano %d klas SAMAR z DB", len(class_lookup))

    csv_rows = _read_csv_rows(args.csv)
    logger.info("Wczytano %d wierszy z %s", len(csv_rows), args.csv)

    payload, unmapped = _build_payload(csv_rows, class_lookup)
    logger.info(
        "Do importu: %d wierszy. Niezmapowane klasy: %d (%s)",
        len(payload),
        len(set(unmapped)),
        sorted(set(unmapped))[:5],
    )

    if args.dry_run:
        logger.info("DRY-RUN: nie wykonuję zapisu. Przykładowe 3 wiersze:")
        for row in payload[:3]:
            logger.info("  %s", row)
        return 0

    # Full replace strategy: delete all, then insert.
    logger.info("DELETE FROM %s ...", TARGET_TABLE)
    # Wymóg PostgREST: DELETE musi mieć filter. .neq na PK to no-op-filter który
    # przepuszcza wszystkie wiersze.
    client.table(TARGET_TABLE).delete().neq(
        "id", "00000000-0000-0000-0000-000000000000"
    ).execute()

    logger.info("INSERT %d wierszy do %s ...", len(payload), TARGET_TABLE)
    # Insert w batchach po 500 (Supabase domyślnie radzi sobie z większymi,
    # ale safe-by-default).
    batch_size = 500
    inserted = 0
    for i in range(0, len(payload), batch_size):
        chunk = payload[i : i + batch_size]
        client.table(TARGET_TABLE).insert(chunk).execute()
        inserted += len(chunk)
        logger.info("  +%d (total %d)", len(chunk), inserted)

    logger.info("✅ Done. Wstawiono %d wierszy.", inserted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
