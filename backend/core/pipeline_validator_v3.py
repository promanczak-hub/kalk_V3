"""V3 validator rules — VAT triangulation, canonical duplicates, multi-vehicle.

Lives in a separate module so the legacy `pipeline_price_validator` stays
under control (already ~1370 LOC). Wired in via `validate_card_summary_prices`
when `EXTRACTION_PROMPTS_V3=1`.

Rules:
- VAT_TRIANGULATION_FAILED     (ERROR)   — gross ≠ net × (1+vat) ±2‰
- VAT_RATE_NON_STANDARD        (WARNING) — vat ∉ allowed_vat_rates
- CANONICAL_DUPLICATE_DETECTED (INFO)    — _duplicate_flags non-empty
- MULTI_VEHICLE_TWIN_INCOMPLETE (WARNING) — twin missing base or low confidence
"""

from __future__ import annotations

from typing import Any, Iterable

from core.pipeline_price_validator import ValidationReport, ValidationWarning
from core.price_inference import (
    DEFAULT_ALLOWED_VAT_RATES,
    TRIANGULATION_TOLERANCE,
)


# Group keys for top-level price triples on CardSummary.
_PRICE_GROUPS: tuple[tuple[str, str, str, str], ...] = (
    ("base_price", "base_price_net", "base_price_gross", "base_price_vat"),
    ("options_price", "options_price_net", "options_price_gross", "options_price_vat"),
    ("total_price", "total_price_net", "total_price_gross", "total_price_vat"),
)


def _triangulation_ok(net: float, gross: float, vat: float) -> bool:
    """Check `gross ≈ net * (1+vat)` within TRIANGULATION_TOLERANCE."""
    expected = net * (1.0 + vat)
    denom = max(abs(expected), abs(gross))
    if denom == 0.0:
        return expected == gross
    return abs(expected - gross) / denom <= TRIANGULATION_TOLERANCE


def check_vat_triangulation(card: dict[str, Any], report: ValidationReport) -> None:
    """Triangulate net+gross+vat on top-level prices and each paid_option /
    service component / service equipment top-level.

    Adds ValidationWarning(rule='VAT_TRIANGULATION_FAILED', severity='ERROR')
    per failing group.
    """
    # Top-level groups
    for path, net_key, gross_key, vat_key in _PRICE_GROUPS:
        net = card.get(net_key)
        gross = card.get(gross_key)
        vat = card.get(vat_key)
        if net is None or gross is None or vat is None:
            continue
        if not _triangulation_ok(float(net), float(gross), float(vat)):
            report.add(ValidationWarning(
                rule="VAT_TRIANGULATION_FAILED",
                message=(
                    f"Triangulacja VAT zawiodła dla {path}: "
                    f"{net} * (1+{vat}) ≠ {gross} (tolerancja {TRIANGULATION_TOLERANCE * 100:.1f}%)"
                ),
                severity="ERROR",
                expected=round(float(net) * (1.0 + float(vat)), 2),
                actual=float(gross),
                field_path=path,
            ))

    # Paid options
    for idx, opt in enumerate(card.get("paid_options") or []):
        if not isinstance(opt, dict):
            continue
        net = opt.get("net_amount")
        gross = opt.get("gross_amount")
        vat = opt.get("vat_rate")
        if net is None or gross is None or vat is None:
            continue
        if not _triangulation_ok(float(net), float(gross), float(vat)):
            report.add(ValidationWarning(
                rule="VAT_TRIANGULATION_FAILED",
                message=(
                    f"Triangulacja VAT zawiodła dla paid_options[{idx}] '{opt.get('name', '')}': "
                    f"{net} * (1+{vat}) ≠ {gross}"
                ),
                severity="ERROR",
                expected=round(float(net) * (1.0 + float(vat)), 2),
                actual=float(gross),
                field_path=f"paid_options[{idx}]",
            ))

    # Service equipment (top-level + components)
    svc_eq = card.get("service_equipment")
    if isinstance(svc_eq, dict):
        _check_item_triangulation(svc_eq, "service_equipment", report)
        for idx, comp in enumerate(svc_eq.get("components") or []):
            if isinstance(comp, dict):
                _check_item_triangulation(
                    comp, f"service_equipment.components[{idx}]", report
                )


