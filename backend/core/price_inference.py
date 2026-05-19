"""Deterministic net/gross/VAT triangulation — no hardcoded VAT rate.

Used by the V3 extraction pipeline (`pipeline_normalization`) to reconcile
net_amount, gross_amount and vat_rate fields on PaidOption / ServiceEquipment
/ CardSummary. The single responsibility: given any 1-3 of (net, gross, vat),
produce a consistent PriceTriple, compute missing values, flag conflicts.

Design rules:
- VAT is INPUT, not hardcoded. We support multi-country (PL: 23/8/5/0, DE: 19/7,
  etc.) via `allowed_vat_rates` parameter.
- Tolerance: 2‰ (0.002) on triangulation — same as
  `pipeline_price_validator._SUM_TOLERANCE_PCT`.
- Round outputs to 2 decimals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# Polish VAT rates as of 2026-05-19 (SOT: gov.pl)
DEFAULT_ALLOWED_VAT_RATES: tuple[float, ...] = (0.0, 0.05, 0.08, 0.23)

# Triangulation tolerance — gross vs net*(1+vat). 2‰ = 0.2%.
TRIANGULATION_TOLERANCE = 0.002

# Snap-to-standard tolerance when deriving VAT from net+gross. Same 2‰.
VAT_SNAP_TOLERANCE = 0.002


ConversionSource = Literal[
    "explicit_both",
    "computed_from_net",
    "computed_from_gross",
    "unknown",
]


@dataclass
class PriceTriple:
    """Reconciled (net, gross, vat_rate) triple with provenance + warnings.

    `warnings` contains rule names (e.g. "VAT_TRIANGULATION_FAILED") matching
    `pipeline_price_validator.ValidationWarning.rule` namespace so they can be
    promoted directly into ValidationReport.
    """

    net: Optional[float] = None
    gross: Optional[float] = None
    vat_rate: Optional[float] = None
    conversion_source: ConversionSource = "unknown"
    warnings: list[str] = field(default_factory=list)


def _round2(value: float) -> float:
    return round(value, 2)


def _is_close(a: float, b: float, *, rel_tol: float) -> bool:
    """Relative comparison: |a-b| / max(|a|, |b|) <= rel_tol. Handles zero."""
    if a == 0.0 and b == 0.0:
        return True
    denom = max(abs(a), abs(b))
    if denom == 0.0:
        return False
    return abs(a - b) / denom <= rel_tol


def _snap_to_standard_vat(
    derived: float,
    allowed: tuple[float, ...],
) -> Optional[float]:
    """If `derived` is within VAT_SNAP_TOLERANCE of any allowed rate, return that
    rate; otherwise return None.
    """
    for rate in allowed:
        if abs(derived - rate) <= VAT_SNAP_TOLERANCE:
            return rate
    return None


def infer_price_pair(
    net: Optional[float],
    gross: Optional[float],
    vat_rate: Optional[float],
    *,
    allowed_vat_rates: tuple[float, ...] = DEFAULT_ALLOWED_VAT_RATES,
) -> PriceTriple:
    """Reconcile a (net, gross, vat_rate) triple.

    Returns a PriceTriple with conversion_source + warnings populated.

    Raises:
        ValueError: if any input is negative or vat_rate > 1.0
    """
    # ── Input validation ────────────────────────────────────────────────
    for label, value in (("net", net), ("gross", gross)):
        if value is not None and value < 0:
            raise ValueError(f"{label} must be non-negative, got {value!r}")
    if vat_rate is not None:
        if vat_rate < 0:
            raise ValueError(f"vat_rate must be non-negative, got {vat_rate!r}")
        if vat_rate > 1.0:
            raise ValueError(
                f"vat_rate must be expressed as a fraction (e.g. 0.23 for 23%), "
                f"got {vat_rate!r}. Values >1.0 are rejected to catch unit errors."
            )

    triple = PriceTriple()

    # ── Case 1: nothing provided ────────────────────────────────────────
    if net is None and gross is None:
        triple.vat_rate = vat_rate
        return triple

    # ── Case 2: both net + gross provided ───────────────────────────────
    if net is not None and gross is not None:
        triple.net = _round2(net)
        triple.gross = _round2(gross)
        triple.conversion_source = "explicit_both"

        if vat_rate is not None:
            # All three given — triangulate
            triple.vat_rate = vat_rate
            expected_gross = net * (1.0 + vat_rate)
            if not _is_close(expected_gross, gross, rel_tol=TRIANGULATION_TOLERANCE):
                triple.warnings.append("VAT_TRIANGULATION_FAILED")
            if vat_rate not in allowed_vat_rates:
                triple.warnings.append("VAT_RATE_NON_STANDARD")
        else:
            # Derive VAT from net + gross
            if net == 0.0:
                # Avoid div by zero; gross must also be 0 for sane result
                if gross == 0.0:
                    triple.vat_rate = None
                else:
                    triple.warnings.append("VAT_TRIANGULATION_FAILED")
                    triple.vat_rate = None
            else:
                derived = (gross / net) - 1.0
                snapped = _snap_to_standard_vat(derived, allowed_vat_rates)
                if snapped is not None:
                    triple.vat_rate = snapped
                else:
                    triple.vat_rate = round(derived, 4)
                    triple.warnings.append("VAT_RATE_NON_STANDARD")
        return triple

    # ── Case 3: only net provided ───────────────────────────────────────
    if net is not None and gross is None:
        triple.net = _round2(net)
        if vat_rate is not None:
            triple.vat_rate = vat_rate
            triple.gross = _round2(net * (1.0 + vat_rate))
            triple.conversion_source = "computed_from_net"
            if vat_rate not in allowed_vat_rates:
                triple.warnings.append("VAT_RATE_NON_STANDARD")
        else:
            triple.conversion_source = "unknown"
        return triple

    # ── Case 4: only gross provided ─────────────────────────────────────
    if gross is not None and net is None:
        triple.gross = _round2(gross)
        if vat_rate is not None:
            triple.vat_rate = vat_rate
            triple.net = _round2(gross / (1.0 + vat_rate))
            triple.conversion_source = "computed_from_gross"
            if vat_rate not in allowed_vat_rates:
                triple.warnings.append("VAT_RATE_NON_STANDARD")
        else:
            triple.conversion_source = "unknown"
        return triple

    # Unreachable — all branches above are exhaustive
    return triple  # pragma: no cover
