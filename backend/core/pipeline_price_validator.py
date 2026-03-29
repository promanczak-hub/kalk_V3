"""
Deterministic post-extraction financial validator.

Runs arithmetic checks on card_summary prices AFTER LLM extraction,
BEFORE saving to database. Adds `_validation` flags to the output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.pipeline_price_summary import generate_price_summary
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
    summary: dict[str, Any] | None = None

    def add(self, warning: ValidationWarning) -> None:
        self.warnings.append(warning)
        if warning.severity == "ERROR":
            self.is_valid = False

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "is_valid": self.is_valid,
            "warnings": [w.to_dict() for w in self.warnings],
            "parsed_prices": {
                "base": self.parsed_base,
                "options": self.parsed_options,
                "total": self.parsed_total,
            },
        }
        if self.summary is not None:
            result["summary"] = self.summary
        return result


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

    # ── Rule 8: Power consistency (kW vs HP) ──
    _check_power_consistency(report, card_summary)

    _log_report(report)
    return report


def validate_and_flag_prices(pro_data: dict[str, Any]) -> dict[str, Any]:
    """
    Pipeline integration point.

    Runs validation on card_summary and injects `_validation` flags.
    Also detects and normalizes price domain (netto/brutto).
    Generates an LLM-powered natural-language summary of findings.
    Returns pro_data with enriched card_summary.
    """
    card_summary = pro_data.get("card_summary")
    if not isinstance(card_summary, dict):
        return pro_data

    # Allow empty dict to still get _validation flags
    report = validate_card_summary_prices(card_summary)

    # Apply self-healing rules if mathematically inconsistent
    _apply_self_healing(card_summary, report)

    # Generate NL summary (Gemini Flash + deterministic fallback)
    validation_dict = report.to_dict()
    report.summary = generate_price_summary(validation_dict, card_summary)

    card_summary["_validation"] = report.to_dict()

    # Detect and propagate price domain
    detected_domain = detect_and_normalize_price_domain(card_summary)
    card_summary["_price_domain"] = detected_domain

    # ── User-facing warning when price domain cannot be determined ──
    if detected_domain == "unknown":
        validation_dict = card_summary.get("_validation", {})
        existing_warnings = validation_dict.get("warnings", [])
        existing_warnings.append(
            {
                "rule": "PRICE_DOMAIN_UNKNOWN",
                "message": (
                    "⚠️ Nie udało się ustalić domeny cenowej (netto/brutto). "
                    "System domyślnie przyjmie BRUTTO. "
                    "Zweryfikuj ręcznie ceny bazową i końcową."
                ),
                "severity": "WARNING",
            }
        )
        validation_dict["warnings"] = existing_warnings
        validation_dict["is_valid"] = False
        card_summary["_validation"] = validation_dict
        logger.warning(
            "[PRICE DOMAIN] Domena cenowa 'unknown' — "
            "dodano ostrzeżenie dla użytkownika"
        )

    return pro_data


def _apply_self_healing(card_summary: dict[str, Any], report: ValidationReport) -> None:
    """Attempt to auto-fix certain mathematical errors in card_summary before generation of summary."""
    sum_warning = next(
        (w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"), None
    )

    if sum_warning and report.parsed_base and report.parsed_total:
        if report.parsed_base < report.parsed_total:
            # We trust base and total more than options string
            corrected_options_val = report.parsed_total - report.parsed_base

            original_options = str(card_summary.get("options_price", ""))

            # Determine currency and suffix from total_price
            total_str = str(card_summary.get("total_price", ""))
            domain_suffix = ""
            if "netto" in total_str.lower():
                domain_suffix = " netto"
            elif "brutto" in total_str.lower():
                domain_suffix = " brutto"

            currency = " PLN" if "PLN" in total_str.upper() else ""
            if not currency and "PLN" in original_options.upper():
                currency = " PLN"

            # Update card_summary
            card_summary["options_price"] = (
                f"{int(corrected_options_val)}{currency}{domain_suffix}".strip()
            )

            logger.info(
                "[PRICE VALIDATOR] Auto-fix: Zmieniono options_price z '%s' na '%s' "
                "aby zachować matematyczną spójność.",
                original_options,
                card_summary["options_price"],
            )

            # Update report so the summary reflects the fix
            report.warnings.remove(sum_warning)
            report.is_valid = not any(w.severity == "ERROR" for w in report.warnings)
            report.parsed_options = corrected_options_val

            # Add an INFO note about the fix
            report.add(
                ValidationWarning(
                    rule="AUTO_FIX_APPLIED",
                    message=f"Automatycznie wyliczono brakujące options_price jako {int(corrected_options_val)} aby zbilansować sumę.",
                    severity="INFO",
                )
            )
        elif (
            report.parsed_base > report.parsed_total
            and report.parsed_options is not None
        ):
            # AI extracted the discounted final price as total_price
            corrected_total_val = report.parsed_base + report.parsed_options

            original_total = str(card_summary.get("total_price", ""))

            # Determine currency and suffix from base_price
            base_str = str(card_summary.get("base_price", ""))
            domain_suffix = ""
            if "netto" in base_str.lower():
                domain_suffix = " netto"
            elif "brutto" in base_str.lower():
                domain_suffix = " brutto"

            currency = " PLN" if "PLN" in base_str.upper() else ""

            # Update card_summary
            card_summary["total_price"] = (
                f"{int(corrected_total_val)}{currency}{domain_suffix}".strip()
            )

            logger.info(
                "[PRICE VALIDATOR] Auto-fix: Nadpisano total_price z '%s' na '%s' "
                "poniewaz oryginalny total_price zawieral kwote zrabatowana.",
                original_total,
                card_summary["total_price"],
            )

            # Update report so the summary reflects the fix
            report.warnings.remove(sum_warning)
            report.is_valid = not any(w.severity == "ERROR" for w in report.warnings)
            report.parsed_total = corrected_total_val

            # Add an INFO note about the fix
            report.add(
                ValidationWarning(
                    rule="AUTO_FIX_APPLIED",
                    message=f"Automatycznie nadpisano total_price (zrabatowana kwota) na sume bazy i opcji: {int(corrected_total_val)}.",
                    severity="INFO",
                )
            )


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

    if diff_pct <= _SUM_TOLERANCE_PCT:
        return

    # Check if this is a netto/brutto mismatch (base + options was Netto, total was Brutto)
    expected_total_brutto = expected_total * _VAT_RATE
    diff_brutto = abs(expected_total_brutto - total.value)
    if (
        expected_total_brutto > 0
        and (diff_brutto / expected_total_brutto) * 100 <= _SUM_TOLERANCE_PCT
    ):
        report.add(
            ValidationWarning(
                rule="SUM_CONSISTENCY_NETTO_BRUTTO_MISMATCH",
                message=(
                    f"Suma (baza {base.value:.0f} + opcje {options_val:.0f}) * {_VAT_RATE} ≈ "
                    f"{expected_total_brutto:.0f}, co odpowiada total = {total.value:.0f}. "
                    "Wykryto pomieszanie kwot netto i brutto."
                ),
                severity="WARNING",
                expected=expected_total_brutto,
                actual=total.value,
            )
        )
        return

    # Check if base + options was Brutto, total was Netto
    expected_total_netto = expected_total / _VAT_RATE
    diff_netto = abs(expected_total_netto - total.value)
    if (
        expected_total_netto > 0
        and (diff_netto / expected_total_netto) * 100 <= _SUM_TOLERANCE_PCT
    ):
        report.add(
            ValidationWarning(
                rule="SUM_CONSISTENCY_BRUTTO_NETTO_MISMATCH",
                message=(
                    f"Suma (baza {base.value:.0f} + opcje {options_val:.0f}) / {_VAT_RATE} ≈ "
                    f"{expected_total_netto:.0f}, co odpowiada total = {total.value:.0f}. "
                    "Wykryto pomieszanie kwot netto i brutto."
                ),
                severity="WARNING",
                expected=expected_total_netto,
                actual=total.value,
            )
        )
        return

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
            
        category = opt.get("category", "").lower()
        if "serwis" in category or "akcesor" in category or "dealer" in category:
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


def _check_power_consistency(
    report: ValidationReport,
    card_summary: dict[str, Any],
) -> None:
    """Validate mathematically if power_kw * 1.36 == power_hp."""
    power_kw = card_summary.get("power_kw")
    power_hp = card_summary.get("power_hp")

    if not isinstance(power_kw, (int, float)) or not isinstance(power_hp, (int, float)):
        return

    if power_kw <= 0 or power_hp <= 0:
        return

    expected_hp = round(power_kw * 1.36)
    diff = abs(expected_hp - power_hp)

    # Allow a small tolerance for rounding differences (e.g., 2 HP)
    if diff > 2:
        report.add(
            ValidationWarning(
                rule="POWER_KW_HP_MISMATCH",
                message=(
                    f"Moc niespójna: {power_kw} kW * 1.36 ≈ {expected_hp} KM, "
                    f"ale wyodrębniono {power_hp} KM"
                ),
                severity="WARNING",
                expected=expected_hp,
                actual=float(power_hp),
            )
        )
