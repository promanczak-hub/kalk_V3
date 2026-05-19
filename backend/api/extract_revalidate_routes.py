"""Re-validate vehicle endpoint — flips verification_status after user edits.

Called by frontend save handlers (VehicleSummaryCard, VehicleEquipmentCard,
VehicleServiceOptionsCard, DiscountAuditCard, VehicleFinancialOptions, etc.)
after persisting field changes. The endpoint re-runs the deterministic
validator + HITL review heuristic; if no blocking issues remain, status
flips from "needs_review" to "completed" (removing the persistent yellow
border on the vehicle row).

Idempotent — safe to call after every save. Validator is pure-Python,
cheap (no LLM), so the per-call cost is negligible.

Audit history (so we can see WHY status changed):
synthesis_data._revalidation_history: list[{timestamp, before, after, reasons}]

AI-lockout safe: UPDATE on vehicle_synthesis is triggered by an explicit
user save action in the UI.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from core.redis_cache import cache_invalidate_pattern

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Re-validation"])


@router.post("/extract/revalidate/{vehicle_id}")
def revalidate_vehicle(vehicle_id: str) -> dict[str, Any]:
    """Re-run validator + HITL review check; flip verification_status accordingly.

    Returns:
        {
          "vehicle_id": str,
          "verification_status_before": str,
          "verification_status": str,         # new status
          "needs_review": bool,
          "reasons": list[str],               # empty when status flipped to "completed"
          "changed": bool                     # True if status changed
        }
    """
    # Import lazily to avoid circular imports with extract_routes
    from api.extract_routes import _direct_update_synthesis, supabase_client
    from core.extraction_pipeline.phase_2_mapping import _needs_hitl_review
    from core.pipeline_price_validator import validate_and_flag_prices

    try:
        resp = (
            supabase_client.table("vehicle_synthesis")
            .select("id, synthesis_data, verification_status")
            .eq("id", vehicle_id)
            .single()
            .execute()
        )
    except Exception as e:
        # Supabase raises APIError for invalid UUID format or missing row.
        # Convert to a clean 404 instead of 500.
        msg = str(e).lower()
        if "invalid input syntax" in msg or "0 rows" in msg or "pgrst116" in msg:
            raise HTTPException(status_code=404, detail="Vehicle not found") from e
        raise
    if not resp.data:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    synthesis = resp.data.get("synthesis_data") or {}
    if not isinstance(synthesis, dict):
        raise HTTPException(status_code=400, detail="Vehicle has no synthesis_data")

    status_before = resp.data.get("verification_status") or "unknown"

    # Some statuses should never be auto-flipped — they represent terminal
    # or in-progress states that the user must resolve explicitly.
    if status_before in ("uploading", "processing", "cancelled", "error"):
        return {
            "vehicle_id": vehicle_id,
            "verification_status_before": status_before,
            "verification_status": status_before,
            "needs_review": False,
            "reasons": [f"status_locked:{status_before}"],
            "changed": False,
        }

    # Re-run financial validator — refreshes synthesis_data._validation
    synthesis = validate_and_flag_prices(synthesis)

    # Re-run HITL review heuristic on the refreshed card_summary
    card_summary = synthesis.get("card_summary") or {}
    needs_review, reasons = _needs_hitl_review(card_summary)

    new_status = "needs_review" if needs_review else "completed"
    changed = new_status != status_before

    # Audit trail — append regardless of whether status changed
    history = synthesis.setdefault("_revalidation_history", [])
    if isinstance(history, list):
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "before": status_before,
            "after": new_status,
            "reasons": reasons,
        })
        # Trim to last 20 entries to avoid unbounded growth
        if len(history) > 20:
            del history[: len(history) - 20]

    # Persist synthesis (refreshed _validation + audit trail)
    _direct_update_synthesis(vehicle_id, synthesis)
    # Flip status only when actually changed (avoid unnecessary writes)
    if changed:
        supabase_client.table("vehicle_synthesis").update(
            {"verification_status": new_status}
        ).eq("id", vehicle_id).execute()
        cache_invalidate_pattern(f"vehicle:{vehicle_id}*")
        logger.info(
            "[REVALIDATE] vehicle=%s status %s → %s (reasons=%d)",
            vehicle_id, status_before, new_status, len(reasons),
        )

    return {
        "vehicle_id": vehicle_id,
        "verification_status_before": status_before,
        "verification_status": new_status,
        "needs_review": needs_review,
        "reasons": reasons,
        "changed": changed,
    }
