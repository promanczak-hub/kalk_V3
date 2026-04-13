import datetime
import logging

from supabase import Client

logger = logging.getLogger(__name__)


def update_progress(supabase: Client, file_id: str, status: str) -> None:
    """Update verification_status in DB — triggers Supabase Realtime."""
    try:
        supabase.table("vehicle_synthesis").update(
            {
                "verification_status": status,
                "processing_updated_at": datetime.datetime.utcnow().isoformat(),
            }
        ).eq("id", file_id).execute()
        logger.info("[PROGRESS] %s -> %s", file_id, status)
    except Exception as e:
        logger.error("[PROGRESS ERROR] Failed to update status to '%s': %s", status, e)


def is_cancelled(file_id: str, supabase: Client) -> bool:
    """Check DB if cancellation was requested."""
    try:
        resp = (
            supabase.table("vehicle_synthesis")
            .select("verification_status")
            .eq("id", file_id)
            .execute()
        )
        if resp.data and resp.data[0].get("verification_status") == "cancelled":
            return True
        return False
    except Exception:
        return False


def normalize_brand(brand: str | None) -> str | None:
    """Normalize brand name: strip diacritics, uppercase, strip whitespace."""
    import unicodedata as _ud

    if not brand:
        return brand
    normalized = _ud.normalize("NFKD", brand).encode("ASCII", "ignore").decode("utf-8")
    return normalized.strip().upper()
