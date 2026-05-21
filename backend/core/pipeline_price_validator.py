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
    field_path: str | None = None  # dot-path do pola (np. "paid_options.3.price", "base_price")

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
        if self.field_path is not None:
            result["field_path"] = self.field_path
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

    # ── Rule 9: Discount triangulation (DiscountBreakdown) ──
    _check_discount_consistency(report, card_summary)

    # ── Rule 10: Detect dealer extras leaking into discountable options ──
    _detect_dealer_extras(report, card_summary)

    # ── Rule 11: Sanity range on computed discount % ──
    _check_discount_pct_sanity(report, card_summary)

    # ── Rule 12: NET/GROSS ratio sanity per item (paid_options + service_equipment) ──
    _check_net_gross_ratio_per_item(report, card_summary)

    # ── Rule 13: service_equipment.total ≈ sum(components) ──
    _check_service_equipment_sum_integrity(report, card_summary)

    # ── Rule 14: total = base + Σ(paid_options) + service_equipment.total ──
    _check_full_sum_integrity(report, card_summary)

    _log_report(report)
    return report


def _promote_prices_from_digital_twin(pro_data: dict[str, Any]) -> None:
    """Fill card_summary.{base,total,options}_price from digital_twin.pricing when missing.

    Why: Audi configurator PDFs print prices without a netto/brutto suffix.
    CARD_SUMMARY_PROMPT then refuses to extract them (refuses ambiguous domain),
    leaving card_summary.base_price=None. The digital twin extractor is more
    lenient and still catches the raw strings in digital_twin.pricing.
    Polish premium catalogues without explicit suffix default to BRUTTO — same
    convention the existing PRICE_DOMAIN_UNKNOWN warning already announces.
    """
    card_summary = pro_data.get("card_summary")
    if not isinstance(card_summary, dict):
        return

    dt_pricing = (pro_data.get("digital_twin") or {}).get("pricing") or {}
    if not isinstance(dt_pricing, dict):
        return

    label = pro_data.get("offer_number") or pro_data.get("model") or "?"
    for field_name in ("base_price", "total_price", "options_price"):
        if card_summary.get(field_name):
            continue
        dt_val = dt_pricing.get(field_name)
        if not isinstance(dt_val, str) or not dt_val.strip():
            continue

        dt_str = dt_val.strip()
        has_domain = "netto" in dt_str.lower() or "brutto" in dt_str.lower()
        promoted = dt_str if has_domain else f"{dt_str} brutto"
        card_summary[field_name] = promoted
        logger.info(
            "[PRICE PROMOTE] %s: card_summary.%s pusty, skopiowano z digital_twin.pricing → %r",
            label, field_name, promoted,
        )


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

    # Promote prices from digital_twin BEFORE validation — fills the gap when
    # CARD_SUMMARY_PROMPT skipped them due to missing netto/brutto suffix.
    _promote_prices_from_digital_twin(pro_data)

    # Allow empty dict to still get _validation flags
    report = validate_card_summary_prices(card_summary)

    # V3 rules — only fire when card_summary has the V3 numeric/dedup fields
    # populated (i.e. came from pipeline_normalization or HITL fixup). On
    # legacy records they're no-ops because all checks bail on missing data.
    try:
        from core.pipeline_validator_v3 import run_v3_rules
        run_v3_rules(card_summary, report)
    except Exception as e:  # pragma: no cover — defensive
        logger.warning("V3 rules failed: %s", e)

    # Detect domain BEFORE self-healing — derived base_price needs the
    # netto/brutto suffix to be formatted correctly, and the self-heal
    # guard for derived base requires a known domain.
    detected_domain = detect_and_normalize_price_domain(card_summary)
    card_summary["_price_domain"] = detected_domain

    # Apply self-healing rules if mathematically inconsistent
    _apply_self_healing(card_summary, report)

    # Generate NL summary (Gemini Flash + deterministic fallback)
    validation_dict = report.to_dict()
    report.summary = generate_price_summary(validation_dict, card_summary)

    card_summary["_validation"] = report.to_dict()

    # ── Boost confidence_breakdown / paid_options.confidence based on warnings ──
    _apply_validator_penalties(card_summary, report)

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


_DERIVED_BASE_MIN_RATIO_OF_TOTAL = 0.30


