"""V3 PASS B — NORMALIZE raw extraction into enriched CardSummary.

Takes a `RawExtractionResult` (from `pipeline_raw_extraction`) and produces
a `CardSummary` populated with:
- numeric net_amount / gross_amount / vat_rate (via price_inference)
- canonical_id + duplicate_of flags (via dedup)
- categorized paid_options / service_equipment split
- legacy `base_price`/`options_price`/`total_price` strings (back-compat)
- source_offsets_by_field (pass through from RAW)

Two execution paths:
- Pure-arithmetic (DEFAULT): no second LLM call, deterministic post-processing
  on top of PASS A output. Cheap, fast, deterministic.
- LLM-assisted (`NORMALIZATION_USE_LLM=1`): Flash call for fuzzy categorization
  + body_style/service_equipment split. Slower but handles ambiguity.

The default path is enough for the parity guarantee — the LLM-assisted path
is opt-in for harder offers.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from core.dedup import compute_canonical_id, flag_potential_duplicates
from core.extractor_models import RawExtractionResult, RawOptionLine, RawPriceLine
from core.price_inference import infer_price_pair

logger = logging.getLogger(__name__)


# Heuristic patterns for category hints (multi-language)
_SERVICE_HINT_PATTERNS = re.compile(
    r"\b(zabudow|izoterm|chłodnia|chlodnia|kontener|skrzynia|wywrotk|"
    r"plandek|agregat|hds|winda|przegląd|serwis|service|maintenance)\w*",
    re.IGNORECASE,
)
_FACTORY_HINT_PATTERNS = re.compile(
    r"\b(fabryczn|factory|werks|werkseitig|usine|fabrik)\w*", re.IGNORECASE
)


def _categorize(name: str, hint: str | None) -> str:
    """Decide between 'Fabryczna' / 'Serwisowa/Akcesoria' from hints."""
    if hint:
        h = hint.lower()
        if "fabryczn" in h or "factory" in h:
            return "Fabryczna"
        if "serwis" in h or "service" in h or "zabudowa" in h or "akcesori" in h:
            return "Serwisowa/Akcesoria"
    if _SERVICE_HINT_PATTERNS.search(name):
        return "Serwisowa/Akcesoria"
    if _FACTORY_HINT_PATTERNS.search(name):
        return "Fabryczna"
    return "Fabryczna"  # default — most paid options are factory


def _build_paid_option(opt: RawOptionLine) -> dict[str, Any]:
    """Convert a RawOptionLine into a dict-shaped PaidOption-like payload.

    Triangulates net/gross/vat via price_inference.
    """
    triple = infer_price_pair(
        net=opt.net_amount, gross=opt.gross_amount, vat_rate=opt.vat_rate
    )
    price_str = ""
    if triple.net is not None:
        price_str = f"{triple.net} PLN netto"
    elif triple.gross is not None:
        price_str = f"{triple.gross} PLN brutto"
    return {
        "name": opt.name,
        "price": price_str,
        "price_type": "netto" if triple.net is not None and triple.conversion_source != "computed_from_gross" else "brutto" if triple.gross is not None else "unknown",
        "category": _categorize(opt.name, opt.category_hint),
        "confidence": 1.0 if opt.net_amount is not None or opt.gross_amount is not None else 0.5,
        "field_id": "",
        "net_amount": triple.net,
        "gross_amount": triple.gross,
        "vat_rate": triple.vat_rate,
        "conversion_source": triple.conversion_source,
        "canonical_id": compute_canonical_id(opt.name, triple.net),
        "duplicate_of": None,
        "source_offsets": [s.model_dump() for s in opt.offsets] or None,
    }


def _build_price_string(triple_net: float | None, triple_gross: float | None) -> str:
    if triple_net is not None:
        return f"{triple_net} PLN netto"
    if triple_gross is not None:
        return f"{triple_gross} PLN brutto"
    return "Brak"


def _aggregate_role(
    raw_prices: list[RawPriceLine], role: str
) -> tuple[float | None, float | None, float | None]:
    """Sum or pick the most authoritative price for a top-level role.

    For roles with multiple raw lines (e.g. several `paid_option` lines), this
    is NOT called — caller iterates raw_options directly. This helper covers
    base_price / options_price / total_price aggregates: pick the FIRST
    matching raw_price line (PASS A is responsible for emitting at most one
    per role).
    """
    for line in raw_prices:
        if line.role == role:
            triple = infer_price_pair(
                net=line.net_amount, gross=line.gross_amount, vat_rate=line.vat_rate
            )
            return triple.net, triple.gross, triple.vat_rate
    return None, None, None


def normalize_raw_to_card_summary(
    raw: RawExtractionResult,
    *,
    legacy_card_seed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert a RawExtractionResult into a CardSummary-shaped dict.

    Args:
        raw: PASS A output.
        legacy_card_seed: Optional pre-existing CardSummary dict to merge
            on top of. The legacy `pipeline_card_summary` Flash output can be
            passed here so we keep its `body_style`/`powertrain`/etc fields
            and only enrich numeric/dedup metadata.

    Returns:
        Dict ready to be merged into `vehicle_synthesis.card_summary` jsonb.
    """
    card: dict[str, Any] = dict(legacy_card_seed or {})

    # ── Top-level price triples ────────────────────────────────────────
    for role, prefix in (
        ("base_price", "base_price"),
        ("options_total", "options_price"),
        ("total_price", "total_price"),
    ):
        net, gross, vat = _aggregate_role(raw.raw_prices, role)
        card[f"{prefix}_net"] = net
        card[f"{prefix}_gross"] = gross
        card[f"{prefix}_vat"] = vat
        # Maintain legacy string field for backward compat (FE consumers).
        legacy_key = prefix
        if legacy_key not in card or card.get(legacy_key) in (None, "", "Brak"):
            card[legacy_key] = _build_price_string(net, gross)

    # ── Paid options + service equipment ──────────────────────────────
    paid_options: list[dict[str, Any]] = []
    service_components: list[dict[str, Any]] = []
    service_total_seed: dict[str, Any] | None = None

    for opt in raw.raw_options:
        built = _build_paid_option(opt)
        if built["category"] == "Serwisowa/Akcesoria":
            # Heuristic: items whose name matches zabudowa/serwis go to
            # service_equipment.components by default.
            service_components.append({
                "name": built["name"],
                "price_net": built["price"] if built["price_type"] == "netto" else "",
                "price_gross": built["price"] if built["price_type"] == "brutto" else "",
                "net_amount": built["net_amount"],
                "gross_amount": built["gross_amount"],
                "vat_rate": built["vat_rate"],
                "conversion_source": built["conversion_source"],
                "canonical_id": built["canonical_id"],
                "confidence": built["confidence"],
                "field_id": "",
                "duplicate_of": None,
                "source_offsets": built["source_offsets"],
            })
        else:
            paid_options.append(built)

    if service_components:
        # Aggregate net/gross from components
        total_net = sum(
            c.get("net_amount") or 0.0 for c in service_components if c.get("net_amount") is not None
        )
        total_gross = sum(
            c.get("gross_amount") or 0.0 for c in service_components if c.get("gross_amount") is not None
        )
        vat = service_components[0].get("vat_rate") if service_components else None
        service_total_seed = {
            "name": "Zabudowa / pakiet serwisowy",
            "total_price_net": f"{total_net} PLN" if total_net else "",
            "total_price_gross": f"{total_gross} PLN" if total_gross else "",
            "components": service_components,
            "net_amount": total_net or None,
            "gross_amount": total_gross or None,
            "vat_rate": vat,
            "canonical_id": "",
            "field_id": "se_main",
            "duplicate_of": None,
            "source_offsets": None,
        }

    card["paid_options"] = paid_options
    if service_total_seed is not None:
        card["service_equipment"] = service_total_seed
    elif "service_equipment" not in card:
        card["service_equipment"] = None

    # ── Source offsets passthrough for top-level fields ────────────────
    offset_entries: list[dict[str, Any]] = []
    for line in raw.raw_prices:
        if not line.offsets:
            continue
        field_path = {
            "base_price": "base_price",
            "options_total": "options_price",
            "total_price": "total_price",
        }.get(line.role)
        if not field_path:
            continue
        offset_entries.append({
            "field_path": field_path,
            "spans": [s.model_dump() for s in line.offsets],
        })
    for line in raw.raw_dimension_lines:
        if not line.offsets:
            continue
        offset_entries.append({
            "field_path": f"dimensions.{line.label or 'unknown'}",
            "spans": [s.model_dump() for s in line.offsets],
        })
    if offset_entries:
        card["source_offsets_by_field"] = offset_entries

    # ── Dedup flagging (canonical_id + duplicate_of) ──────────────────
    card = flag_potential_duplicates(card)

    return card
