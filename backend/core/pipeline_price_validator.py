"""
Deterministic post-extraction financial validator.

Runs arithmetic checks on card_summary prices AFTER LLM extraction,
BEFORE saving to database. Adds `_validation` flags to the output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.price_parser import ParsedPrice, parse_price_string

logger = logging.getLogger(__name__)

# ── Tolerances ──

_SUM_TOLERANCE_PCT = 0.2  # base + options vs total (2‰)
_OPTIONS_TOLERANCE_PCT = 0.2  # sum(paid_options) vs declared options_price (2‰)
_SINGLE_OPTION_MAX_RATIO = 0.50  # single option > 50% of base → alert
_MIN_REALISTIC_PRICE = 70_000.0  # below 70k PLN → suspicious vehicle price
_MAX_REALISTIC_PRICE = 3_000_000.0  # above 3M PLN → suspicious


@dataclass
class ValidationWarning:
    """Single validation issue."""

    rule: str
    message: str
    severity: str  # "INFO" | "WARNING" | "ERROR"
    expected: float | None = None
    actual: float | None = None
    diff_pct: float | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
        }
        if self.expected is not None:
            result["expected"] = self.expected
        if self.actual is not None:
            result["actual"] = self.actual
        if self.diff_pct is not None:
            result["diff_pct"] = round(self.diff_pct, 2)
        return result


@dataclass
class ValidationReport:
    """Full validation result for a card_summary."""

    is_valid: bool = True
    warnings: list[ValidationWarning] = field(default_factory=list)
    parsed_base: float | None = None
    parsed_options: float | None = None
    parsed_total: float | None = None

    def add(self, warning: ValidationWarning) -> None:
        self.warnings.append(warning)
        if warning.severity == "ERROR":
            self.is_valid = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "warnings": [w.to_dict() for w in self.warnings],
            "parsed_prices": {
                "base": self.parsed_base,
                "options": self.parsed_options,
                "total": self.parsed_total,
            },
        }


def validate_card_summary_prices(
    card_summary: dict[str, Any],
) -> ValidationReport:
    """
    Run deterministic arithmetic checks on card_summary prices.

    Rules:
    1. SANITY: prices must be in realistic range
    2. SUM_CHECK: base + options ≈ total (±tolerance)
    3. OPTIONS_CROSS: sum(paid_options) ≈ declared options_price
    4. SINGLE_OPTION: no single option > 50% of base price
    5. BASE_VS_TOTAL: base_price <= total_price (usually)
    """
    report = ValidationReport()

    base = parse_price_string(card_summary.get("base_price"))
    options = parse_price_string(card_summary.get("options_price"))
    total = parse_price_string(card_summary.get("total_price"))

    report.parsed_base = base.value if base else None
    report.parsed_options = options.value if options else None
    report.parsed_total = total.value if total else None

    # ── Rule 1: Sanity check on individual prices ──
    _check_price_sanity(report, "base_price", base)
    _check_price_sanity(report, "total_price", total)

    # ── Rule 2: base + options ≈ total ──
    _check_sum_consistency(report, base, options, total)

    # ── Rule 3: sum(paid_options) ≈ options_price ──
    paid_options = card_summary.get("paid_options", [])
    _check_options_cross_sum(report, options, paid_options)

    # ── Rule 4: No single option > 50% of base ──
    _check_single_option_ratio(report, base, paid_options)

    # ── Rule 5: base <= total ──
    _check_base_vs_total(report, base, total)

    # ── Rule 6: Detect base/total swap ──
    _check_base_total_swap(report, base, options, total)

    # ── Rule 7: Flag unparseable paid_option prices ──
    _check_unparseable_options(report, paid_options)

    _log_report(report)
    return report


def validate_and_flag_prices(pro_data: dict[str, Any]) -> dict[str, Any]:
    """
    Pipeline integration point.

    Runs validation on card_summary and injects `_validation` flags.
    Also detects and normalizes price domain (netto/brutto).
    Returns pro_data with enriched card_summary.
    """
    card_summary = pro_data.get("card_summary")
    if not isinstance(card_summary, dict):
        return pro_data

    # Allow empty dict to still get _validation flags
    report = validate_card_summary_prices(card_summary)
    card_summary["_validation"] = report.to_dict()

    # Detect and propagate price domain
    detected_domain = detect_and_normalize_price_domain(card_summary)
    card_summary["_price_domain"] = detected_domain

    return pro_data


# ── Price domain detection ──

_VAT_RATE = 1.23
_VAT_TOLERANCE = 2.0  # ±2 PLN tolerance for VAT ratio check


def detect_and_normalize_price_domain(
    card_summary: dict[str, Any],
) -> str:
    """
    Deterministically detect whether prices are netto or brutto.

    Priority:
    1. Explicit tax_type from parsed base_price / total_price strings
    2. AI-declared price_domain field
    3. Arithmetic: check if any price pair satisfies A × 1.23 ≈ B
    4. Fallback: "unknown"

    Side effect: propagates detected domain to paid_options[].price_type.
    """
    # Step 1: Check parsed main prices for explicit netto/brutto labels
    base = parse_price_string(card_summary.get("base_price"))
    total = parse_price_string(card_summary.get("total_price"))
    _options = parse_price_string(card_summary.get("options_price"))

    detected = "unknown"

    # Ground truth from explicit label in price string
    for price_obj, label in [(base, "base"), (total, "total")]:
        if price_obj and price_obj.tax_type != "unknown":
            detected = price_obj.tax_type
            logger.info(
                "[PRICE DOMAIN] Wykryto '%s' z etykiety w %s_price",
                detected,
                label,
            )
            break

    # Step 2: If still unknown, use AI-declared price_domain
    if detected == "unknown":
        ai_domain = card_summary.get("price_domain", "unknown")
        if ai_domain in ("netto", "brutto"):
            detected = ai_domain
            logger.info(
                "[PRICE DOMAIN] Użyto AI-deklarowanego price_domain='%s'",
                detected,
            )

    # Step 3: Arithmetic fallback — check VAT ratio between prices
    if detected == "unknown" and base and total:
        detected = _detect_via_vat_arithmetic(base.value, total.value)
        if detected != "unknown":
            logger.info(
                "[PRICE DOMAIN] Wykryto '%s' z arytmetyki VAT (base=%.0f, total=%.0f)",
                detected,
                base.value,
                total.value,
            )

    # Step 4: Propagate to paid_options
    _propagate_domain_to_options(card_summary, detected)

    logger.info("[PRICE DOMAIN] Finalna domena cenowa: '%s'", detected)
    return detected


def _detect_via_vat_arithmetic(price_a: float, price_b: float) -> str:
    """
    Check if two prices are related by VAT (×1.23).

    If price_a × 1.23 ≈ price_b → price_a is netto.
    If price_b × 1.23 ≈ price_a → price_b is netto (prices are brutto).
    """
    if price_a <= 0 or price_b <= 0:
        return "unknown"

    # Check: a is netto, b is brutto
    if abs(price_a * _VAT_RATE - price_b) <= _VAT_TOLERANCE:
        return "netto"  # base is netto

    # Check: b is netto, a is brutto
    if abs(price_b * _VAT_RATE - price_a) <= _VAT_TOLERANCE:
        return "brutto"  # base is brutto

    return "unknown"


def _propagate_domain_to_options(
    card_summary: dict[str, Any],
    domain: str,
) -> None:
    """
    Set price_type on each paid_option that has 'unknown'.

    Also ensures price string contains netto/brutto suffix.
    """
    if domain == "unknown":
        return

    paid_options = card_summary.get("paid_options", [])
    for opt in paid_options:
        if not isinstance(opt, dict):
            continue

        current_type = opt.get("price_type", "unknown")
        if current_type == "unknown":
            # Check if the price string itself has a label
            price_str = opt.get("price", "")
            parsed = parse_price_string(price_str)
            if parsed and parsed.tax_type != "unknown":
                opt["price_type"] = parsed.tax_type
            else:
                opt["price_type"] = domain


# ── Private rule implementations ──


def _check_price_sanity(
    report: ValidationReport,
    field_name: str,
    parsed: ParsedPrice | None,
) -> None:
    if parsed is None:
        return

    if parsed.value < _MIN_REALISTIC_PRICE:
        report.add(
            ValidationWarning(
                rule="PRICE_TOO_LOW",
                message=(
                    f"{field_name} = {parsed.value:.0f} — "
                    f"podejrzanie niska cena pojazdu"
                ),
                severity="WARNING",
                actual=parsed.value,
            )
        )

    if parsed.value > _MAX_REALISTIC_PRICE:
        report.add(
            ValidationWarning(
                rule="PRICE_TOO_HIGH",
                message=(
                    f"{field_name} = {parsed.value:.0f} — "
                    f"podejrzanie wysoka cena pojazdu"
                ),
                severity="WARNING",
                actual=parsed.value,
            )
        )


def _check_sum_consistency(
    report: ValidationReport,
    base: ParsedPrice | None,
    options: ParsedPrice | None,
    total: ParsedPrice | None,
) -> None:
    if base is None or total is None:
        return

    options_val = options.value if options else 0.0
    expected_total = base.value + options_val

    if expected_total == 0:
        return

    diff = abs(expected_total - total.value)
    diff_pct = (diff / expected_total) * 100

    if diff_pct > _SUM_TOLERANCE_PCT:
        severity = "ERROR" if diff_pct > 1.0 else "WARNING"
        report.add(
            ValidationWarning(
                rule="BASE_PLUS_OPTIONS_VS_TOTAL",
                message=(
                    f"baza({base.value:.0f}) + opcje({options_val:.0f}) "
                    f"= {expected_total:.0f}, ale total = {total.value:.0f} "
                    f"(Δ {diff:.0f} / {diff_pct:.1f}%)"
                ),
                severity=severity,
                expected=expected_total,
                actual=total.value,
                diff_pct=diff_pct,
            )
        )


def _check_options_cross_sum(
    report: ValidationReport,
    declared_options: ParsedPrice | None,
    paid_options: list[Any],
) -> None:
    if not paid_options or declared_options is None:
        return

    option_sum = 0.0
    parsed_count = 0
    for opt in paid_options:
        if not isinstance(opt, dict):
            continue
        price_str = opt.get("price", "")
        parsed = parse_price_string(price_str)
        if parsed:
            option_sum += parsed.value
            parsed_count += 1

    if parsed_count == 0 or option_sum == 0:
        return

    diff = abs(option_sum - declared_options.value)
    diff_pct = (diff / declared_options.value) * 100

    if diff_pct > _OPTIONS_TOLERANCE_PCT:
        report.add(
            ValidationWarning(
                rule="OPTIONS_SUM_MISMATCH",
                message=(
                    f"Σ(paid_options) = {option_sum:.0f}, "
                    f"ale options_price = {declared_options.value:.0f} "
                    f"(Δ {diff:.0f} / {diff_pct:.1f}%)"
                ),
                severity="WARNING",
                expected=declared_options.value,
                actual=option_sum,
                diff_pct=diff_pct,
            )
        )


def _check_single_option_ratio(
    report: ValidationReport,
    base: ParsedPrice | None,
    paid_options: list[Any],
) -> None:
    if base is None or not paid_options:
        return

    for opt in paid_options:
        if not isinstance(opt, dict):
            continue
        parsed = parse_price_string(opt.get("price", ""))
        if parsed is None:
            continue

        ratio = parsed.value / base.value
        if ratio > _SINGLE_OPTION_MAX_RATIO:
            report.add(
                ValidationWarning(
                    rule="SINGLE_OPTION_SUSPICIOUSLY_EXPENSIVE",
                    message=(
                        f"Opcja '{opt.get('name', '?')}' kosztuje "
                        f"{parsed.value:.0f} ({ratio:.0%} ceny bazowej)"
                    ),
                    severity="WARNING",
                    actual=parsed.value,
                    diff_pct=ratio * 100,
                )
            )


def _check_base_vs_total(
    report: ValidationReport,
    base: ParsedPrice | None,
    total: ParsedPrice | None,
) -> None:
    if base is None or total is None:
        return

    if total.value < base.value * 0.5:
        report.add(
            ValidationWarning(
                rule="TOTAL_BELOW_BASE",
                message=(
                    f"total({total.value:.0f}) < 50% base({base.value:.0f}) — "
                    f"prawdopodobna halucynacja"
                ),
                severity="ERROR",
                expected=base.value,
                actual=total.value,
            )
        )


def _log_report(report: ValidationReport) -> None:
    if not report.warnings:
        logger.info("[PRICE VALIDATOR] ✅ Wszystkie ceny spójne")
        return

    for w in report.warnings:
        log_fn = logger.warning if w.severity == "WARNING" else logger.error
        log_fn(f"[PRICE VALIDATOR] {w.severity}: {w.message}")


def _check_base_total_swap(
    report: ValidationReport,
    base: ParsedPrice | None,
    options: ParsedPrice | None,
    total: ParsedPrice | None,
) -> None:
    """Detect if LLM swapped base_price and total_price.

    Heuristic: if base > total AND (total + options ≈ base),
    then the fields were likely swapped.
    """
    if base is None or total is None:
        return

    if base.value <= total.value:
        return  # Normal order

    # Check if swap makes the sum work
    options_val = options.value if options else 0.0
    expected_total_if_swapped = total.value + options_val

    # If "swapped base + options" is close to "swapped total" (which is original base)
    if expected_total_if_swapped > 0:
        diff_pct = (
            abs(expected_total_if_swapped - base.value)
            / expected_total_if_swapped
            * 100
        )
        if diff_pct <= 2.0:  # Within 2% tolerance
            report.add(
                ValidationWarning(
                    rule="BASE_TOTAL_SWAPPED",
                    message=(
                        f"base({base.value:.0f}) > total({total.value:.0f}) "
                        f"i po zamianie suma się zgadza (Δ {diff_pct:.1f}%) — "
                        f"LLM prawdopodobnie zamienił pola"
                    ),
                    severity="ERROR",
                    expected=total.value,
                    actual=base.value,
                    diff_pct=diff_pct,
                )
            )
            return

    # Even without sum match, base > total is suspicious
    report.add(
        ValidationWarning(
            rule="BASE_TOTAL_SWAPPED",
            message=(
                f"base({base.value:.0f}) > total({total.value:.0f}) — "
                f"kolejność cen może być odwrócona"
            ),
            severity="WARNING",
            expected=total.value,
            actual=base.value,
        )
    )


def _check_unparseable_options(
    report: ValidationReport,
    paid_options: list[Any],
) -> None:
    """Flag paid_options with missing or unparseable prices.

    These require manual verification.
    """
    if not paid_options:
        return

    unparseable: list[str] = []
    for opt in paid_options:
        if not isinstance(opt, dict):
            continue
        price_str = opt.get("price", "")
        name = opt.get("name", "<brak nazwy>")
        parsed = parse_price_string(price_str)
        if parsed is None:
            unparseable.append(name)

    if unparseable:
        report.add(
            ValidationWarning(
                rule="OPTION_PRICE_UNPARSEABLE",
                message=(
                    f"{len(unparseable)} opcji z brakującą ceną — "
                    f"wymaga weryfikacji: {', '.join(unparseable)}"
                ),
                severity="WARNING",
            )
        )
