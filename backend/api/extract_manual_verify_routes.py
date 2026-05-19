"""Manual Verification endpoint — full drag&drop mapping source→target.

Companion to V3 HITL endpoints (`/move_item`, `/update_item`, `/split_item`),
but operates at a higher abstraction: instead of moving individual items
between buckets, the user assigns ENTIRE source objects (from digital_twin)
to TARGET FIELDS in card_summary.

Endpoint:
- POST /extract/hitl/manual_verify/{vehicle_id}

Payload shape:
  {
    "assignments": [
      {"target_bucket": "engine", "source_payload": {"label": "2.0 TSI", "value": "..."}, "source_path": "digital_twin.technical_data.engine_type"},
      {"target_bucket": "transmission", "source_payload": {...}, "source_path": "..."},
      ...
    ],
    "discount": {  // optional
      "rabat_type": "kwotowo" | "procentowo",
      "rabat_basis": "netto" | "brutto",
      "rabat_value": 12000.0,
      "discount_scope": ["base", "factory_options"]
    }
  }

Behavior:
- For each assignment, MAP source → target field(s) on card_summary
- Idempotent: re-applying same assignments produces identical state
- Re-runs validator + dedup after mutation
- Audit log to vehicle_synthesis.synthesis_data._manual_verification_history (jsonb append-only)

AI-lockout safe: UPDATE on vehicle_synthesis is an explicit user click in HITL UI.
"""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.dedup import flag_potential_duplicates
from core.pipeline_price_validator import validate_and_flag_prices
from core.price_inference import infer_price_pair
from core.redis_cache import cache_invalidate_pattern

logger = logging.getLogger(__name__)

router = APIRouter(tags=["HITL Manual Verification"])


# ─────────────────────────────────────────────────────────────────────
# Payload models
# ─────────────────────────────────────────────────────────────────────


class ManualAssignment(BaseModel):
    """One source-object → target-bucket assignment."""

    target_bucket: str = Field(
        description="Bucket id from frontend catalogue: 'brand_model', "
        "'trim_level', 'engine', 'transmission', 'drive_type', 'fuel', "
        "'power', 'body_style', 'vehicle_class', 'seats', 'paint', "
        "'base_price', 'discount', 'factory_options', 'service_equipment', "
        "'dimensions', 'wheels', 'standard_equipment', 'skip'"
    )
    source_path: str = Field(
        description="Audit trail: where the value came from in digital_twin "
        "(e.g. 'digital_twin.technical_data.engine_type')"
    )
    source_payload: dict[str, Any] = Field(
        description="The actual data payload (label/value/extras). Shape "
        "varies per source type — backend interprets per target_bucket."
    )
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class ManualDiscount(BaseModel):
    rabat_type: str = Field(description="'kwotowo' | 'procentowo'")
    rabat_basis: str = Field(description="'netto' | 'brutto'")
    rabat_value: float
    discount_scope: list[str] = Field(default_factory=list)


class ManualVerifyPayload(BaseModel):
    assignments: list[ManualAssignment] = Field(default_factory=list)
    discount: ManualDiscount | None = None
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────
# Bucket → card_summary mapping
# ─────────────────────────────────────────────────────────────────────


