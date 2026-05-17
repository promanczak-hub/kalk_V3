"""One-off cleanup: usuwa pole `user_overrides` z synthesis_data we wszystkich
wierszach vehicle_synthesis. Pole było używane przez wycofany lejek
disambiguation — po jego usunięciu nikt już go nie czyta ani nie zapisuje.

Skrypt jest idempotentny: ponowne uruchomienie nic nie zmienia.

Uruchomienie:
    python -m backend.scripts.cleanup_user_overrides
"""

import logging

from supabase.client import create_client

from core.settings import SUPABASE_URL, SUPABASE_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_user_overrides() -> None:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    logger.info("Fetching vehicle_synthesis rows...")
    resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .execute()
    )

    rows = resp.data or []
    logger.info("Found %d rows.", len(rows))

    cleaned = 0
    skipped = 0
    for row in rows:
        vid = row["id"]
        syn = row.get("synthesis_data") or {}

        if not isinstance(syn, dict) or "user_overrides" not in syn:
            skipped += 1
            continue

        syn.pop("user_overrides", None)
        try:
            sb.table("vehicle_synthesis").update(
                {"synthesis_data": syn}
            ).eq("id", vid).execute()
            cleaned += 1
        except Exception as exc:
            logger.error("Update failed for %s: %s", vid, exc)

    logger.info(
        "Cleanup done. cleaned=%d skipped=%d total=%d",
        cleaned,
        skipped,
        len(rows),
    )


if __name__ == "__main__":
    cleanup_user_overrides()
