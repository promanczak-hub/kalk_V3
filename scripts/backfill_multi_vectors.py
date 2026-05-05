"""Backfill multi-vector embeddings for completed vehicles.

For each vehicle with `verification_status = 'completed'` we build three
distinct text representations (use_case / specs / equipment), embed each
separately with Gemini, and write the resulting 768-dim vectors into
vehicle_synthesis. Also refreshes `semantic_embedding`.

Run inside the backend container so `core.*` imports resolve:

    docker cp scripts/backfill_multi_vectors.py kalk_v3-backend-1:/app/_backfill.py
    docker exec kalk_v3-backend-1 sh -c 'cd /app && python -u _backfill.py'
"""

from __future__ import annotations

import logging
import sys
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()

from core.database import supabase  # noqa: E402
from core.embeddings import (  # noqa: E402
    build_equipment_text,
    build_specs_text,
    build_use_case_text,
    build_vehicle_document,
    generate_embedding,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("backfill_multi_vectors")


def fetch_targets() -> list[dict]:
    resp = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, synthesis_data")
        .eq("verification_status", "completed")
        .execute()
    )
    return resp.data or []


def _vec_lit(vec: list[float]) -> str:
    return "[" + ",".join(str(v) for v in vec) + "]"


def update_vectors(vid: str, payload: dict[str, str]) -> None:
    payload["multi_vectors_at"] = "now()"
    supabase.table("vehicle_synthesis").update(payload).eq("id", vid).execute()


def main(only_ids: Iterable[str] | None = None) -> int:
    rows = fetch_targets()
    if only_ids:
        only = set(only_ids)
        rows = [r for r in rows if r["id"] in only]
    log.info("Backfilling embeddings for %d vehicles", len(rows))

    ok = 0
    failed: list[tuple[str, str]] = []

    for i, row in enumerate(rows, start=1):
        vid = row["id"]
        brand = row.get("brand") or ""
        model = row.get("model") or ""
        sd = row.get("synthesis_data") or {}

        texts = {
            "semantic_embedding": build_vehicle_document(brand, model, sd),
            "vector_use_case": build_use_case_text(brand, model, sd),
            "vector_specs": build_specs_text(brand, model, sd),
            "vector_equipment": build_equipment_text(brand, model, sd),
        }

        payload: dict[str, str] = {}
        col_failures: list[str] = []
        for col, text in texts.items():
            if not text or not text.strip():
                col_failures.append(f"{col}:empty_text")
                continue
            try:
                vec = generate_embedding(text)
            except Exception as exc:
                log.exception("[%d/%d] %s %s: embed error", i, len(rows), vid, col)
                col_failures.append(f"{col}:exception:{exc}")
                continue
            if not vec:
                col_failures.append(f"{col}:none")
                continue
            payload[col] = _vec_lit(vec)

        if not payload:
            log.warning("[%d/%d] %s: skipping — all 4 embeddings failed: %s",
                        i, len(rows), vid, col_failures)
            failed.append((vid, ";".join(col_failures)))
            continue

        try:
            update_vectors(vid, payload)
            ok += 1
            log.info("[%d/%d] %s %s — saved %s%s",
                     i, len(rows), brand, model, sorted(payload.keys()),
                     f" (partial: {col_failures})" if col_failures else "")
        except Exception as exc:
            log.exception("[%d/%d] %s: update error", i, len(rows), vid)
            failed.append((vid, f"update_error:{exc}"))

    log.info("Done: ok=%d failed=%d", ok, len(failed))
    if failed:
        for vid, reason in failed[:20]:
            log.warning("FAIL %s: %s", vid, reason)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