def _apply_self_healing(card_summary: dict[str, Any], report: ValidationReport) -> None:
    """Attempt to auto-fix certain mathematical errors in card_summary before generation of summary."""
    # Branch 0: derive missing base_price from total − options when LLM
    # couldn't find it directly (e.g. Audi catalogs print only final price
    # + options breakdown). Symmetric to the options-derivation branch below.
    if (
        report.parsed_base is None
        and report.parsed_total is not None
        and report.parsed_options is not None
    ):
        _try_derive_base_price(card_summary, report)

    sum_warning = next(
        (w for w in report.warnings if w.rule == "BASE_PLUS_OPTIONS_VS_TOTAL"), None
    )

    if sum_warning and report.parsed_base and report.parsed_total:
        if report.parsed_base < report.parsed_total:
            # We trust base and total more than options string.
            #
            # Pełne równanie z uwzględnieniem rabatu i zabudowy:
            #   total = base + options_fabryczne + non_discountable - rabat
            # Stąd:
            #   options_fabryczne = total + rabat - non_discountable - base
            #
            # Gdy discount nie istnieje, równanie redukuje się do
            # options = total - base (zachowanie historyczne).
            discount = card_summary.get("discount") or {}
            rabat = 0.0
            non_disc = 0.0
            if isinstance(discount, dict):
                try:
                    rabat = float(discount.get("explicit_rabat_pln") or 0)
                except (TypeError, ValueError):
                    rabat = 0.0
                try:
                    non_disc = float(
                        discount.get("non_discountable_total_net") or 0
                    )
                except (TypeError, ValueError):
                    non_disc = 0.0

            # Per memory `extractor_price_quirks` (Renault Master 2026-05-19):
            # service_equipment.total też redukuje pulę opcji. AI zwraca często
            # "cenę pojazdu" w total bez zabudowy/agregatu, ale czasem WŁĄCZA
            # service_equipment w total — różnica decyduje czy AUTO_FIX dziala
            # czy musi się wstrzymać.
            domain = card_summary.get("_price_domain", "unknown")
            service_total = (
                _service_equipment_total_in_domain(card_summary, domain)
                if domain in ("netto", "brutto")
                else 0.0
            )

            corrected_options_val = (
                report.parsed_total
                + rabat
                - non_disc
                - service_total
                - report.parsed_base
            )

            # Jeśli korekta dałaby ujemną kwotę opcji → niespójność danych:
            # zostawiamy `BASE_PLUS_OPTIONS_VS_TOTAL` jako warning i pozwalamy
            # FULL_SUM_INTEGRITY (Rule 14) skierować pojazd do HITL.
            if corrected_options_val < 0:
                return

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
            fix_msg = (
                f"Automatycznie wyliczono options_price jako "
                f"{int(corrected_options_val)} (= total + rabat − zabudowa − base)."
            )
            if rabat > 0 or non_disc > 0:
                fix_msg += (
                    f" Użyto rabatu={int(rabat)} i non_discountable={int(non_disc)}."
                )
            report.add(
                ValidationWarning(
                    rule="AUTO_FIX_APPLIED",
                    message=fix_msg,
                    severity="INFO",
                )
            )
        elif (
            report.parsed_base > report.parsed_total
            and report.parsed_options is not None
        ):
            # AI extracted the discounted final price as total_price
            discount = (
                report.parsed_base + report.parsed_options
            ) - report.parsed_total

            logger.info(
                "[PRICE VALIDATOR] Auto-fix: Wykryto zrabatowaną cenę całkowitą (discount). "
                "Base+Options=%.0f, Total=%.0f, Rabat=%.0f",
                report.parsed_base + report.parsed_options,
                report.parsed_total,
                discount,
            )

            # Update report so the summary reflects the fix
            report.warnings.remove(sum_warning)
            report.is_valid = not any(w.severity == "ERROR" for w in report.warnings)

            # Add an INFO note about the fix
            report.add(
                ValidationWarning(
                    rule="DISCOUNT_DETECTED",
                    message=f"Cena całkowita uwzględnia rabat w wysokości ok. {int(discount)} PLN.",
                    severity="INFO",
                )
            )


