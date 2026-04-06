"""One-shot script: Find kalkulacje without matrix cache and recalculate them.

Usage (from d:/kalk_v3/backend):
    poetry run python /tmp/recalc_missing.py
"""

import sys
import logging

# Ensure the backend root is on sys.path
sys.path.insert(0, r"d:\kalk_v3\backend")

# Suppress excessive debug output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recalc_missing")


def main() -> None:
    from core.database import supabase

    # 1. Get ALL kalkulacje
    logger.info("Pobieranie wszystkich kalkulacji z ltr_kalkulacje...")
    kalk_res = supabase.table("ltr_kalkulacje").select("id, dane_pojazdu, numer_kalkulacji, cena_netto, stan_json").order("created_at", desc=True).execute()
    all_kalks = kalk_res.data or []
    logger.info("Znaleziono %d kalkulacji w sumie.", len(all_kalks))

    if not all_kalks:
        logger.info("Brak kalkulacji w bazie. Koniec.")
        return

    # 2. Get ALL kalkulacja_ids that DO have matrix cache entries
    kalk_ids = [k["id"] for k in all_kalks]
    cache_res = supabase.table("vehicle_matrix_cache").select("kalkulacja_id").in_("kalkulacja_id", kalk_ids).execute()
    cached_kalk_ids = set()
    for row in (cache_res.data or []):
        cached_kalk_ids.add(row["kalkulacja_id"])

    # 3. Find kalkulacje WITHOUT cache
    missing = [k for k in all_kalks if k["id"] not in cached_kalk_ids]
    logger.info(
        "Kalkulacje BEZ macierzy (matrix cache): %d / %d",
        len(missing),
        len(all_kalks),
    )

    if not missing:
        logger.info("✅ Wszystkie kalkulacje mają przeliczone macierze. Koniec.")
        return

    # Print summary
    for i, k in enumerate(missing, 1):
        sj = k.get("stan_json") or {}
        vehicle_id = sj.get("vehicle_id", "brak")
        source = sj.get("source", "?")
        logger.info(
            "  [%d] %s | %s | cena=%.0f | vehicle=%s | source=%s",
            i,
            k["numer_kalkulacji"],
            k.get("dane_pojazdu", "?"),
            k.get("cena_netto") or 0,
            vehicle_id,
            source,
        )

    # 4. Recalculate each synchronously
    from core.matrix_cache_job import process_single_kalkulacja_matrix_task

    success = 0
    failed = 0
    for i, k in enumerate(missing, 1):
        kalk_id = k["id"]
        logger.info(
            "=== Przeliczanie [%d/%d]: %s (%s) ===",
            i,
            len(missing),
            k["numer_kalkulacji"],
            k.get("dane_pojazdu", "?"),
        )
        try:
            process_single_kalkulacja_matrix_task(
                kalkulacja_id=kalk_id,
                celery_task_id=None,
                trace_id=f"RECALC_MISSING_{i}",
            )
            success += 1
            logger.info("  ✅ OK")
        except Exception as e:
            failed += 1
            logger.error("  ❌ Błąd: %s", e)

    logger.info("=" * 60)
    logger.info(
        "PODSUMOWANIE: %d przeliczonych, %d błędów, %d pominiętych (już OK)",
        success,
        failed,
        len(all_kalks) - len(missing),
    )


if __name__ == "__main__":
    main()