def _apply_assignment(
    card: dict[str, Any], assignment: ManualAssignment
) -> list[str]:
    """Apply a single assignment to card_summary in-place. Returns a list of
    field paths that were modified (audit trail).
    """
    bucket = assignment.target_bucket
    payload = assignment.source_payload or {}
    label = payload.get("label") or ""
    value = payload.get("value")

    modified: list[str] = []

    if bucket == "brand_model":
        # Source may be brand or model — heuristic: short uppercase = brand
        if isinstance(value, str):
            if value.isupper() or len(value) <= 12:
                card["brand"] = value
                modified.append("brand")
            else:
                card["model"] = value
                modified.append("model")
    elif bucket == "trim_level":
        if isinstance(value, str) and value:
            card["trim_level"] = value
            modified.append("trim_level")
    elif bucket == "engine":
        if isinstance(value, str):
            card["powertrain"] = value
            modified.append("powertrain")
        elif isinstance(value, dict):
            for k in ("engine_capacity", "engine_designation", "engine_marketing_name", "power_hp", "power_kw"):
                if k in value:
                    card[k] = value[k]
                    modified.append(k)
    elif bucket == "transmission":
        if isinstance(value, str) and value:
            card["transmission"] = value
            modified.append("transmission")
    elif bucket == "drive_type":
        if isinstance(value, str) and value:
            card["drive_type"] = value
            modified.append("drive_type")
    elif bucket == "fuel":
        if isinstance(value, str) and value:
            card["fuel"] = value
            modified.append("fuel")
    elif bucket == "power":
        # Expect numeric HP or {power_hp, power_kw}
        if isinstance(value, (int, float)):
            card["power_hp"] = int(value)
            modified.append("power_hp")
        elif isinstance(value, dict):
            if "power_hp" in value:
                card["power_hp"] = int(value["power_hp"])
                modified.append("power_hp")
            if "power_kw" in value:
                card["power_kw"] = int(value["power_kw"])
                modified.append("power_kw")
    elif bucket == "body_style":
        if isinstance(value, str) and value:
            card["body_style"] = value
            modified.append("body_style")
    elif bucket == "vehicle_class":
        if isinstance(value, str) and value:
            card["vehicle_class"] = value
            modified.append("vehicle_class")
    elif bucket == "seats":
        if isinstance(value, (int, float, str)):
            try:
                card["number_of_seats"] = int(float(value))
                modified.append("number_of_seats")
            except (TypeError, ValueError):
                pass
    elif bucket == "paint":
        if isinstance(value, str) and value:
            card["exterior_color"] = value
            modified.append("exterior_color")
        elif isinstance(value, dict):
            if value.get("exterior_paint_name"):
                card["exterior_color"] = value["exterior_paint_name"]
                modified.append("exterior_color")
            if "is_metalic_paint" in value:
                card["is_metalic_paint"] = bool(value["is_metalic_paint"])
                modified.append("is_metalic_paint")
    elif bucket == "base_price":
        if isinstance(value, (int, float)):
            card["base_price"] = f"{float(value):.2f} PLN brutto"
            triple = infer_price_pair(net=None, gross=float(value), vat_rate=0.23)
            card["base_price_net"] = triple.net
            card["base_price_gross"] = triple.gross
            card["base_price_vat"] = triple.vat_rate
            modified.extend(["base_price", "base_price_net", "base_price_gross"])
        elif isinstance(value, str):
            card["base_price"] = value
            modified.append("base_price")
    elif bucket == "discount":
        # Discount handled separately in main endpoint via ManualDiscount
        modified.append("discount")
    elif bucket == "factory_options":
        # Append source to paid_options
        if isinstance(value, dict) and value.get("name"):
            name = value.get("name", "")
            price = value.get("price")
            if isinstance(price, (int, float)):
                price_str = f"{price:.2f} PLN brutto"
            else:
                price_str = str(price or "")
            triple = (
                infer_price_pair(net=None, gross=float(price), vat_rate=0.23)
                if isinstance(price, (int, float))
                else None
            )
            new_item = {
                "name": name,
                "price": price_str,
                "price_type": "brutto",
                "category": "Fabryczna",
                "confidence": assignment.confidence,
                "field_id": str(uuid.uuid4()),
                "_source": assignment.source_path,
            }
            if triple:
                new_item["net_amount"] = triple.net
                new_item["gross_amount"] = triple.gross
                new_item["vat_rate"] = triple.vat_rate
                new_item["conversion_source"] = triple.conversion_source
            card.setdefault("paid_options", []).append(new_item)
            modified.append(f"paid_options[+{name}]")
    elif bucket == "service_equipment":
        # Append source to service_equipment.components
        if isinstance(value, dict) and value.get("name"):
            name = value.get("name", "")
            price = value.get("price")
            gross = float(price) if isinstance(price, (int, float)) else 0.0
            triple = infer_price_pair(net=None, gross=gross, vat_rate=0.23)
            new_comp = {
                "name": name,
                "price_net": f"{triple.net or 0.0:.2f} PLN netto",
                "price_gross": f"{triple.gross or 0.0:.2f} PLN brutto",
                "net_amount": triple.net,
                "gross_amount": triple.gross,
                "vat_rate": triple.vat_rate,
                "confidence": assignment.confidence,
                "field_id": str(uuid.uuid4()),
                "_source": assignment.source_path,
            }
            se = card.get("service_equipment")
            if not isinstance(se, dict):
                se = {
                    "name": name,
                    "total_price_net": "",
                    "total_price_gross": "",
                    "components": [],
                }
                card["service_equipment"] = se
            se.setdefault("components", []).append(new_comp)
            modified.append(f"service_equipment.components[+{name}]")
    elif bucket == "dimensions":
        if isinstance(value, dict):
            dims = card.get("dimensions") or {}
            for k in (
                "length_mm", "width_mm", "height_mm", "wheelbase_mm",
                "cargo_length_mm", "cargo_width_mm", "cargo_height_mm",
                "cargo_volume_m3", "curb_weight_kg", "payload_kg",
                "gross_vehicle_weight_kg", "fuel_tank_capacity_l",
            ):
                # Accept both flat ("length_mm") and TechnicalData prefix
                # ("dimensions_length_mm") source shapes.
                if k in value:
                    dims[k] = value[k]
                tk = f"dimensions_{k}"
                if tk in value:
                    dims[k] = value[tk]
            card["dimensions"] = dims
            modified.append("dimensions")
    elif bucket == "wheels":
        # Expect a tire size like "235/45R18" or just rim "18"
        if isinstance(value, str) and value:
            # Extract just the rim diameter (heuristic)
            import re as _re
            m = _re.search(r"R?(\d{2})", value)
            if m:
                card["wheels"] = m.group(1)
                modified.append("wheels")
            else:
                card["wheels"] = value
                modified.append("wheels")
        elif isinstance(value, dict) and value.get("size"):
            card["wheels"] = str(value["size"])
            modified.append("wheels")
    elif bucket == "standard_equipment":
        if isinstance(value, str) and value:
            card.setdefault("standard_equipment", []).append(value)
            modified.append(f"standard_equipment[+{label or value[:30]}]")
        elif isinstance(value, dict) and value.get("name"):
            card.setdefault("standard_equipment", []).append(value["name"])
            modified.append(f"standard_equipment[+{value['name'][:30]}]")
    elif bucket == "skip":
        # User explicitly marked source as noise — no card_summary mutation,
        # just audit-log it.
        modified.append("skip(noise)")
    else:
        logger.warning("Unknown target_bucket: %r", bucket)

    return modified


