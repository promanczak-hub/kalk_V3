"""Deterministic post-processor for the digital_twin → card_summary mapping.

The PROBLEM this solves (observed 2026-05-19):
  Gemini 2.5 Flash (`generate_card_summary_from_twin`) reliably drops 80% of
  the data that Gemini 2.5 Pro extracted into `digital_twin`. Concrete cases:
  - Renault Master izoterma_EX (382fceed): digital_twin had 7 options including
    "Zabudowa Kontener Izotermiczny" (47970) and "Agregat Zanotti" (37527),
    card_summary.paid_options=[], service_equipment=null.
  - Toyota Hilux (2b7e9285): digital_twin had 4 options, card_summary same: [].

This module replaces that fuzzy Flash step with deterministic Python rules:
  - paid_options ← optional_equipment WHERE price > 0 AND NOT service-keyword
  - service_equipment.components ← optional_equipment WHERE name matches
    /zabudowa|izoterma|kontener|agregat|chłodnia|skrzynia|wywrotka|plandeka|przegląd|serwis/
  - vehicle_class ← brand+model lookup table
  - body_style ← brand+model hint (Master+zabudowa→Podwozie, Hilux→Pickup, …)
  - base_price/total_price ← digital_twin.financials.* with PLN brutto suffix

IDEMPOTENCY: every fill is "only if missing" — never overwrites a Flash output
when present. Existing tests for Flash output stay valid. Backward-compatible.

This is "Warstwa 3" (NORMALIZE) in the layered pipeline architecture
described to the user 2026-05-19.
"""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any

from core.price_inference import infer_price_pair

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# 0. Robust price parser (handles 'float | int | "738.00 zł" | "47 970.00 zł"')
# ─────────────────────────────────────────────────────────────────────

# Digits + spaces (thousands sep) + dot/comma decimal, optional currency tag.
_PRICE_NUMBER_RE = re.compile(r"[-+]?[\d](?:[\d\s., ])*")


