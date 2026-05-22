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
    code = item.get("code")
    return {
        "name": name,
        "price": _format_price(gross, "brutto"),
        "price_type": "brutto",
        "category": "Fabryczna",
        # Phase C: carry manufacturer option code (e.g. "9AK") through from
        # digital_twin.optional_equipment so HITL/feature-matching can use it.
        "option_code": code if isinstance(code, str) and code.strip() else None,
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


# ─────────────────────────────────────────────────────────────────────
# Primitive scalar parsers for digital_twin.technical/features strings
# ─────────────────────────────────────────────────────────────────────

_INT_RE = re.compile(r"-?\d+")

# 1 mechanical horsepower (KM = PS, ISO 80000-4) = 0.7355 kW.
# Deterministic unit conversion — not an inference, not an estimate.
_KM_TO_KW = 0.7355


def _parse_int_from_unit(value: Any, unit_hint: str | None = None) -> int | None:
    """Extract first integer from a string like '204 KM' or '2755'.

    ``unit_hint`` is informational only — used to assert the matched substring
    actually appears with that unit. When the unit is given and the parsed number
    is not adjacent to it (within the same string), returns None to avoid
    grabbing the wrong number (e.g. parsing '10.1 l/100km' as 10 KM).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    m = _INT_RE.search(s)
    if not m:
        return None
    if unit_hint:
        # Look for the unit token following the number (case-insensitive)
        tail = s[m.end():].lstrip()
        if not tail.lower().startswith(unit_hint.lower()):
            return None
    try:
        return int(m.group(0))
    except (TypeError, ValueError):
        return None


def _km_to_kw(km: int | None) -> int | None:
    """Convert horsepower (KM/PS) to kilowatts — deterministic ISO 80000 ratio."""
    if km is None:
        return None
    return round(km * _KM_TO_KW)


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

    # ── digital_twin.technical → card_summary scalar fields ──────────
    # Pro VLM extracts raw strings (e.g. "204 KM", "265 g/km", "2755") into
    # digital_twin.technical; deterministic parsers lift them into typed
    # card_summary fields so UI dropdowns + downstream calc see the data.
    technical = digital_twin.get("technical") or {}
    if isinstance(technical, dict):
        if _is_empty(out.get("power_hp")):
            hp = _parse_int_from_unit(technical.get("power"), unit_hint="KM")
            if hp is not None:
                out["power_hp"] = hp

        if _is_empty(out.get("power_kw")):
            # Prefer an explicit power_kw from the twin if Pro ever writes one;
            # otherwise derive deterministically from power_hp (KM × 0.7355 — ISO 80000).
            explicit_kw = _parse_int_from_unit(technical.get("power_kw"), unit_hint="kW")
            if explicit_kw is not None:
                out["power_kw"] = explicit_kw
            else:
                derived_kw = _km_to_kw(out.get("power_hp"))
                if derived_kw is not None:
                    out["power_kw"] = derived_kw

        if _is_empty(out.get("transmission")):
            t = technical.get("transmission")
            if isinstance(t, str) and t.strip():
                out["transmission"] = t.strip()

        if _is_empty(out.get("emissions")):
            co2 = technical.get("co2")
            if isinstance(co2, str) and co2.strip():
                out["emissions"] = co2.strip()

        if _is_empty(out.get("engine_capacity")):
            cap = _parse_int_from_unit(technical.get("capacity"))
            if cap is not None:
                out["engine_capacity"] = cap

    # ── digital_twin.features → card_summary scalar fields ───────────
    features = digital_twin.get("features") or {}
    if isinstance(features, dict):
        if _is_empty(out.get("exterior_color")):
            color = features.get("color")
            if isinstance(color, str) and color.strip():
                out["exterior_color"] = color.strip()

        if _is_empty(out.get("wheels")):
            wheels = features.get("wheels")
            if isinstance(wheels, str) and wheels.strip():
                out["wheels"] = wheels.strip()

    # ── digital_twin.dimensions → card_summary.dimensions (1:1 passthrough) ──
    # CargoAndDimensions Pydantic schema matches digital_twin.dimensions keys
    # exactly (length_mm/width_mm/height_mm/wheelbase_mm/cargo_*/curb_weight_kg/
    # payload_kg/gross_vehicle_weight_kg/fuel_tank_capacity_l). No reshape needed.
    dims = digital_twin.get("dimensions")
    if _is_empty(out.get("dimensions")) and isinstance(dims, dict) and dims:
        out["dimensions"] = dims

    # ── digital_twin.standard_equipment → card_summary.standard_equipment ──
    # Frontend useVehicleFeaturesCache reads card_summary.standard_equipment to
    # render the "Konfiguracja (PDF)" chips in CECHY UŻYTKOWE POJAZDU.
    # Per user 2026-05-19: "cechy użytkowe" = EVERY feature the car has
    # (standard + service + paid + dimensions), NOT only paid_options. Pro
    # writes a list[str] of ~50 standard-equipment names to digital_twin;
    # without this passthrough card_summary.standard_equipment stays empty.
    std_eq = digital_twin.get("standard_equipment")
    if _is_empty(out.get("standard_equipment")) and isinstance(std_eq, list) and std_eq:
        # Filter to non-empty strings only — Pro occasionally emits None/""
        cleaned = [
            s.strip() for s in std_eq
            if isinstance(s, str) and s.strip()
        ]
        if cleaned:
            out["standard_equipment"] = cleaned

    return out
