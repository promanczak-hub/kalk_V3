"""Tests for the Tender Engine — pure evaluation logic.

Tests cover:
- _evaluate_single_criterion (all operators, types, edge cases)
- _calculate_compliance_score (weighting, status determination)
- _extract_actual_value (type-based dispatch, fallback)

Does NOT require database (mocked in integration tests).
"""

from __future__ import annotations

import pytest

from backend.core.mdm_models import (
    ComplianceStatus,
    CriterionResult,
    TenderCriterion,
    VehicleComplianceStatus,
)
from backend.core.tender_engine import (
    _calculate_compliance_score,
    _evaluate_single_criterion,
    _extract_actual_value,
)


# ---------------------------------------------------------------------------
# _evaluate_single_criterion
# ---------------------------------------------------------------------------


class TestEvaluateSingleCriterion:
    """Unit tests for single criterion evaluation."""

    # ── Numeric comparisons ──

    def test_gte_pass(self) -> None:
        c = TenderCriterion(feature_key="hp", operator=">=", value=150, priority="MUST")
        assert _evaluate_single_criterion(c, 200) == ComplianceStatus.PASS

    def test_gte_exact(self) -> None:
        c = TenderCriterion(feature_key="hp", operator=">=", value=150, priority="MUST")
        assert _evaluate_single_criterion(c, 150) == ComplianceStatus.PASS

    def test_gte_fail(self) -> None:
        c = TenderCriterion(feature_key="hp", operator=">=", value=150, priority="MUST")
        assert _evaluate_single_criterion(c, 100) == ComplianceStatus.FAIL

    def test_lte_pass(self) -> None:
        c = TenderCriterion(
            feature_key="co2", operator="<=", value=120, priority="SHOULD"
        )
        assert _evaluate_single_criterion(c, 110) == ComplianceStatus.PASS

    def test_lte_fail(self) -> None:
        c = TenderCriterion(
            feature_key="co2", operator="<=", value=120, priority="SHOULD"
        )
        assert _evaluate_single_criterion(c, 130) == ComplianceStatus.FAIL

    def test_gt_pass(self) -> None:
        c = TenderCriterion(feature_key="seats", operator=">", value=5, priority="NICE")
        assert _evaluate_single_criterion(c, 7) == ComplianceStatus.PASS

    def test_gt_exact_fails(self) -> None:
        c = TenderCriterion(feature_key="seats", operator=">", value=5, priority="NICE")
        assert _evaluate_single_criterion(c, 5) == ComplianceStatus.FAIL

    def test_lt_pass(self) -> None:
        c = TenderCriterion(
            feature_key="price", operator="<", value=50000, priority="MUST"
        )
        assert _evaluate_single_criterion(c, 45000) == ComplianceStatus.PASS

    def test_eq_numeric(self) -> None:
        c = TenderCriterion(feature_key="doors", operator="=", value=4, priority="MUST")
        assert _evaluate_single_criterion(c, 4) == ComplianceStatus.PASS

    def test_neq_numeric(self) -> None:
        c = TenderCriterion(
            feature_key="doors", operator="!=", value=2, priority="NICE"
        )
        assert _evaluate_single_criterion(c, 4) == ComplianceStatus.PASS

    # ── Boolean / String comparisons ──

    def test_eq_bool_true(self) -> None:
        c = TenderCriterion(
            feature_key="abs", operator="=", value=True, priority="MUST"
        )
        assert _evaluate_single_criterion(c, True) == ComplianceStatus.PASS

    def test_eq_bool_false(self) -> None:
        c = TenderCriterion(
            feature_key="abs", operator="=", value=True, priority="MUST"
        )
        assert _evaluate_single_criterion(c, False) == ComplianceStatus.FAIL

    def test_eq_string(self) -> None:
        c = TenderCriterion(
            feature_key="fuel", operator="=", value="diesel", priority="MUST"
        )
        assert _evaluate_single_criterion(c, "DIESEL") == ComplianceStatus.PASS

    def test_neq_string(self) -> None:
        c = TenderCriterion(
            feature_key="fuel", operator="!=", value="diesel", priority="MUST"
        )
        assert _evaluate_single_criterion(c, "benzyna") == ComplianceStatus.PASS

    # ── IN operator ──

    def test_in_pass(self) -> None:
        c = TenderCriterion(
            feature_key="fuel",
            operator="IN",
            value=["diesel", "hybrid"],
            priority="MUST",
        )
        assert _evaluate_single_criterion(c, "Diesel") == ComplianceStatus.PASS

    def test_in_fail(self) -> None:
        c = TenderCriterion(
            feature_key="fuel",
            operator="IN",
            value=["diesel", "hybrid"],
            priority="MUST",
        )
        assert _evaluate_single_criterion(c, "benzyna") == ComplianceStatus.FAIL

    # ── Missing value ──

    def test_missing_value(self) -> None:
        c = TenderCriterion(feature_key="hp", operator=">=", value=150, priority="MUST")
        assert _evaluate_single_criterion(c, None) == ComplianceStatus.MISSING

    # ── Edge cases ──

    def test_zero_value(self) -> None:
        c = TenderCriterion(
            feature_key="emissions", operator="=", value=0, priority="MUST"
        )
        assert _evaluate_single_criterion(c, 0) == ComplianceStatus.PASS

    def test_negative_value(self) -> None:
        c = TenderCriterion(
            feature_key="temp", operator=">=", value=-10, priority="NICE"
        )
        assert _evaluate_single_criterion(c, -5) == ComplianceStatus.PASS

    def test_float_precision(self) -> None:
        c = TenderCriterion(
            feature_key="weight", operator="<=", value=2500.5, priority="MUST"
        )
        assert _evaluate_single_criterion(c, 2500.5) == ComplianceStatus.PASS

    def test_non_numeric_with_gt_operator_fails(self) -> None:
        """Attempting > on strings should FAIL, not crash."""
        c = TenderCriterion(
            feature_key="fuel", operator=">", value="diesel", priority="NICE"
        )
        assert _evaluate_single_criterion(c, "benzyna") == ComplianceStatus.FAIL