def parse_price_to_float(value: Any) -> float:
    """Robustly coerce a price value (float|int|str) to a non-negative float.

    Handles real-world digital_twin payloads where Pro returns:
      "738.00 zł"      → 738.0
      "47 970.00 zł"   → 47970.0   (NBSP or regular space thousands separator)
      "123,50 zł"      → 123.5     (comma decimal)
      "1 234,56"       → 1234.56
      738.0 / 738      → 738.0
      ""  / None       → 0.0
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return max(float(value), 0.0)
    s = str(value)
    if not s.strip():
        return 0.0
    m = _PRICE_NUMBER_RE.search(s)
    if not m:
        return 0.0
    raw = m.group(0)
    # Remove all whitespace (including U+00A0 NBSP used as Polish thousands sep)
    raw = re.sub(r"\s+", "", raw)
    # Normalize decimal: if both comma and dot present, comma is thousands and dot is decimal.
    # If only comma, treat as decimal. If only dot, decimal.
    if "," in raw and "." in raw:
        # Polish: "1.234,56" — dot=thousands, comma=decimal
        # English: "1,234.56" — comma=thousands, dot=decimal
        # Decide by position of last separator
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return max(float(raw), 0.0)
    except (TypeError, ValueError):
        return 0.0


# ─────────────────────────────────────────────────────────────────────
# 1. Service-equipment keyword catalogue
# ─────────────────────────────────────────────────────────────────────

# Multi-language (PL primary, EN fallback). Names ARE diacritic-folded before
# matching, so we list ASCII forms too where Polish chars are common.
SERVICE_EQUIPMENT_KEYWORDS: tuple[str, ...] = (
    # Polish body conversions
    "zabudowa",
    "izoterm",  # izoterma, izotermiczna, izotermiczny
    "izoterm",
    "kontener",
    "chlodnia",  # ASCII fold of "chłodnia"
    "chłodnia",
    "skrzynia",
    "wywrotka",
    "plandeka",
    "agregat",
    "hds",
    "winda",
    "podnosnik",  # podnośnik
    "podnośnik",
    # Service / maintenance packages
    "przegl",  # przegląd, przeglądów
    "serwis",
    # English fallbacks
    "isotherm",
    "refrigerat",
    "box body",
    "tipper",
    "tarpaulin",
)


def _ascii_fold(s: str) -> str:
    """Fold Polish/German diacritics to ASCII for matching."""
    if not s:
        return ""
    # Handle non-decomposable codepoints first
    s = s.replace("Ł", "L").replace("ł", "l").replace("ß", "ss")
    # NFKD + strip combining marks
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def is_service_equipment_name(name: str | None) -> bool:
    """Return True if the item name matches a service-equipment / zabudowa pattern.

    Case-insensitive, diacritic-folded. Conservative — only matches when a
    keyword appears as a whole word or word-prefix, not as a substring.
    """
    if not name:
        return False
    folded = _ascii_fold(name).lower()
    for kw in SERVICE_EQUIPMENT_KEYWORDS:
        kw_folded = _ascii_fold(kw).lower()
        if kw_folded in folded:
            # Avoid false-positives on "konteneryzacja" (not a body type)
            # by requiring that the keyword stands as a token. Simple heuristic:
            # check that the char before is start-of-string or non-letter.
            idx = folded.find(kw_folded)
            if idx == 0 or not folded[idx - 1].isalpha():
                return True
    return False


# ─────────────────────────────────────────────────────────────────────
# 2. Partition optional_equipment into paid + service
# ─────────────────────────────────────────────────────────────────────


@dataclass
class PartitionResult:
    paid_options: list[dict[str, Any]] = field(default_factory=list)
    service_components: list[dict[str, Any]] = field(default_factory=list)
    paid_options_total_gross: float = 0.0
    service_total_gross: float = 0.0


def partition_optional_equipment(
    optional_equipment: list[dict[str, Any]] | None,
) -> PartitionResult:
    """Split digital_twin.optional_equipment into paid_options + service components.

    Rules:
      - price <= 0  → skip (standard/free item)
      - name matches service keyword → service component (regardless of price)
      - otherwise (price > 0, no service keyword) → paid option

    Returns a PartitionResult with dict-shaped payloads ready for direct
    insertion into card_summary.
    """
    result = PartitionResult()
    if not optional_equipment:
        return result

    for item in optional_equipment:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        price = parse_price_to_float(item.get("price"))

        is_service = is_service_equipment_name(name)

        if price <= 0 and not is_service:
            # Standard/free — skip
            continue

        if is_service:
            result.service_components.append(item)
            result.service_total_gross += max(price, 0.0)
        else:
            result.paid_options.append(item)
            result.paid_options_total_gross += price

    return result


# ─────────────────────────────────────────────────────────────────────
# 3. vehicle_class classifier (brand+model lookup)
# ─────────────────────────────────────────────────────────────────────

# Tier 1: explicit LCV vans (panel vans, chassis, larger commercial)
_LCV_MODELS_RE = (
    "master|trafic|kangoo|express|"
    "sprinter|vito|citan|"
    "crafter|transporter|caddy|caravelle|"
    "transit|ranger|"
    "daily|"
    "boxer|expert|partner|traveller|"
    "jumper|jumpy|berlingo|spacetourer|"
    "movano|vivaro|combo|zafira life|"
    "proace|hiace|"
    "staria|h350|h1|"
    "ducato|talento|scudo|doblo|fiorino|"
    "nv200|nv300|nv400|interstar|primastar"
)

# Tier 2: pickups (technically N1 in EU homologacja → Dostawczy)
_PICKUP_MODELS_RE = (
    "hilux|amarok|ranger|navara|l200|d-?max|"
    "fullback|alaskan|frontier|colorado|tacoma|"
    "tundra|gladiator|ridgeline"
)


def classify_vehicle_class(brand: str | None, model: str | None) -> str | None:
    """Return 'Dostawczy' / 'Osobowy' / None based on brand+model lookup.

    None is returned when we can't decide — caller / HITL fills in.
    """
    if not brand and not model:
        return None
    import re as _re

    model_lc = (model or "").lower()
    if _re.search(_LCV_MODELS_RE, model_lc):
        return "Dostawczy"
    if _re.search(_PICKUP_MODELS_RE, model_lc):
        return "Dostawczy"
    # Otherwise — passenger by default. Conservative for now; HITL can correct.
    return "Osobowy"


# ─────────────────────────────────────────────────────────────────────
# 4. body_style hint
# ─────────────────────────────────────────────────────────────────────


def derive_body_style_hint(
    brand: str | None,
    model: str | None,
    equipment_names: list[str],
) -> str | None:
    """Return a body_style hint or None when unknown.

    Logic:
      - Pickup model → "Pickup"
      - LCV van model + zabudowa in equipment → "Podwozie" (chassis + body conv.)
      - LCV van model + no zabudowa → "Furgon" (panel van default)
      - Otherwise → None (HITL fills)
    """
    if not model:
        return None
    import re as _re

    model_lc = model.lower()

    if _re.search(_PICKUP_MODELS_RE, model_lc):
        return "Pickup"

    if _re.search(_LCV_MODELS_RE, model_lc):
        # Has any service-equipment keyword in optional equipment?
        has_zabudowa = any(is_service_equipment_name(n) for n in (equipment_names or []))
        if has_zabudowa:
            return "Podwozie"
        return "Furgon"

    return None


# ─────────────────────────────────────────────────────────────────────
# 5. Format helpers
# ─────────────────────────────────────────────────────────────────────


def _format_price(amount: float, suffix: str = "brutto") -> str:
    """Format a numeric amount as a Polish price string ('167 218.50 PLN brutto')."""
    return f"{amount:.2f} PLN {suffix}"


def _build_paid_option_payload(
    item: dict[str, Any], default_vat: float = 0.23
) -> dict[str, Any]:
    """Convert a digital_twin.optional_equipment EquipmentItem into a PaidOption-shaped dict."""
    name = item.get("name") or ""
    gross = parse_price_to_float(item.get("price"))
    triple = infer_price_pair(net=None, gross=gross, vat_rate=default_vat)
    return {
        "name": name,
        "price": _format_price(gross, "brutto"),
        "price_type": "brutto",
        "category": "Fabryczna",
        "confidence": 0.8,  # deterministic but Flash dropped it → moderate
        "field_id": str(uuid.uuid4()),
        # V3 numeric fields
        "net_amount": triple.net,
        "gross_amount": triple.gross,
        "vat_rate": triple.vat_rate,
        "conversion_source": triple.conversion_source,
        "canonical_id": "",  # filled by dedup pass downstream
        "duplicate_of": None,
        "source_offsets": None,
        # Provenance marker (audit trail)
        "_source": "deterministic_normalize:digital_twin.optional_equipment",
    }


def _build_service_component_payload(
    item: dict[str, Any], default_vat: float = 0.23
) -> dict[str, Any]:
    """Convert a digital_twin EquipmentItem destined for service_equipment.components."""
    name = item.get("name") or ""
    gross = parse_price_to_float(item.get("price"))
    triple = infer_price_pair(net=None, gross=gross, vat_rate=default_vat)
    return {
        "name": name,
        "price_net": _format_price(triple.net or 0.0, "netto"),
        "price_gross": _format_price(triple.gross or 0.0, "brutto"),
        "confidence": 0.8,
        "field_id": str(uuid.uuid4()),
        "net_amount": triple.net,
        "gross_amount": triple.gross,
        "vat_rate": triple.vat_rate,
        "conversion_source": triple.conversion_source,
        "canonical_id": "",
        "duplicate_of": None,
        "source_offsets": None,
        "_source": "deterministic_normalize:digital_twin.optional_equipment[service]",
    }


def _pick_service_aggregate_name(components: list[dict[str, Any]]) -> str:
    """Pick a sensible service_equipment.name based on its components.

    Heuristic: longest-name component wins (usually the most descriptive).
    Fallback: "Zabudowa / pakiet serwisowy".
    """
    if not components:
        return "Zabudowa / pakiet serwisowy"
    names = [c.get("name", "") for c in components if c.get("name")]
    if not names:
        return "Zabudowa / pakiet serwisowy"
    return max(names, key=len)


# ─────────────────────────────────────────────────────────────────────
# 6. Main entry point
# ─────────────────────────────────────────────────────────────────────


def _is_empty(value: Any) -> bool:
    """Return True when a card_summary field is missing/empty/'Brak'."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in ("", "brak"):
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def normalize_card_summary_from_digital_twin(
    card_summary: dict[str, Any],
    digital_twin: dict[str, Any],
    *,
    brand_fallback: str | None = None,
    model_fallback: str | None = None,
) -> dict[str, Any]:
    """Idempotently fill missing card_summary fields from digital_twin.

    NEVER overwrites a field that's already populated — only patches gaps.
    Returns a NEW dict (does not mutate caller's input).

    Args:
        card_summary: The (possibly Flash-drained) card_summary dict.
        digital_twin: The Pro-extracted twin (optional_equipment, financials, …).
        brand_fallback: Top-level synthesis_data.brand for vehicle_class lookup
            when digital_twin.brand is null (observed in real Renault Master rows).
        model_fallback: Same for model.

    Filled when missing:
      - paid_options[]            from digital_twin.optional_equipment (non-service, price > 0)
      - service_equipment         from digital_twin.optional_equipment (service keywords)
      - vehicle_class             from brand+model lookup
      - body_style                from brand+model + equipment hints
      - base_price / total_price  from digital_twin.financials.*
    """
    if not isinstance(card_summary, dict):
        return card_summary
    out = {k: v for k, v in card_summary.items()}  # shallow copy ok — we replace lists/dicts

    if not isinstance(digital_twin, dict) or not digital_twin:
        # Even with empty twin, brand/model fallback may still let us classify
        if brand_fallback or model_fallback:
            if _is_empty(out.get("vehicle_class")):
                vc = classify_vehicle_class(brand_fallback, model_fallback)
                if vc:
                    out["vehicle_class"] = vc
        return out

    brand = digital_twin.get("brand") or brand_fallback
    model = digital_twin.get("model") or model_fallback
    optional_equipment = digital_twin.get("optional_equipment") or []

    # ── Partition optional_equipment once, reuse below ───────────────
    partition = partition_optional_equipment(optional_equipment)

    # ── paid_options ─────────────────────────────────────────────────
    if _is_empty(out.get("paid_options")):
        out["paid_options"] = [
            _build_paid_option_payload(item) for item in partition.paid_options
        ]
        if out["paid_options"]:
            logger.info(
                "[NORMALIZE] paid_options filled from digital_twin: %d items",
                len(out["paid_options"]),
            )

    # ── service_equipment ────────────────────────────────────────────
    if _is_empty(out.get("service_equipment")) and partition.service_components:
        components = [
            _build_service_component_payload(item)
            for item in partition.service_components
        ]
        total_net = sum(c.get("net_amount") or 0.0 for c in components)
        total_gross = sum(c.get("gross_amount") or 0.0 for c in components)
        out["service_equipment"] = {
            "name": _pick_service_aggregate_name(components),
            "total_price_net": _format_price(total_net, "netto"),
            "total_price_gross": _format_price(total_gross, "brutto"),
            "components": components,
            # V3 aggregate fields
            "net_amount": total_net,
            "gross_amount": total_gross,
            "vat_rate": 0.23,
            "conversion_source": "computed_from_gross",
            "canonical_id": "",
            "duplicate_of": None,
            "source_offsets": None,
            "field_id": str(uuid.uuid4()),
            "_source": "deterministic_normalize",
        }
        logger.info(
            "[NORMALIZE] service_equipment filled: %d components, total %.2f brutto",
            len(components), total_gross,
        )

    # ── vehicle_class ────────────────────────────────────────────────
    if _is_empty(out.get("vehicle_class")):
        vc = classify_vehicle_class(brand, model)
        if vc:
            out["vehicle_class"] = vc
            logger.info("[NORMALIZE] vehicle_class filled: %s (%s %s)", vc, brand, model)

    # ── body_style ──────────────────────────────────────────────────
    if _is_empty(out.get("body_style")):
        equipment_names = [(e.get("name") or "") for e in optional_equipment if isinstance(e, dict)]
        bs = derive_body_style_hint(brand, model, equipment_names)
        if bs:
            out["body_style"] = bs
            logger.info("[NORMALIZE] body_style filled: %s (%s %s)", bs, brand, model)

    # ── base_price / total_price ─────────────────────────────────────
    financials = digital_twin.get("financials") or {}
    if isinstance(financials, dict):
        base_gross = financials.get("base_price_gross")
        final_gross = financials.get("final_price_gross")
        if _is_empty(out.get("base_price")) and isinstance(base_gross, (int, float)):
            out["base_price"] = _format_price(float(base_gross), "brutto")
        if _is_empty(out.get("total_price")) and isinstance(final_gross, (int, float)):
            out["total_price"] = _format_price(float(final_gross), "brutto")

    return out