def _try_derive_base_price(
    card_summary: dict[str, Any], report: ValidationReport
) -> None:
    """Derive missing base_price from total − options when guards pass.

    Mirror of the options-derivation logic in _apply_self_healing. Used when
    LLM couldn't find an explicit base_price in the document (e.g. Audi
    catalogs that print only final price + options breakdown).

    Equation: total = base + options + non_discountable − rabat
              ⇒ base = total + rabat − non_discountable − options
    """
    # G1: options sum must be consistent (paid_options ≈ declared options_price).
    # Without this, deriving base would replicate the very error the prompt warns
    # about: a missed option would inflate the derived base.
    if any(w.rule == "OPTIONS_SUM_MISMATCH" for w in report.warnings):
        return

    # G2: price domain must be known (netto vs brutto) to format the derived
    # value correctly and to avoid mixing-domain arithmetic.
    domain = card_summary.get("_price_domain", "unknown")
    if domain == "unknown":
        return

    # Defensive — caller already checked these are non-None.
    if report.parsed_total is None or report.parsed_options is None:
        return

    # Read discount components — same pattern as options-derivation branch.
    discount = card_summary.get("discount") or {}
    rabat = 0.0
    non_disc = 0.0
    if isinstance(discount, dict):
        try:
            rabat = float(discount.get("explicit_rabat_pln") or 0)
        except (TypeError, ValueError):
            rabat = 0.0
        try:
            non_disc = float(discount.get("non_discountable_total_net") or 0)
        except (TypeError, ValueError):
            non_disc = 0.0

    # Per memory `extractor_price_quirks` (Renault Master 2026-05-19):
    # service_equipment.total też redukuje pulę bazy, jeśli total_price ją obejmuje.
    service_total = _service_equipment_total_in_domain(card_summary, domain)

    derived_base = (
        report.parsed_total
        + rabat
        - non_disc
        - service_total
        - report.parsed_options
    )

    # G3 & G4: sanity range. Negative or implausibly small derived base means
    # the inputs are inconsistent — leaving base as "Brak" is safer than
    # writing a misleading value.
    min_allowed = _DERIVED_BASE_MIN_RATIO_OF_TOTAL * report.parsed_total
    if derived_base <= 0 or derived_base < min_allowed:
        report.add(
            ValidationWarning(
                rule="BASE_DERIVATION_OUT_OF_RANGE",
                message=(
                    f"Próba wyliczenia ceny bazowej dała wartość poza rozsądnym "
                    f"zakresem: {derived_base:.0f} (total={report.parsed_total:.0f}, "
                    f"options={report.parsed_options:.0f}, rabat={rabat:.0f}, "
                    f"non_disc={non_disc:.0f}). Pozostawiono bazę jako 'Brak'."
                ),
                severity="ERROR",
                actual=derived_base,
            )
        )
        return

    # Format derived value to match existing string convention used elsewhere
    # in this module (see options self-heal, lines ~250-266).
    total_str = str(card_summary.get("total_price", ""))
    domain_suffix = ""
    if "netto" in total_str.lower():
        domain_suffix = " netto"
    elif "brutto" in total_str.lower():
        domain_suffix = " brutto"
    else:
        domain_suffix = f" {domain}"

    currency = " PLN" if "PLN" in total_str.upper() else ""
    if not currency:
        options_str = str(card_summary.get("options_price", ""))
        if "PLN" in options_str.upper():
            currency = " PLN"

    original_base = str(card_summary.get("base_price", ""))
    card_summary["base_price"] = (
        f"{int(derived_base)}{currency}{domain_suffix}".strip()
    )
    card_summary["_base_derived"] = True

    # Critical: update report so the gate in phase_2_mapping.py
    # (`parsed_prices.get("base") is not None`) lets the row through to
    # feature enrichment instead of stalling in 'needs_review'.
    report.parsed_base = derived_base

    logger.info(
        "[PRICE VALIDATOR] Auto-derive: Wyliczono base_price '%s' z total − options "
        "(rabat=%.0f, non_disc=%.0f). Oryginał: '%s'",
        card_summary["base_price"],
        rabat,
        non_disc,
        original_base,
    )

    derive_msg = (
        f"Cena bazowa nie była podana literalnie w dokumencie. "
        f"Wyliczono jako total + rabat − non_discountable − options "
        f"= {int(derived_base)}. Zweryfikuj manualnie."
    )
    if rabat > 0 or non_disc > 0:
        derive_msg += (
            f" Użyto rabatu={int(rabat)} i non_discountable={int(non_disc)}."
        )

    report.add(
        ValidationWarning(
            rule="BASE_AUTO_DERIVED",
            message=derive_msg,
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
            field_path="total_price",
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
                field_path="total_price",
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
                    field_path="base_price",
                )
            )
            return

    # If swapping them doesn't fix the sum, base > total is likely just a result of a discount.
    # We shouldn't flag it as a swapped field unless swapping actually works mathematically.


def _check_unparseable_options(
    report: ValidationReport,
    paid_options: list[Any],
) -> None:
    """Flag paid_options with missing or unparseable prices.

    These require manual verification. Emits one warning per unparseable option
    with field_path pointing to that option's price slot.
    """
    if not paid_options:
        return

    for idx, opt in enumerate(paid_options):
        if not isinstance(opt, dict):
            continue
        price_str = opt.get("price", "")
        name = opt.get("name", "<brak nazwy>")
        parsed = parse_price_string(price_str)
        if parsed is None:
            report.add(
                ValidationWarning(
                    rule="OPTION_PRICE_UNPARSEABLE",
                    message=(
                        f"Opcja '{name}' (idx {idx}) ma nieparsowalną cenę "
                        f"'{price_str}' — wymaga weryfikacji."
                    ),
                    severity="WARNING",
                    field_path=f"paid_options.{idx}.price",
                )
            )


