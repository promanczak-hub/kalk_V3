"""V3 HITL endpoints — structural mutations on extracted card_summary.

Companion to the existing `/extract/hitl/preview` and `/extract/hitl/apply`
in `extract_routes.py`. These three give the user FULL control over what
goes into which bucket and what price it has — addressing the "paid_options
↔ service_equipment duplicate" gap by handing the decision to the user.

Endpoints:
- POST /extract/hitl/move_item/{vehicle_id}  — move a tile between lists
- POST /extract/hitl/update_item/{vehicle_id} — inline edit (price, name, vat)
- POST /extract/hitl/split_item/{vehicle_id} — split a package into components

All three: re-run `flag_potential_duplicates` after mutation, re-run
validator (`validate_and_flag_prices`), persist via `_direct_update_synthesis`,
invalidate the vehicle cache, return the updated `card_summary` + validation.

AI-lockout safe: a UPDATE on `vehicle_synthesis` here is an EXPLICIT USER ACTION
(click in HITL UI), which is allowed by CLAUDE.md rules.
"""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.dedup import compute_canonical_id, flag_potential_duplicates
from core.pipeline_price_validator import validate_and_flag_prices
from core.price_inference import infer_price_pair
from core.redis_cache import cache_invalidate_pattern

logger = logging.getLogger(__name__)

router = APIRouter(tags=["HITL V3"])


# ─────────────────────────────────────────────────────────────────────
# Payload models
# ─────────────────────────────────────────────────────────────────────


class MoveItemPayload(BaseModel):
    """Move a card_summary tile from one list to another."""

    src_path: str = Field(
        description="Where the item lives now: 'paid_options[N]' or "
        "'service_equipment.components[N]' or 'service_equipment'"
    )
    dst_path: str = Field(
        description="Destination list: 'paid_options' or "
        "'service_equipment.components' or 'service_equipment'"
    )
    new_category: Optional[str] = Field(
        default=None,
        description="Override category ('Fabryczna' / 'Serwisowa/Akcesoria'). "
        "If null, derived from destination.",
    )
    merge_into_field_id: Optional[str] = Field(
        default=None,
        description="If set, instead of moving, MERGE source into target item "
        "(target keeps its name, gets summed/maxed price). Source is removed.",
    )


class UpdateItemPayload(BaseModel):
    """Inline edit one tile."""

    path: str = Field(description="Item path: 'paid_options[N]' etc.")
    patch: dict[str, Any] = Field(
        description="Partial fields to overwrite: 'name', 'net_amount', "
        "'gross_amount', 'vat_rate', 'category'. Backend triangulates VAT."
    )


class SplitItemPayload(BaseModel):
    """Split a package into N components."""

    path: str = Field(description="Item path to split: 'paid_options[N]' etc.")
    into: list[dict[str, Any]] = Field(
        description="List of new items: each {name, net_amount} (vat_rate "
        "inherited from parent if not supplied)."
    )


# ─────────────────────────────────────────────────────────────────────
# Helpers — path resolution
# ─────────────────────────────────────────────────────────────────────


def _parse_path(path: str) -> tuple[str, int | None]:
    """Parse 'paid_options[3]' → ('paid_options', 3); 'service_equipment' → (..., None)."""
    if "[" in path and path.endswith("]"):
        base, idx_str = path.split("[", 1)
        idx = int(idx_str.rstrip("]"))
        return base, idx
    return path, None


def _get_item(card: dict[str, Any], path: str) -> dict[str, Any]:
    base, idx = _parse_path(path)
    if base == "service_equipment":
        se = card.get("service_equipment")
        if not isinstance(se, dict):
            raise HTTPException(404, f"No service_equipment to address with {path!r}")
        return se
    if base == "paid_options":
        lst = card.get("paid_options") or []
        if idx is None or not (0 <= idx < len(lst)):
            raise HTTPException(404, f"paid_options[{idx}] out of range")
        return lst[idx]
    if base == "service_equipment.components":
        se = card.get("service_equipment") or {}
        comps = se.get("components") or []
        if idx is None or not (0 <= idx < len(comps)):
            raise HTTPException(404, f"service_equipment.components[{idx}] out of range")
        return comps[idx]
    raise HTTPException(400, f"Unknown path base: {base!r}")