# ---------------------------------------------------------------------------
# _calculate_compliance_score
# ---------------------------------------------------------------------------


class TestCalculateComplianceScore:
    """Tests for weighted compliance score calculation."""

    def _make_result(self, status: ComplianceStatus) -> CriterionResult:
        return CriterionResult(
            feature_key="test",
            feature_name="Test",
            required_operator=">=",
            required_value="100",
            actual_value=None,
            status=status,
        )

    def test_all_must_pass(self) -> None:
        criteria = [
            TenderCriterion(feature_key="a", operator=">=", value=1, priority="MUST"),
            TenderCriterion(feature_key="b", operator=">=", value=1, priority="MUST"),
        ]
        results = [self._make_result(ComplianceStatus.PASS)] * 2
        score, status, must_p, must_f, should_p, nice_p = _calculate_compliance_score(
            results, criteria
        )
        assert status == VehicleComplianceStatus.MATCH
        assert score == 1.0
        assert must_p == 2
        assert must_f == 0

    def test_one_must_fail(self) -> None:
        criteria = [
            TenderCriterion(feature_key="a", operator=">=", value=1, priority="MUST"),
            TenderCriterion(feature_key="b", operator=">=", value=1, priority="MUST"),
        ]
        results = [
            self._make_result(ComplianceStatus.PASS),
            self._make_result(ComplianceStatus.FAIL),
        ]
        score, status, must_p, must_f, should_p, nice_p = _calculate_compliance_score(
            results, criteria
        )
        assert status == VehicleComplianceStatus.NOT_COMPLIANT
        assert must_f == 1
        assert score == 0.5  # 3/6

    def test_must_missing_gives_missing_data_status(self) -> None:
        criteria = [
            TenderCriterion(feature_key="a", operator=">=", value=1, priority="MUST"),
        ]
        results = [self._make_result(ComplianceStatus.MISSING)]
        _, status, _, must_f, _, _ = _calculate_compliance_score(results, criteria)
        assert status == VehicleComplianceStatus.MISSING_DATA
        assert must_f == 0  # MISSING != FAIL

    def test_weighted_scoring(self) -> None:
        """MUST=3, SHOULD=2, NICE=1. Total=6. Earned=3 (MUST pass)."""
        criteria = [
            TenderCriterion(feature_key="a", operator=">=", value=1, priority="MUST"),
            TenderCriterion(feature_key="b", operator=">=", value=1, priority="SHOULD"),
            TenderCriterion(feature_key="c", operator=">=", value=1, priority="NICE"),
        ]
        results = [
            self._make_result(ComplianceStatus.PASS),  # MUST: +3
            self._make_result(ComplianceStatus.FAIL),  # SHOULD: +0
            self._make_result(ComplianceStatus.FAIL),  # NICE: +0
        ]
        score, status, _, _, should_p, nice_p = _calculate_compliance_score(
            results, criteria
        )
        assert score == pytest.approx(3.0 / 6.0, rel=1e-6)
        assert status == VehicleComplianceStatus.MATCH  # All MUST passed
        assert should_p == 0
        assert nice_p == 0

    def test_empty_criteria_score_zero(self) -> None:
        score, status, _, _, _, _ = _calculate_compliance_score([], [])
        assert score == 0.0
        assert status == VehicleComplianceStatus.MATCH


# ---------------------------------------------------------------------------
# _extract_actual_value
# ---------------------------------------------------------------------------


class TestExtractActualValue:
    """Tests for type-based value extraction from spec rows."""

    def test_bool_type(self) -> None:
        row = {"value_bool": True, "value_numeric": None, "value_text": None}
        assert _extract_actual_value(row, "boolean") is True

    def test_numeric_type(self) -> None:
        row = {"value_bool": None, "value_numeric": 150, "value_text": None}
        assert _extract_actual_value(row, "numeric") == 150.0

    def test_int_type(self) -> None:
        row = {"value_bool": None, "value_numeric": 5, "value_text": None}
        assert _extract_actual_value(row, "int") == 5.0

    def test_float_type(self) -> None:
        row = {"value_bool": None, "value_numeric": 3.14, "value_text": None}
        assert _extract_actual_value(row, "float") == pytest.approx(3.14)

    def test_enum_type(self) -> None:
        row = {"value_bool": None, "value_numeric": None, "value_text": "diesel"}
        assert _extract_actual_value(row, "enum") == "diesel"

    def test_text_type(self) -> None:
        row = {"value_bool": None, "value_numeric": None, "value_text": "Automat"}
        assert _extract_actual_value(row, "text") == "Automat"

    def test_none_row(self) -> None:
        assert _extract_actual_value(None, "numeric") is None

    def test_fallback_to_available(self) -> None:
        """Unknown feature_type falls through to first non-None value."""
        row = {"value_bool": None, "value_numeric": None, "value_text": "fallback"}
        assert _extract_actual_value(row, "unknown_type") == "fallback"

    def test_numeric_none_returns_none(self) -> None:
        row = {"value_bool": None, "value_numeric": None, "value_text": None}
        assert _extract_actual_value(row, "numeric") is None

    def test_empty_row(self) -> None:
        assert _extract_actual_value({}, "numeric") is None