_DEALER_EXTRA_KEYWORDS = (
    "zabudowa",
    "kontener",
    "izoterm",
    "wywrotka",
    "plandeka",
    "skrzynia ładunkow",
    "skrzynia ladunkow",
    "chłodnia",
    "chlodnia",
    "winda",
    " hds",
    "modyfikacj",
    "akcesoria dealer",
    "wyposażenie dealer",
    "wyposazenie dealer",
    "foliowanie",
    "hak dealer",
)

_DISCOUNT_TRIANGULATION_TOLERANCE_PLN = 1.0
_DISCOUNT_PCT_MIN_SANE = 0.5
_DISCOUNT_PCT_MAX_SANE = 60.0


def _check_discount_consistency(
    report: ValidationReport,
    card_summary: dict[str, Any],
) -> None:
    """Rule 9 — triangulacja DiscountBreakdown.

    Sprawdza czy: discountable_base + non_discountable - explicit_rabat ≈ total
    Zatrzymuje błąd '7% zamiast 29%' przy ofertach z zabudową dealera.
    """
    discount = card_summary.get("discount")
    if not isinstance(discount, dict):
        return

    explicit_pln = discount.get("explicit_rabat_pln")
    discountable_base = discount.get("discountable_base_net")
    non_discountable = discount.get("non_discountable_total_net") or 0.0

    base = parse_price_string(card_summary.get("base_price"))
    total = parse_price_string(card_summary.get("total_price"))

    if explicit_pln is None or total is None:
        return

    base_for_check = discountable_base if discountable_base else (base.value if base else None)
    if base_for_check is None:
        return

    expected_total = base_for_check - explicit_pln + non_discountable
    diff = abs(expected_total - total.value)

    if diff > _DISCOUNT_TRIANGULATION_TOLERANCE_PLN:
        diff_pct = (diff / total.value) * 100 if total.value else 0
        severity = "ERROR" if diff_pct > 5 else "WARNING"
        report.add(
            ValidationWarning(
                rule="DISCOUNT_TRIANGULATION_FAILED",
                message=(
                    f"Rabat {explicit_pln:.0f} PLN nie pasuje do arytmetyki: "
                    f"discountable({base_for_check:.0f}) - rabat({explicit_pln:.0f}) "
                    f"+ non_discountable({non_discountable:.0f}) = {expected_total:.0f}, "
                    f"ale total = {total.value:.0f} (Δ {diff_pct:.1f}%). "
                    "Sprawdź czy zabudowa/dealer extras nie zostały pominięte w non_discountable."
                ),
                severity=severity,
                expected=expected_total,
                actual=total.value,
                diff_pct=diff_pct,
            )
        )


def _detect_dealer_extras(
    report: ValidationReport,
    card_summary: dict[str, Any],
) -> None:
    """Rule 10 — wykryj zabudowy/dealer extras w paid_options.

    Te pozycje powinny mieć `no_discount=true` w warstwie kalkulatora,
    a w `discount.non_discountable_total_net` ich suma powinna się zgadzać.
    """
    paid_options = card_summary.get("paid_options", [])
    if not paid_options:
        return

    suspect: list[tuple[int, str, float]] = []
    for idx, opt in enumerate(paid_options):
        if not isinstance(opt, dict):
            continue
        name = (opt.get("name") or "").lower()
        category = (opt.get("category") or "").lower()
        haystack = f"{name} {category}"
        if any(kw in haystack for kw in _DEALER_EXTRA_KEYWORDS):
            parsed = parse_price_string(opt.get("price", ""))
            price_val = parsed.value if parsed else 0.0
            suspect.append((idx, opt.get("name", "?"), price_val))

    if not suspect:
        return

    suspect_sum = sum(p for _, _, p in suspect)
    suspect_names = ", ".join(name for _, name, _ in suspect)
    suspect_paths = ",".join(f"paid_options.{idx}" for idx, _, _ in suspect)

    discount = card_summary.get("discount")
    declared_non_discountable = (
        discount.get("non_discountable_total_net") if isinstance(discount, dict) else None
    ) or 0.0

    diff = abs(suspect_sum - declared_non_discountable)
    if diff > 1.0:
        report.add(
            ValidationWarning(
                rule="DEALER_EXTRA_NOT_IN_NON_DISCOUNTABLE",
                message=(
                    f"Wykryto pozycje typu zabudowa/dealer w paid_options: "
                    f"{suspect_names} (Σ ≈ {suspect_sum:.0f} PLN), ale "
                    f"non_discountable_total_net = {declared_non_discountable:.0f}. "
                    "Te pozycje powinny zostać oznaczone `no_discount=true` "
                    "i wliczone do non_discountable, inaczej rabat zostanie "
                    "błędnie zastosowany do podstawy zawierającej zabudowę."
                ),
                severity="WARNING",
                expected=suspect_sum,
                actual=declared_non_discountable,
                field_path=suspect_paths,
            )
        )
    else:
        report.add(
            ValidationWarning(
                rule="DEALER_EXTRA_DETECTED",
                message=(
                    f"Wykryto i prawidłowo zaklasyfikowano dealer extras: "
                    f"{suspect_names} (Σ {suspect_sum:.0f} PLN)."
                ),
                severity="INFO",
                field_path=suspect_paths,
            )
        )


