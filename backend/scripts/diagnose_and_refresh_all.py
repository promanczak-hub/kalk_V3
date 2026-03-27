"""
Diagnose and refresh LTR matrix cache for ALL vehicles.

Produces a human-readable report of:
  - vehicles that succeeded
  - vehicles that FAILED (with date, brand, model, error)
"""

import sys
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import supabase
from core.models import ControlCenterSettings
from core.matrix_cache_job import (
    build_calculator_input,
    process_single_kalkulacja_matrix_task,
)
from typing import cast, Any
import uuid


def run_refresh_and_report() -> None:
    # 1. Fetch all vehicles
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, verification_status, created_at, synthesis_data")
        .execute()
    )
    vehicles = res.data or []
    print(f"\n{'=' * 70}")
    print(f"  DIAGNOZA KALKULACJI LTR - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 70}")
    print(f"Łączna liczba aut w bazie: {len(vehicles)}\n")

    # 2. Fetch CC settings once
    settings_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    if not settings_res.data:
        print("BŁĄD KRYTYCZNY: Brak ustawień Control Center!")
        return
    settings = ControlCenterSettings(**cast(dict[str, Any], settings_res.data[0]))

    successes: list[dict] = []
    failures: list[dict] = []
    skipped_no_price: list[dict] = []

    for i, row in enumerate(vehicles):
        vid = row["id"]
        brand = row.get("brand") or "?"
        model = row.get("model") or "?"
        created_at = row.get("created_at", "?")
        label = f"{brand} {model}"

        sys.stdout.flush()

        # Try to build input
        try:
            calc_input = build_calculator_input(
                row, margin_pct=float(settings.default_ltr_margin), settings=settings
            )
        except Exception as e:
            failures.append(
                {
                    "vehicle_id": vid,
                    "label": label,
                    "created_at": created_at,
                    "error": f"build_input: {e}",
                    "stage": "CalculatorInput",
                }
            )
            continue

        if not calc_input:
            skipped_no_price.append(
                {
                    "vehicle_id": vid,
                    "label": label,
                    "created_at": created_at,
                }
            )
            continue

        # Upsert auto kalkulacja
        stan_json = calc_input.model_dump()
        stan_json["source"] = "auto_extract"
        stan_json["brand"] = brand
        stan_json["model"] = model

        now = datetime.now()
        numer = f"AUTO/{now.year}/{now.month:02d}/{uuid.uuid4().hex[:6].upper()}"
        kalk_data = {
            "numer_kalkulacji": numer,
            "status": "szkic_vertex",
            "stan_json": stan_json,
            "dane_pojazdu": label,
            "cena_netto": float(calc_input.base_price_net),
        }

        try:
            exist_res = (
                supabase.table("ltr_kalkulacje")
                .select("id")
                .eq("stan_json->>vehicle_id", vid)
                .eq("stan_json->>source", "auto_extract")
                .execute()
            )
            if exist_res.data:
                kalk_id = exist_res.data[0]["id"]
                supabase.table("ltr_kalkulacje").update(kalk_data).eq(
                    "id", kalk_id
                ).execute()
            else:
                ins = supabase.table("ltr_kalkulacje").insert(kalk_data).execute()
                if not ins.data:
                    raise ValueError("Insert zwrócił brak danych")
                kalk_id = ins.data[0]["id"]
        except Exception as e:
            failures.append(
                {
                    "vehicle_id": vid,
                    "label": label,
                    "created_at": created_at,
                    "error": f"upsert_kalk: {e}",
                    "stage": "DB Insert",
                }
            )
            continue

        # Run matrix calculation
        try:
            # Capture errors from process_single_kalkulacja_matrix_task
            import logging as _logging

            captured_error = []

            class _ErrorCapture(_logging.Handler):
                def emit(self, record):
                    if record.levelno >= _logging.ERROR:
                        captured_error.append(record.getMessage())

            handler = _ErrorCapture()
            job_logger = _logging.getLogger("core.matrix_cache_job")
            job_logger.addHandler(handler)

            process_single_kalkulacja_matrix_task(kalk_id)

            job_logger.removeHandler(handler)

            if captured_error:
                failures.append(
                    {
                        "vehicle_id": vid,
                        "label": label,
                        "created_at": created_at,
                        "error": captured_error[-1],
                        "stage": "MatrixBuild",
                        "kalk_id": kalk_id,
                    }
                )
            else:
                successes.append(
                    {"vehicle_id": vid, "label": label, "created_at": created_at}
                )

        except Exception as e:
            failures.append(
                {
                    "vehicle_id": vid,
                    "label": label,
                    "created_at": created_at,
                    "error": str(e),
                    "stage": "MatrixBuild",
                    "kalk_id": kalk_id,
                }
            )

        # Progress counter every 10
        if (i + 1) % 10 == 0:
            print(f"  [{i + 1}/{len(vehicles)}] Przetworzono...", flush=True)

    # ── REPORT ───────────────────────────────────────────────────────────────

    print(f"\n{'=' * 70}")
    print("  WYNIKI")
    print(f"{'=' * 70}")
    print(f"OK  Sukces:          {len(successes)} aut")
    print(f"!   Brak ceny:       {len(skipped_no_price)} aut")
    print(f"ERR Blad kalkulacji: {len(failures)} aut")

    if skipped_no_price:
        print(f"\n{'─' * 70}")
        print("[BRAK CENY] AUTA BEZ CENY (pomin lub sprawdz ekstrakcje):")
        print(f"{'─' * 70}")
        for v in skipped_no_price:
            dt = v["created_at"][:10] if len(v["created_at"]) >= 10 else v["created_at"]
            print(f"  [{dt}]  {v['label']:<40}  id={v['vehicle_id']}")

    if failures:
        print(f"\n{'─' * 70}")
        print("[BLAD] AUTA Z BLEDEM (zla ekstrakcja lub brak danych w konfiguracji):")
        print(f"{'─' * 70}")
        for v in failures:
            dt = v["created_at"][:10] if len(v["created_at"]) >= 10 else v["created_at"]
            stage = v.get("stage", "?")
            err = v.get("error", "?")
            print(f"  [{dt}]  {v['label']:<35}  etap={stage}")
            print(f"           BLAD: {err}")
            print(f"           ID: {v['vehicle_id']}")
            print()

    print(f"{'=' * 70}")
    print("Raport zakończony.")


if __name__ == "__main__":
    run_refresh_and_report()