def _remove_item(card: dict[str, Any], path: str) -> dict[str, Any]:
    """Remove and return the item at `path`. 404 when out-of-range/missing."""
    base, idx = _parse_path(path)
    if base == "paid_options":
        lst = card.get("paid_options") or []
        if idx is None or not (0 <= idx < len(lst)):
            raise HTTPException(404, f"paid_options[{idx}] out of range (len={len(lst)})")
        return lst.pop(idx)
    if base == "service_equipment.components":
        se = card.get("service_equipment") or {}
        comps = se.get("components") or []
        if idx is None or not (0 <= idx < len(comps)):
            raise HTTPException(
                404, f"service_equipment.components[{idx}] out of range (len={len(comps)})"
            )
        return comps.pop(idx)
    if base == "service_equipment":
        item = card.get("service_equipment")
        if not item:
            raise HTTPException(404, "service_equipment is empty, nothing to remove")
        card["service_equipment"] = None
        return item
    raise HTTPException(400, f"Cannot remove from path: {base!r}")


def _append_to(card: dict[str, Any], dst: str, item: dict[str, Any]) -> None:
    """Append `item` into the list at `dst` ('paid_options' or 'service_equipment.components')."""
    if dst == "paid_options":
        card.setdefault("paid_options", []).append(item)
    elif dst == "service_equipment.components":
        se = card.get("service_equipment")
        if not isinstance(se, dict):
            se = {
                "name": "Zabudowa / pakiet serwisowy",
                "total_price_net": "",
                "total_price_gross": "",
                "components": [],
            }
            card["service_equipment"] = se
        se.setdefault("components", []).append(item)
    elif dst == "service_equipment":
        # Replace top-level service_equipment with the item
        card["service_equipment"] = item
    else:
        raise HTTPException(400, f"Unknown dst_path: {dst!r}")


# ─────────────────────────────────────────────────────────────────────
# Common post-mutation pipeline
# ─────────────────────────────────────────────────────────────────────


def _retriangulate_item(item: dict[str, Any]) -> None:
    """Re-run price_inference on an item's net/gross/vat after a mutation."""
    triple = infer_price_pair(
        net=item.get("net_amount"),
        gross=item.get("gross_amount"),
        vat_rate=item.get("vat_rate"),
    )
    item["net_amount"] = triple.net
    item["gross_amount"] = triple.gross
    item["vat_rate"] = triple.vat_rate
    item["conversion_source"] = triple.conversion_source
    item["canonical_id"] = compute_canonical_id(
        (item.get("name") or "").strip(), triple.net
    )
    item["duplicate_of"] = None  # reset; flag_potential_duplicates re-computes


def _finalize_card(card: dict[str, Any]) -> dict[str, Any]:
    """Re-run dedup + validation on the mutated card. Returns the card."""
    card = flag_potential_duplicates(card)
    pro_data = {"card_summary": card}
    validate_and_flag_prices(pro_data)
    return pro_data["card_summary"]


# ─────────────────────────────────────────────────────────────────────
# DB I/O — imported lazily to avoid circular imports with extract_routes
# ─────────────────────────────────────────────────────────────────────