def _check_discount_pct_sanity(
    report: ValidationReport,
    card_summary: dict[str, Any],
) -> None:
    """Rule 11 — zakres normalny wyliczonego rabatu.

    Bardzo niski (<0.5%) sugeruje że LLM zlekceważył non_discountable.
    Bardzo wysoki (>60%) to prawdopodobnie błąd ekstrakcji.
    """
    discount = card_summary.get("discount")
    if not isinstance(discount, dict):
        return

    pct = discount.get("computed_pct")
    if pct is None:
        return

    method = discount.get("extraction_method")

    if pct < _DISCOUNT_PCT_MIN_SANE:
        report.add(
            ValidationWarning(
                rule="DISCOUNT_PCT_SUSPICIOUSLY_LOW",
                message=(
                    f"Rabat {pct:.2f}% jest podejrzanie niski. "
                    "Najczęstsza przyczyna: zabudowa lub akcesoria dealera "
                    "zostały błędnie wliczone do discountable_base_net "
                    "(zamiast do non_discountable)."
                ),
                severity="WARNING",
                actual=pct,
            )
        )
        return

    if pct > _DISCOUNT_PCT_MAX_SANE:
        report.add(
            ValidationWarning(
                rule="DISCOUNT_PCT_SUSPICIOUSLY_HIGH",
                message=(
                    f"Rabat {pct:.2f}% przekracza {_DISCOUNT_PCT_MAX_SANE:.0f}% — "
                    "prawdopodobny błąd ekstrakcji lub niepełna podstawa."
                ),
                severity="ERROR",
                actual=pct,
            )
        )
        return

    if method == "computed_from_total":
        report.add(
            ValidationWarning(
                rule="DISCOUNT_COMPUTED_INDIRECTLY",
                message=(
                    f"Rabat {pct:.2f}% wyliczony pośrednio (brak literalnej linii "
                    "RABAT w dokumencie). Zweryfikuj manualnie."
                ),
                severity="INFO",
                actual=pct,
            )
        )


def _check_net_gross_ratio_per_item(
    report: ValidationReport,
    card_summary: dict[str, Any],
) -> None:
    """Sprawdza czy stosunek price_gross/price_net dla każdej pozycji
    z osobnymi polami netto i brutto mieści się w realnym zakresie VAT
    (~1.23 ± tolerancja). Pozycje poza zakresem są flagowane.

    Łapie:
    - AI dała te same kwoty do net i gross (ratio = 1.0)
    - AI dała losowe wartości bez relacji VAT (ratio np. 1.5)
    - Pomyłki konwersji (gross = net * 1.08 dla niepoprawnej stawki)

    NIE łapie przypadku, gdy AI poprawnie pomnożyła kwotę przez 1.23,
    ale OBIE wartości są w złej domenie (np. wzięła brutto z dokumentu jako
    netto i dorobiła "brutto" jako 1.23×brutto).
    """
    _MIN_RATIO = 1.20
    _MAX_RATIO = 1.26

    def _check_pair(name: str, net_raw: Any, gross_raw: Any, path: str) -> None:
        net = parse_price_string(str(net_raw) if net_raw else None)
        gross = parse_price_string(str(gross_raw) if gross_raw else None)
        if net is None or gross is None:
            return
        if net.value <= 0 or gross.value <= 0:
            return
        ratio = gross.value / net.value
        if _MIN_RATIO <= ratio <= _MAX_RATIO:
            return
        report.add(
            ValidationWarning(
                rule="NET_GROSS_RATIO_INVALID",
                message=(
                    f"'{name}' ma podejrzany stosunek brutto/netto = {ratio:.3f} "
                    f"(oczekiwane ≈1.23). path={path}, net={net.value:.2f}, "
                    f"gross={gross.value:.2f}"
                ),
                severity="WARNING",
                expected=round(net.value * 1.23, 2),
                actual=gross.value,
                diff_pct=abs(ratio - 1.23) * 100,
            )
        )

    # service_equipment.components[*] + service_equipment.total_*
    service_eq = card_summary.get("service_equipment")
    if isinstance(service_eq, dict):
        for idx, comp in enumerate(service_eq.get("components") or []):
            if not isinstance(comp, dict):
                continue
            _check_pair(
                comp.get("name", f"component[{idx}]"),
                comp.get("price_net"),
                comp.get("price_gross"),
                f"service_equipment.components[{idx}]",
            )
        _check_pair(
            service_eq.get("name", "service_equipment"),
            service_eq.get("total_price_net"),
            service_eq.get("total_price_gross"),
            "service_equipment.total",
        )


