"""Manual-blank vehicle creation — alternative entry to the HITL wizard.

`POST /extract/blank` inserts a fresh `vehicle_synthesis` row with a SKELETAL
`synthesis_data.card_summary` and marks `_origin="manual_blank"`. The user
then fills in everything (powertrain, body_style, paid_options, etc.) via
the existing HITL UI (`/extract/hitl/manual_verify` + `/hitl/preview` +
`/hitl/apply` + `/hitl/move_item|update_item|split_item`).

SOT mapping (engines, samar_classes, body_types) is deferred to the FIRST
`/extract/hitl/apply` call — at that point the user has supplied the
minimum required fields (fuel especially, which `map_to_engine_class`
needs). See `extract_routes.py:hitl_apply` for the trigger.

AI-lockout safe: only INSERT, no destructive ops.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import supabase as supabase_client
from core.redis_cache import cache_invalidate_pattern

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Extract — Blank"])


class CreateBlankRequest(BaseModel):
    """Optional pre-seed values. All fields nullable — user can fill later in HITL."""

    brand: str | None = None
    model: str | None = None
    vehicle_class: str = "Osobowy"


def _build_skeleton(req: CreateBlankRequest) -> dict:
    """Minimal synthesis_data so HITL endpoints don't 400 on missing keys.

    Keys chosen to satisfy:
    - `card_summary` MUST be a dict (hitl_preview / hitl_apply / V3 mutations all
      return 400 otherwise).
    - `paid_options` MUST be a list (hitl_apply iterates it).
    - `service_equipment` MAY be None (V3 move_item promotes it on first add).
    - String fields default to "Brak" — matches the convention used by Vertex
      output for missing data, so downstream parsers behave identically.
    - `_origin="manual_blank"` is the one-shot trigger consumed (and popped) in
      hitl_apply to run finalize_vehicle_pipeline once.
    - `_requires_user_input` is purely informational for the UI to highlight
      mandatory fields; backend doesn't enforce it (the fuel guard in
      hitl_apply does).
    """
    return {
        "_origin": "manual_blank",
        "mapped_ai_data": {},
        "card_summary": {
            "powertrain": "",
            "vehicle_class": req.vehicle_class,
            "body_style": "",
            "trim_level": "",
            "base_price": "Brak",
            "options_price": "Brak",
            "total_price": "Brak",
            "fuel": "Brak",
            "transmission": "Brak",
            "wheels": "Brak",
            "exterior_color": "Brak",
            "standard_equipment": [],
            "paid_options": [],
            "service_equipment": None,
            "available_powertrains": [],
            "financial_reasoning": "Manual draft — created via UI without source PDF",
            "price_domain": "netto",
            "_requires_user_input": [
                "base_price",
                "powertrain",
                "body_style",
                "fuel",
            ],
        },
    }


@router.post("/extract/blank")
def create_blank_vehicle(req: CreateBlankRequest) -> dict:
    """Create an empty vehicle_synthesis row for manual HITL fill-in.

    Returns `{vehicle_id, verification_status}`. Frontend should:
    1. Append `?highlight=<vehicle_id>` to URL (or set local highlight state).
    2. Refresh the vehicle list — realtime INSERT subscription also fires.
    3. Auto-expand the new row so the user lands in the HITL wizard inline.
    """
    new_id = str(uuid.uuid4())
    skeleton = _build_skeleton(req)

    try:
        supabase_client.table("vehicle_synthesis").insert(
            {
                "id": new_id,
                "verification_status": "needs_review",
                "brand": req.brand,
                "model": req.model,
                "synthesis_data": skeleton,
            }
        ).execute()
    except Exception as e:
        logger.exception("Failed to insert blank vehicle_synthesis row: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create blank vehicle: {e}",
        )

    cache_invalidate_pattern("initial_data")
    cache_invalidate_pattern("filters:*")

    logger.info(
        "[BLANK] Created manual-draft vehicle_synthesis id=%s brand=%r model=%r",
        new_id,
        req.brand,
        req.model,
    )

    return {
        "vehicle_id": new_id,
        "verification_status": "needs_review",
    }