def _check_item_triangulation(
    item: dict[str, Any], path: str, report: ValidationReport
) -> None:
    net = item.get("net_amount")
    gross = item.get("gross_amount")
    vat = item.get("vat_rate")
    if net is None or gross is None or vat is None:
        return
    if not _triangulation_ok(float(net), float(gross), float(vat)):
        report.add(ValidationWarning(
            rule="VAT_TRIANGULATION_FAILED",
            message=(
                f"Triangulacja VAT zawiodła dla {path} '{item.get('name', '')}': "
                f"{net} * (1+{vat}) ≠ {gross}"
            ),
            severity="ERROR",
            expected=round(float(net) * (1.0 + float(vat)), 2),
            actual=float(gross),
            field_path=path,
        ))


def check_vat_rate_standard(
    card: dict[str, Any],
    report: ValidationReport,
    *,
    allowed: tuple[float, ...] = DEFAULT_ALLOWED_VAT_RATES,
) -> None:
    """Flag VAT rates outside the allowed set as WARNING (legitimate edge cases
    exist — e.g. 0% export, 0.19 German VAT — so we warn, not error).
    """
    def _check(vat: Any, path: str) -> None:
        if vat is None:
            return
        try:
            v = float(vat)
        except (TypeError, ValueError):
            return
        if v not in allowed:
            report.add(ValidationWarning(
                rule="VAT_RATE_NON_STANDARD",
                message=f"Stawka VAT {v} (na {path}) poza standardowym zbiorem {allowed}",
                severity="WARNING",
                actual=v,
                field_path=path,
            ))

    for path, _, _, vat_key in _PRICE_GROUPS:
        _check(card.get(vat_key), path)

    for idx, opt in enumerate(card.get("paid_options") or []):
        if isinstance(opt, dict):
            _check(opt.get("vat_rate"), f"paid_options[{idx}]")

    svc_eq = card.get("service_equipment")
    if isinstance(svc_eq, dict):
        _check(svc_eq.get("vat_rate"), "service_equipment")
        for idx, comp in enumerate(svc_eq.get("components") or []):
            if isinstance(comp, dict):
                _check(comp.get("vat_rate"), f"service_equipment.components[{idx}]")


def check_canonical_duplicate(card: dict[str, Any], report: ValidationReport) -> None:
    """Promote `_duplicate_flags` audit log to INFO warnings.

    INFO severity — does NOT block pipeline. Triggers HITL via
    `_HITL_RECOMMENDED_RULES` in phase_2_mapping.
    """
    flags = card.get("_duplicate_flags") or []
    if not isinstance(flags, list):
        return
    for entry in flags:
        if not isinstance(entry, dict):
            continue
        names = entry.get("names") or []
        field_ids = entry.get("field_ids") or []
        report.add(ValidationWarning(
            rule="CANONICAL_DUPLICATE_DETECTED",
            message=(
                f"Wykryto potencjalny duplikat: {names} (field_ids: {field_ids}). "
                f"Otwórz HITL aby zweryfikować — nie usuwamy automatycznie."
            ),
            severity="INFO",
            field_path=",".join(str(f) for f in field_ids) or None,
        ))


def check_multi_vehicle_twin_completeness(
    twins: Iterable[dict[str, Any]] | None,
) -> list[ValidationWarning]:
    """Validate that each twin in a multi-vehicle batch is complete.

    Returns a list of ValidationWarnings (not added to a report — multi-vehicle
    check happens at batch level, before per-twin reports are built).

    Triggers WARNING (not ERROR) when:
    - twin's `base_price` is "Brak" or empty
    - twin's `confidence_score` < 0.5
    Single-twin batches (len==1) are skipped — see CardSummary-level validators.
    """
    if not twins:
        return []
    twins_list = list(twins)
    if len(twins_list) < 2:
        return []

    warnings: list[ValidationWarning] = []
    for idx, twin in enumerate(twins_list):
        if not isinstance(twin, dict):
            continue
        base = (twin.get("base_price") or "").strip().lower()
        confidence = twin.get("confidence_score", 1.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 1.0
        if base in ("", "brak") or confidence < 0.5:
            warnings.append(ValidationWarning(
                rule="MULTI_VEHICLE_TWIN_INCOMPLETE",
                message=(
                    f"Pojazd {idx + 1}/{len(twins_list)} (twin[{idx}]) niekompletny: "
                    f"base_price={twin.get('base_price')!r}, confidence={confidence}"
                ),
                severity="WARNING",
                field_path=f"twins[{idx}]",
                actual=confidence,
            ))
    return warnings


def run_v3_rules(card: dict[str, Any], report: ValidationReport) -> None:
    """Apply all CardSummary-level V3 rules to a single card_summary.

    Multi-vehicle rule must be called separately at batch level (it has a
    different signature — list of twins, returns warnings).
    """
    check_vat_triangulation(card, report)
    check_vat_rate_standard(card, report)
    check_canonical_duplicate(card, report)
