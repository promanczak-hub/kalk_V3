"""Ponowne przetworzenie istniejących JSONów przez pipeline Flash.

Pobiera rekordy z vehicle_synthesis i re-runuje:
1. AI Mapper (Flash) → brand, model, fuel, transmission, vehicle_type
2. Engine Mapper (Flash) → fuel (uściślone), engine_class, engine_candidates
3. SAMAR Mapper (Flash) → samar_category, samar_candidates (uses seats + full context)

Użycie:
    python reprocess_flash.py                     # wszystkie completed
    python reprocess_flash.py --dry-run            # bez zapisu
    python reprocess_flash.py --limit 5            # max 5 rekordów
    python reprocess_flash.py --vehicle-id UUID    # konkretny pojazd
"""

import argparse
import json
import sys
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

# Dodaj backend do ścieżki (na wypadek uruchomienia z katalogu backend)
sys.path.insert(0, ".")

from core.database import supabase as supabase_client
from core.engine_mapper import map_to_engine_class
from core.samar_mapper import map_to_samar_class
from services.ai_mapper_service import map_vehicle_data_flash


def _fetch_vehicles(
    vehicle_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Pobierz rekordy z vehicle_synthesis do ponownego przetworzenia."""
    query = supabase_client.table("vehicle_synthesis").select(
        "id, brand, model, synthesis_data, verification_status"
    )

    if vehicle_id:
        query = query.eq("id", vehicle_id)
    else:
        query = query.eq("verification_status", "completed")

    query = query.order("created_at", desc=True)

    if limit:
        query = query.limit(limit)

    response = query.execute()
    return response.data or []


def _reprocess_single(
    row: dict[str, Any],
    dry_run: bool = False,
) -> bool:
    """Przetworz jeden rekord przez Flash. Zwraca True jeśli sukces."""
    vehicle_id: str = row["id"]
    synthesis: dict[str, Any] = row.get("synthesis_data") or {}

    if not synthesis:
        print(f"  ⚠ [{vehicle_id}] Brak synthesis_data — pomijam")
        return False

    brand = row.get("brand") or synthesis.get("brand")
    model = row.get("model") or synthesis.get("model")
    label = f"{brand} {model}".strip() or vehicle_id[:8]

    print(f"\n{'=' * 60}")
    print(f"  🔄 [{label}] id={vehicle_id}")

    # ── Step 1: AI Mapper (Flash) ──
    print("     → Step 1/3: AI Mapper (Flash)...")
    try:
        mapped_data = map_vehicle_data_flash(synthesis)
    except Exception as exc:
        print(f"     ✗ AI Mapper error: {exc}")
        return False

    new_brand = mapped_data.get("brand") or brand
    new_model = mapped_data.get("model") or model
    print(
        f"     ✓ brand={new_brand}, model={new_model}, fuel={mapped_data.get('fuel')}"
    )

    # Shared context from card_summary
    card_summary = synthesis.get("card_summary", {})
    trim = mapped_data.get("trim_level")

    # ── Step 2: Engine Mapper (Flash) — first, doesn't depend on SAMAR ──
    print("     → Step 2/3: Engine Mapper...")
    powertrain = (
        card_summary.get("powertrain", {})
        if isinstance(card_summary.get("powertrain"), dict)
        else {}
    )
    engine_designation = powertrain.get("engine_designation")
    capacity = powertrain.get("engine_capacity")
    power = card_summary.get("power_hp")

    try:
        eng_name, eng_cat, eng_candidates = map_to_engine_class(
            fuel=mapped_data.get("fuel"),
            engine_designation=engine_designation,
            power=str(power) if power else None,
            capacity=str(capacity) if capacity else None,
            model=new_model,
            trim=trim,
        )
        if eng_name != "UNKNOWN":
            mapped_data["fuel"] = eng_name
            mapped_data["engine_class"] = eng_cat
            mapped_data["engine_candidates"] = eng_candidates
            print(f"     ✓ Engine={eng_name} ({eng_cat})")
        else:
            # Fallback — szukaj w DB
            try:
                engines_resp = (
                    supabase_client.table("engines")
                    .select("category")
                    .eq("name", mapped_data.get("fuel"))
                    .execute()
                )
                if engines_resp.data:
                    mapped_data["engine_class"] = engines_resp.data[0]["category"]
                    print(f"     ✓ Engine (DB fallback)={mapped_data.get('fuel')}")
            except Exception as db_exc:
                print(f"     ⚠ Engine DB fallback error: {db_exc}")
    except Exception as exc:
        print(f"     ✗ Engine Mapper error: {exc}")

    # ── Step 3: SAMAR Mapper (Flash) — last, uses full context incl. seats ──
    print("     → Step 3/3: SAMAR Mapper...")
    segment = card_summary.get("segment") or card_summary.get("car_segment")
    body_style = card_summary.get("body_style")
    transmission = mapped_data.get("transmission")
    seats_raw = card_summary.get("number_of_seats")

    try:
        samar_code, samar_name, samar_candidates = map_to_samar_class(
            brand=new_brand,
            model=new_model,
            segment=segment,
            body_style=body_style,
            trim=trim,
            transmission=transmission,
            number_of_seats=int(seats_raw) if seats_raw else None,
        )
        mapped_data["samar_category"] = samar_name
        mapped_data["samar_candidates"] = samar_candidates
        print(f"     ✓ SAMAR={samar_name} ({samar_code})")
    except Exception as exc:
        print(f"     ✗ SAMAR Mapper error: {exc}")

    # ── Merge & Save ──
    synthesis["mapped_ai_data"] = mapped_data

    if dry_run:
        print("     🏁 DRY-RUN — nie zapisuję do DB")
        print(
            f"     Mapped data preview: "
            f"{json.dumps(mapped_data, ensure_ascii=False, indent=2)[:500]}"
        )
        return True

    try:
        update_payload: dict[str, Any] = {
            "brand": new_brand,
            "model": new_model,
            "synthesis_data": synthesis,
        }
        supabase_client.table("vehicle_synthesis").update(update_payload).eq(
            "id", vehicle_id
        ).execute()
        print(f"     ✅ Zapisano do DB")
        return True
    except Exception as exc:
        print(f"     ✗ DB save error: {exc}")
        return False


def main() -> None:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Ponowne przetworzenie istniejących JSONów przez pipeline Gemini Flash."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nie zapisuj zmian do bazy danych.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maksymalna liczba rekordów do przetworzenia.",
    )
    parser.add_argument(
        "--vehicle-id",
        type=str,
        default=None,
        help="ID konkretnego pojazdu do przetworzenia.",
    )
    args = parser.parse_args()

    print("🚀 Flash Re-Processing Pipeline")
    print(f"   dry-run={args.dry_run}, limit={args.limit}")
    if args.vehicle_id:
        print(f"   vehicle-id={args.vehicle_id}")
    print()

    rows = _fetch_vehicles(
        vehicle_id=args.vehicle_id,
        limit=args.limit,
    )

    if not rows:
        print("⚠ Nie znaleziono rekordów do przetworzenia.")
        return

    print(f"📋 Znaleziono {len(rows)} rekord(ów) do przetworzenia.\n")

    success_count = 0
    error_count = 0
    start_time = time.time()

    for idx, row in enumerate(rows, start=1):
        print(f"[{idx}/{len(rows)}]", end="")
        ok = _reprocess_single(row, dry_run=args.dry_run)
        if ok:
            success_count += 1
        else:
            error_count += 1

        # Krótka pauza między wywołaniami API (rate limiting)
        if idx < len(rows):
            time.sleep(1)

    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print(f"🏁 Zakończono w {elapsed:.1f}s")
    print(f"   ✅ Sukces: {success_count}")
    print(f"   ✗ Błędy:  {error_count}")
    if args.dry_run:
        print("   ℹ  DRY-RUN — żadne zmiany nie zostały zapisane.")


if __name__ == "__main__":
    main()