def _check_service_equipment_sum_integrity(
    report: ValidationReport,
    card_summary: dict[str, Any],
) -> None:
    """Sprawdza czy sum(components.price_net) ≈ service_equipment.total_price_net
    oraz analogicznie dla brutto. Tolerancja: ±1 PLN.

    Łapie przypadki gdzie AI zapisała komponenty z innymi kwotami niż
    aggregowany total (literówki / niespójność wewnętrzna ekstrakcji).
    """
    service_eq = card_summary.get("service_equipment")
    if not isinstance(service_eq, dict):
        return
    components = service_eq.get("components")
    if not isinstance(components, list) or not components:
        return

    def _sum_field(key: str) -> float | None:
        total = 0.0
        seen = False
        for comp in components:
            if not isinstance(comp, dict):
                continue
            parsed = parse_price_string(str(comp.get(key)) if comp.get(key) else None)
            if parsed is None:
                continue
            total += parsed.value
            seen = True
        return total if seen else None

    for field_total, field_comp, label in (
        ("total_price_net", "price_net", "netto"),
        ("total_price_gross", "price_gross", "brutto"),
    ):
        declared = parse_price_string(
            str(service_eq.get(field_total)) if service_eq.get(field_total) else None
        )
        components_sum = _sum_field(field_comp)
        if declared is None or components_sum is None or declared.value <= 0:
            continue
        diff = abs(components_sum - declared.value)
        if diff <= 1.0:
            continue
        diff_pct = (diff / declared.value) * 100
        report.add(
            ValidationWarning(
                rule="SERVICE_EQUIPMENT_SUM_MISMATCH",
                message=(
                    f"Σ(components.{field_comp}) = {components_sum:.2f}, "
                    f"ale service_equipment.{field_total} = {declared.value:.2f} "
                    f"(Δ {diff:.2f} PLN / {diff_pct:.2f}%, domena: {label})"
                ),
                severity="WARNING",
                expected=declared.value,
                actual=components_sum,
                diff_pct=diff_pct,
                field_path=f"service_equipment.{field_total}",
            )
        )


def _service_equipment_total_in_domain(
    card_summary: dict[str, Any], domain: str
) -> float:
    """Zwraca service_equipment.total_price_(net|gross) sparsowane w żądanej domenie.

    Preferuje pole zgodne z domeną; jeśli puste, parsuje drugie i konwertuje VAT-em.
    Jeśli `service_equipment.total_*` nie jest podane ale `components` istnieją,
    sumuje komponenty. Zwraca 0.0 gdy nic nie ma.
    """
    se = card_summary.get("service_equipment")
    if not isinstance(se, dict):
        return 0.0

    preferred = "total_price_net" if domain == "netto" else "total_price_gross"
    fallback = "total_price_gross" if domain == "netto" else "total_price_net"

    parsed = parse_price_string(str(se.get(preferred)) if se.get(preferred) else None)
    if parsed and parsed.value > 0:
        return parsed.value

    parsed_alt = parse_price_string(str(se.get(fallback)) if se.get(fallback) else None)
    if parsed_alt and parsed_alt.value > 0:
        return parsed_alt.value_net if domain == "netto" else parsed_alt.value_gross

    # Fallback: sum components in matching domain
    comp_field = "price_net" if domain == "netto" else "price_gross"
    comp_total = 0.0
    seen = False
    for comp in se.get("components", []) or []:
        if not isinstance(comp, dict):
            continue
        p = parse_price_string(str(comp.get(comp_field)) if comp.get(comp_field) else None)
        if p:
            comp_total += p.value
            seen = True
    return comp_total if seen else 0.0


def _paid_options_total_in_domain(
    card_summary: dict[str, Any], domain: str
) -> float:
    """Suma `paid_options[].price` sparsowana zgodnie z domeną.

    Dla każdej opcji: jeśli string ma jawny sufiks netto/brutto inny niż domain,
    konwertuje przez VAT. Inaczej zakłada domain ze stringa.
    """
    total = 0.0
    for opt in card_summary.get("paid_options", []) or []:
        if not isinstance(opt, dict):
            continue
        category = (opt.get("category") or "").lower()
        if "serwis" in category or "akcesor" in category:
            # Service / accessory items are captured in service_equipment instead
            # to avoid double-counting (memory: extractor_price_quirks 2026-05-06).
            continue
        parsed = parse_price_string(opt.get("price", ""))
        if parsed is None:
            continue
        if parsed.tax_type == domain or parsed.tax_type == "unknown":
            total += parsed.value
        elif domain == "netto":
            total += parsed.value_net
        else:
            total += parsed.value_gross
    return total