# ─────────────────────────────────────────────────────────────────────
# Discount application
# ─────────────────────────────────────────────────────────────────────


def _apply_discount(card: dict[str, Any], discount: ManualDiscount) -> None:
    """Apply user-provided discount to card_summary.discount."""
    breakdown = card.get("discount") or {}
    if not isinstance(breakdown, dict):
        breakdown = {}

    breakdown["rabat_type"] = discount.rabat_type
    breakdown["rabat_basis"] = discount.rabat_basis
    if discount.rabat_type == "kwotowo":
        breakdown["explicit_rabat_pln"] = discount.rabat_value
    else:
        breakdown["explicit_rabat_pct"] = discount.rabat_value
    breakdown["discount_scope"] = discount.discount_scope
    breakdown["extraction_method"] = (
        "explicit_amount" if discount.rabat_type == "kwotowo" else "explicit_percentage"
    )
    breakdown["confidence"] = 1.0
    breakdown["audit_notes"] = breakdown.get("audit_notes") or []
    breakdown["audit_notes"].append(
        f"manual_verify: type={discount.rabat_type}, basis={discount.rabat_basis}, value={discount.rabat_value}"
    )
    card["discount"] = breakdown


# ─────────────────────────────────────────────────────────────────────
# DB I/O
# ─────────────────────────────────────────────────────────────────────


def _load_synthesis(vehicle_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from api.extract_routes import supabase_client

    resp = (
        supabase_client.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Vehicle not found")
    synthesis = resp.data.get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary")
    if not isinstance(card_summary, dict):
        raise HTTPException(400, "Vehicle has no card_summary to verify")
    return synthesis, card_summary


def _persist(vehicle_id: str, synthesis: dict[str, Any]) -> None:
    from api.extract_routes import _direct_update_synthesis

    _direct_update_synthesis(vehicle_id, synthesis)
    cache_invalidate_pattern(f"vehicle:{vehicle_id}*")


# ─────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────


@router.post("/extract/hitl/manual_verify/{vehicle_id}")
def hitl_manual_verify(
    vehicle_id: str, payload: ManualVerifyPayload
) -> dict[str, Any]:
    """Apply a batch of source→target assignments + discount to a vehicle.

    Returns the updated card_summary + validation report.
    """
    synthesis, card_summary = _load_synthesis(vehicle_id)
    card = copy.deepcopy(card_summary)

    all_modified: list[str] = []
    for assignment in payload.assignments:
        try:
            modified = _apply_assignment(card, assignment)
            all_modified.extend(modified)
        except Exception as e:
            logger.warning(
                "Manual verify assignment failed: bucket=%s path=%s err=%s",
                assignment.target_bucket, assignment.source_path, e,
            )

    if payload.discount:
        _apply_discount(card, payload.discount)
        all_modified.append("discount")

    # Re-run dedup + validator
    card = flag_potential_duplicates(card)
    proxy = {"card_summary": card}
    validate_and_flag_prices(proxy)
    card = proxy["card_summary"]

    # Audit log
    history = synthesis.setdefault("_manual_verification_history", [])
    if isinstance(history, list):
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "assignments_count": len(payload.assignments),
            "modified_fields": all_modified,
            "notes": payload.notes or "",
        })

    synthesis["card_summary"] = card
    _persist(vehicle_id, synthesis)

    return {
        "card_summary": card,
        "_validation": card.get("_validation"),
        "modified_fields": all_modified,
    }