def _load_synthesis(vehicle_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load `synthesis_data` for `vehicle_id`. Returns (synthesis_data, card_summary)."""
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
        raise HTTPException(400, "Vehicle has no card_summary to mutate")
    return synthesis, card_summary


def _persist(vehicle_id: str, synthesis: dict[str, Any]) -> None:
    from api.extract_routes import _direct_update_synthesis

    _direct_update_synthesis(vehicle_id, synthesis)
    cache_invalidate_pattern(f"vehicle:{vehicle_id}*")


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────


@router.post("/extract/hitl/move_item/{vehicle_id}")
def hitl_move_item(vehicle_id: str, payload: MoveItemPayload) -> dict[str, Any]:
    """Move a tile between lists. Optionally merge into an existing target.

    Returns: {card_summary, _validation}
    """
    synthesis, card_summary = _load_synthesis(vehicle_id)
    card = copy.deepcopy(card_summary)

    if payload.merge_into_field_id:
        # Find target by field_id, sum source's net_amount into it, drop source
        target = _find_by_field_id(card, payload.merge_into_field_id)
        if target is None:
            raise HTTPException(404, f"merge target {payload.merge_into_field_id} not found")
        source = _remove_item(card, payload.src_path)
        src_net = source.get("net_amount") or 0.0
        tgt_net = target.get("net_amount") or 0.0
        target["net_amount"] = src_net + tgt_net if src_net and tgt_net else (src_net or tgt_net)
        _retriangulate_item(target)
    else:
        item = _remove_item(card, payload.src_path)
        if payload.new_category:
            item["category"] = payload.new_category
        item["field_id"] = item.get("field_id") or str(uuid.uuid4())
        _retriangulate_item(item)
        _append_to(card, payload.dst_path, item)

    card = _finalize_card(card)
    synthesis["card_summary"] = card
    _persist(vehicle_id, synthesis)
    return {"card_summary": card, "_validation": card.get("_validation")}


@router.post("/extract/hitl/update_item/{vehicle_id}")
def hitl_update_item(vehicle_id: str, payload: UpdateItemPayload) -> dict[str, Any]:
    """Inline edit one tile. Re-triangulates VAT, re-computes canonical_id."""
    synthesis, card_summary = _load_synthesis(vehicle_id)
    card = copy.deepcopy(card_summary)
    item = _get_item(card, payload.path)

    allowed_keys = {"name", "net_amount", "gross_amount", "vat_rate", "category", "price_type"}
    for k, v in payload.patch.items():
        if k in allowed_keys:
            item[k] = v
    _retriangulate_item(item)

    card = _finalize_card(card)
    synthesis["card_summary"] = card
    _persist(vehicle_id, synthesis)
    return {"card_summary": card, "_validation": card.get("_validation")}


@router.post("/extract/hitl/split_item/{vehicle_id}")
def hitl_split_item(vehicle_id: str, payload: SplitItemPayload) -> dict[str, Any]:
    """Split a package into N components.

    The source item is removed; each `payload.into[i]` is inserted as a
    new tile in the same list (or in service_equipment.components if source
    was a service-eq aggregate).
    """
    synthesis, card_summary = _load_synthesis(vehicle_id)
    card = copy.deepcopy(card_summary)

    src_item = _remove_item(card, payload.path)
    parent_vat = src_item.get("vat_rate")
    src_base, _ = _parse_path(payload.path)
    dst = "service_equipment.components" if src_base.startswith("service_equipment") else "paid_options"

    new_items: list[dict[str, Any]] = []
    for spec in payload.into:
        new_item = {
            "name": spec.get("name") or "",
            "net_amount": spec.get("net_amount"),
            "gross_amount": spec.get("gross_amount"),
            "vat_rate": spec.get("vat_rate") if spec.get("vat_rate") is not None else parent_vat,
            "category": src_item.get("category") or "Fabryczna",
            "price_type": src_item.get("price_type") or "netto",
            "field_id": str(uuid.uuid4()),
        }
        _retriangulate_item(new_item)
        new_items.append(new_item)
        _append_to(card, dst, new_item)

    card = _finalize_card(card)
    synthesis["card_summary"] = card
    _persist(vehicle_id, synthesis)
    return {
        "card_summary": card,
        "split_into": new_items,
        "_validation": card.get("_validation"),
    }


def _find_by_field_id(card: dict[str, Any], field_id: str) -> dict[str, Any] | None:
    for opt in card.get("paid_options") or []:
        if isinstance(opt, dict) and opt.get("field_id") == field_id:
            return opt
    se = card.get("service_equipment") or {}
    if isinstance(se, dict):
        if se.get("field_id") == field_id:
            return se
        for comp in se.get("components") or []:
            if isinstance(comp, dict) and comp.get("field_id") == field_id:
                return comp
    return None