def _check_full_sum_integrity(
    report: ValidationReport,
    card_summary: dict[str, Any],
) -> None:
    """Rule 14 — pełna spójność: total = base + Σ(paid_options) + service_equipment.total.

    Łapie case gdy Gemini zwróci `total_price` jako "cenę pojazdu" pomijając
    usługi serwisowe (zabudowa, agregat), a sumę całej oferty trzeba dopiero
    poskładać z pól field-by-field. Bez tej reguły AUTO_FIX `BASE_PLUS_OPTIONS_VS_TOTAL`
    rekonstruuje fałszywe `options_price` dopasowane do niepełnego total
    (memory: extractor_price_quirks — Renault Master 2026-05-19).

    Sprawdzenie po stronie domeny ustalonej przez `_price_domain` — jeśli
    domena nie jest znana, reguła pasywna (inne reguły flagują domenę osobno).
    """
    if report.parsed_base is None or report.parsed_total is None:
        return

    # Reguła odpalana wewnątrz `validate_card_summary_prices`, gdzie
    # `card_summary["_price_domain"]` jest jeszcze NIE ustawione
    # (wypełniane dopiero przez `validate_and_flag_prices` po walidacji).
    # Inferujemy lokalnie z tax_type na base/total, żeby reguła działała
    # niezależnie od orkiestracji.
    domain = card_summary.get("_price_domain", "unknown")
    if domain not in ("netto", "brutto"):
        base_parsed = parse_price_string(card_summary.get("base_price"))
        total_parsed = parse_price_string(card_summary.get("total_price"))
        for p in (base_parsed, total_parsed):
            if p and p.tax_type in ("netto", "brutto"):
                domain = p.tax_type
                break
    if domain not in ("netto", "brutto"):
        return

    paid_sum = _paid_options_total_in_domain(card_summary, domain)
    service_sum = _service_equipment_total_in_domain(card_summary, domain)

    if service_sum <= 0 and paid_sum <= 0:
        # Nic do sprawdzenia — Rule 2 (BASE_PLUS_OPTIONS_VS_TOTAL) wystarczy
        return

    expected_total = report.parsed_base + paid_sum + service_sum
    diff = abs(expected_total - report.parsed_total)

    # 0.5% lub minimum 5 PLN tolerance (zaokrąglenia VAT przy paru pozycjach)
    tolerance = max(5.0, report.parsed_total * 0.005)
    if diff <= tolerance:
        return

    diff_pct = (diff / report.parsed_total * 100) if report.parsed_total else 0.0
    report.add(
        ValidationWarning(
            rule="FULL_SUM_INTEGRITY",
            message=(
                f"Niespójna suma końcowa ({domain}): "
                f"base({report.parsed_base:.0f}) + Σ(paid_options){paid_sum:.0f} "
                f"+ service_equipment({service_sum:.0f}) = {expected_total:.0f}, "
                f"ale total_price = {report.parsed_total:.0f} (Δ {diff:.0f} / {diff_pct:.1f}%). "
                "AI prawdopodobnie podało 'cenę pojazdu' a nie sumę całej oferty — "
                "weryfikacja ręczna wymagana."
            ),
            severity="ERROR",
            expected=expected_total,
            actual=report.parsed_total,
            diff_pct=diff_pct,
            field_path="total_price",
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
                field_path="power_hp",
            )
        )


# ── HITL confidence boost / penalty machinery ──

_SEVERITY_PENALTY = {"ERROR": 0.5, "WARNING": 0.2, "INFO": 0.05}

# Top-level fields w confidence_breakdown — bezpośrednie odwzorowanie field_path
_TOP_LEVEL_CONFIDENCE_KEYS = {
    "base_price",
    "options_price",
    "total_price",
    "body_style",
    "discount.rabat_pct",
    "engine_class",
    "samar_category",
    "trim_level",
    "power_hp",
    "power_kw",
    "service_equipment.total_price_net",
    "service_equipment.total_price_gross",
}


