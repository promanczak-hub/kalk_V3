"""Unit tests for soften_discount_blind_warnings (confirm-path reconciliation).

Pure dict logic — no DB. Verifies that discount-blind sum ERRORs are downgraded
to INFO only when the price is confirmed AND the discount triangulation closes.
"""

from __future__ import annotations

from typing import Any

from core.pipeline_price_validator import soften_discount_blind_warnings


def _card(confirmed: bool = True, total: float = 204817.14) -> dict[str, Any]:
    """A confirmed Renault-Master-like card whose discount triangulation closes:
    discountable_base(169248) - rabat(49928.16) + non_disc(85497.3) = 204817.14.
    """
    return {
        "_price_confirmed": confirmed,
        "discount": {
            "explicit_rabat_pln": 49928.16,
            "discountable_base_net": 169248.0,
            "non_discountable_total_net": 85497.3,
        },
        "_validation": {
            "is_valid": False,
            "parsed_prices": {"base": 167218.5, "options": 2029.5, "total": total},
            "warnings": [
                {"rule": "BASE_PLUS_OPTIONS_VS_TOTAL", "severity": "ERROR", "message": "x"},
                {"rule": "FULL_SUM_INTEGRITY", "severity": "ERROR", "message": "y"},
                {"rule": "DISCOUNT_COMPUTED_INDIRECTLY", "severity": "INFO", "message": "z"},
            ],
        },
    }


def _severity(card: dict[str, Any], rule: str) -> str | None:
    for w in card["_validation"]["warnings"]:
        if w["rule"] == rule:
            return w["severity"]
    return None


def test_confirmed_and_triangulation_closes_downgrades_to_info() -> None:
    card = _card()
    changed = soften_discount_blind_warnings(card)
    assert changed is True
    assert _severity(card, "BASE_PLUS_OPTIONS_VS_TOTAL") == "INFO"
    assert _severity(card, "FULL_SUM_INTEGRITY") == "INFO"
    # No ERROR left → offer reads as valid.
    assert card["_validation"]["is_valid"] is True


def test_not_confirmed_is_noop() -> None:
    card = _card(confirmed=False)
    assert soften_discount_blind_warnings(card) is False
    assert _severity(card, "BASE_PLUS_OPTIONS_VS_TOTAL") == "ERROR"
    assert card["_validation"]["is_valid"] is False


def test_triangulation_does_not_close_keeps_errors() -> None:
    # total far from discountable_base - rabat + non_disc → gap is NOT the rabat.
    card = _card(total=150000.0)
    assert soften_discount_blind_warnings(card) is False
    assert _severity(card, "BASE_PLUS_OPTIONS_VS_TOTAL") == "ERROR"
    assert _severity(card, "FULL_SUM_INTEGRITY") == "ERROR"


def test_no_discount_is_noop() -> None:
    card = _card()
    card["discount"]["explicit_rabat_pln"] = 0
    assert soften_discount_blind_warnings(card) is False
    assert _severity(card, "FULL_SUM_INTEGRITY") == "ERROR"


def test_other_errors_keep_invalid() -> None:
    card = _card()
    card["_validation"]["warnings"].append(
        {"rule": "PRICE_TOO_LOW", "severity": "ERROR", "message": "still bad"}
    )
    changed = soften_discount_blind_warnings(card)
    assert changed is True
    # discount-blind rules softened…
    assert _severity(card, "BASE_PLUS_OPTIONS_VS_TOTAL") == "INFO"
    # …but an unrelated ERROR keeps the offer invalid.
    assert card["_validation"]["is_valid"] is False
