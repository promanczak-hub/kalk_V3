"""Ponowna ekstrakcja card_summary dla pojazdów z '2x4' w mapped_ai_data.drive_type.

Problem: Flash mapper wyciągał '2X4' z tytułu oferty (np. 'Superb 2x4'), ale:
- feature_enrichment.py nie znał '2x4' → FWD (teraz naprawione)
- frontend DRIVE_TYPE_MAP nie zawierał '2X4' → FWD (teraz naprawione)
- card_summary.drive_type zostawał None (LLM nie wiedział że '2x4' = FWD)

Skrypt:
1. Pobiera pojazdy gdzie mapped_ai_data.drive_type zawiera '2x4'
2. Dodatkowo sprawdza FORCE_INCLUDE_OFFER_NUMBERS
3. Re-uruchamia process_single_twin (Gemini Flash) → card_summary.drive_type = 'FWD'

Użycie:
  python reprocess_2x4_drive_type.py [--dry-run]
"""

from __future__ import annotations

import json
import os
import sys
import time

WORKTREE_BACKEND = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend")
)
MAIN_BACKEND = r"D:\kalk_v3\backend"

sys.path.insert(0, WORKTREE_BACKEND)

from dotenv import load_dotenv

for _env_path in [os.path.join(WORKTREE_BACKEND, ".env"), os.path.join(MAIN_BACKEND, ".env")]:
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        break

from core.database import supabase  # noqa: E402  (after path setup)

DRY_RUN = "--dry-run" in sys.argv

FORCE_INCLUDE_OFFER_NUMBERS: list[str] = [
    "GOC-26-12972",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> None:
    log("=== Batch reprocess: 2x4 drive_type fix ===")
    if DRY_RUN:
        log("DRY RUN — brak zapisu do DB")

    # 1. Pobierz wszystkie pojazdy (65 rekordów) i filtruj w Pythonie
    resp_all = (
        supabase.table("vehicle_synthesis")
        .select("id, offer_number, brand, model, synthesis_data")
        .execute()
    )
    all_records = resp_all.data or []
    log(f"Pobrano {len(all_records)} pojazdów z DB")

    # Filtruj te z '2x4' w mapped_ai_data.drive_type
    by_drive: dict[str, dict] = {}
    for r in all_records:
        sd = r.get("synthesis_data") or {}
        mapped = sd.get("mapped_ai_data") or {}
        raw = str(mapped.get("drive_type") or "").upper()
        if "2X4" in raw:
            by_drive[r["id"]] = r

    log(f"Z '2X4' w mapped_ai_data.drive_type: {len(by_drive)}")

    # 2. Wymuś konkretne offer_numbers
    forced: dict[str, dict] = {}
    for offer_num in FORCE_INCLUDE_OFFER_NUMBERS:
        resp = (
            supabase.table("vehicle_synthesis")
            .select("id, offer_number, brand, model, synthesis_data")
            .eq("offer_number", offer_num)
            .limit(1)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            if row["id"] not in by_drive:
                forced[row["id"]] = row
                log(f"  Wymuszono: {offer_num} (nie był w filtrze)")

    to_fix = {**by_drive, **forced}
    log(f"Łącznie do reprocessingu: {len(to_fix)}")

    if not to_fix:
        log("Brak pojazdów do naprawy. Koniec.")
        return

    # Lazy import — dopiero kiedy mamy co przetwarzać
    if not DRY_RUN:
        from core.extractor_v2 import process_single_twin  # noqa: PLC0415

    for i, (vid, row) in enumerate(to_fix.items(), 1):
        offer = row.get("offer_number", "?")
        brand = row.get("brand", "?")
        model = row.get("model", "?")
        sd = row.get("synthesis_data") or {}
        mapped_drive = (sd.get("mapped_ai_data") or {}).get("drive_type", "?")
        cs_drive = (sd.get("card_summary") or {}).get("drive_type", "None")

        log(f"\n[{i}/{len(to_fix)}] {offer} — {brand} {model}")
        log(f"  mapped_ai_data.drive_type: {mapped_drive}")
        log(f"  card_summary.drive_type:   {cs_drive}")

        if not sd.get("digital_twin"):
            log(f"  SKIP — brak digital_twin")
            continue

        if DRY_RUN:
            log(f"  DRY RUN — pominięto ekstrakcję")
            continue

        try:
            new_json_str = process_single_twin(sd)
            new_data = json.loads(new_json_str)
            new_drive = (new_data.get("card_summary") or {}).get("drive_type", "?")
            log(f"  Nowy card_summary.drive_type: {new_drive}")

            supabase.table("vehicle_synthesis").update(
                {"synthesis_data": new_data}
            ).eq("id", vid).execute()
            log(f"  OK — zapisano")

            if i < len(to_fix):
                time.sleep(2)

        except Exception as exc:
            log(f"  BLAD: {exc}")
            import traceback
            traceback.print_exc()

    log("\n=== Gotowe ===")


if __name__ == "__main__":
    main()