def _decrement_confidence(card_summary: dict[str, Any], field_path: str, penalty: float) -> None:
    """Obniż confidence pola wskazanego przez field_path o `penalty`.

    Obsługuje 3 kształty field_path:
    - "paid_options.<idx>" lub "paid_options.<idx>.<subfield>" → paid_options[idx].confidence
    - "service_equipment.components.<idx>" → service_equipment.components[idx].confidence
    - dowolne inne → confidence_breakdown[field_path]
    """
    if not field_path:
        return

    parts = field_path.split(".")
    if parts[0] == "paid_options" and len(parts) >= 2 and parts[1].isdigit():
        idx = int(parts[1])
        options = card_summary.get("paid_options", [])
        if 0 <= idx < len(options) and isinstance(options[idx], dict):
            current = options[idx].get("confidence", 1.0)
            options[idx]["confidence"] = max(0.0, current - penalty)
        return

    if (
        parts[0] == "service_equipment"
        and len(parts) >= 3
        and parts[1] == "components"
        and parts[2].isdigit()
    ):
        idx = int(parts[2])
        se = card_summary.get("service_equipment") or {}
        components = se.get("components", []) if isinstance(se, dict) else []
        if 0 <= idx < len(components) and isinstance(components[idx], dict):
            current = components[idx].get("confidence", 1.0)
            components[idx]["confidence"] = max(0.0, current - penalty)
        return

    # Top-level: zapisuj zarówno do confidence_breakdown jak i pełnego field_path
    # (zachowuje subfields jak "paid_options.3.price" dla diagnostyki UI)
    breakdown = card_summary.setdefault("confidence_breakdown", {})
    current = breakdown.get(field_path, 1.0)
    breakdown[field_path] = max(0.0, current - penalty)


def _apply_validator_penalties(card_summary: dict[str, Any], report: ValidationReport) -> None:
    """Po wygenerowaniu raportu walidatora, obniż confidence pól odpowiadających warningom.

    Każdy warning z `field_path` powoduje obniżkę:
    - ERROR: −0.5 od bieżącej wartości confidence
    - WARNING: −0.2
    - INFO: −0.05

    Pola tekstowe w `field_path` mogą być comma-separated (np. DEALER_EXTRA_DETECTED
    "paid_options.0,paid_options.3"). Każda ścieżka dostaje osobną obniżkę.
    """
    for warning in report.warnings:
        if not warning.field_path:
            continue
        penalty = _SEVERITY_PENALTY.get(warning.severity, 0.0)
        if penalty == 0.0:
            continue
        for path in warning.field_path.split(","):
            path = path.strip()
            if path:
                _decrement_confidence(card_summary, path, penalty)


# ── Confirmed-price reconciliation: soften discount-blind sum errors ──

_DISCOUNT_BLIND_RULES = {"BASE_PLUS_OPTIONS_VS_TOTAL", "FULL_SUM_INTEGRITY"}


def soften_discount_blind_warnings(card_summary: dict[str, Any]) -> bool:
    """Downgrade discount-blind sum ERRORs to INFO once a price is user-confirmed
    AND the discount triangulation closes.

    `BASE_PLUS_OPTIONS_VS_TOTAL` / `FULL_SUM_INTEGRITY` compare base + options
    (+ service) against the POST-discount total without subtracting the rabat,
    so a legitimately discounted, *confirmed* offer keeps showing red errors
    whose magnitude equals the discount. When the discount-aware triangulation
    (`discountable_base − rabat + non_discountable ≈ total`) holds, that gap is
    expected — soften those two rules to INFO so the offer reads as valid.

    Only the confirm path calls this; the validator's rules stay untouched
    (their parity tests still see ERROR severity at extraction time).

    Mutates ``card_summary['_validation']`` in place. Returns True if changed.
    """
    if not card_summary.get("_price_confirmed"):
        return False
    validation = card_summary.get("_validation")
    if not isinstance(validation, dict):
        return False

    discount = card_summary.get("discount") or {}
    try:
        rabat = float(discount.get("explicit_rabat_pln") or 0)
        disc_base = float(discount.get("discountable_base_net") or 0)
        non_disc = float(discount.get("non_discountable_total_net") or 0)
    except (TypeError, ValueError):
        return False
    if rabat <= 0:
        return False

    total = (validation.get("parsed_prices") or {}).get("total")
    if not isinstance(total, (int, float)) or total <= 0:
        return False

    expected_total = disc_base - rabat + non_disc
    if abs(expected_total - total) > max(1.0, total * 0.005):
        return False  # triangulation doesn't close → keep the errors

    changed = False
    for w in validation.get("warnings", []):
        if w.get("rule") in _DISCOUNT_BLIND_RULES and w.get("severity") == "ERROR":
            w["severity"] = "INFO"
            w["message"] = (
                f"{w.get('message', '')} — różnica odpowiada zatwierdzonemu "
                "rabatowi; obniżono do INFO po triangulacji."
            )
            changed = True

    if changed:
        validation["is_valid"] = not any(
            w.get("severity") == "ERROR" for w in validation.get("warnings", [])
        )
    return changed
