"""Phase A — tests for HITL confidence/hallucination plumbing.

Verifies:
1. Pydantic schema accepts new confidence + field_id + confidence_breakdown + hallucinated_fields fields
2. _post_process_hitl_metadata removes confidence=0.0 entries + generates field_id
3. _apply_validator_penalties lowers confidence based on warning severity + field_path
4. _needs_hitl_review triggers on low confidence / hallucinations / blocking warnings
5. validate_and_flag_prices feeds penalties into confidence_breakdown / paid_options.confidence
"""

from __future__ import annotations

import pytest

from core.extractor_models import (
    CardSummary,
    DiscountBreakdown,
    PaidOption,
    ServiceComponentItem,
)
from core.extraction_pipeline.phase_2_mapping import _needs_hitl_review
from core.pipeline_card_summary import _post_process_hitl_metadata
from core.pipeline_price_validator import (
    ValidationReport,
    ValidationWarning,
    _apply_validator_penalties,
    _decrement_confidence,
)


# ── Schema acceptance ────────────────────────────────────────────────────

class TestSchemaAcceptsHITLFields:
    def test_paid_option_confidence_and_field_id(self):
        po = PaidOption(
            name="Zabudowa",
            price="47970 PLN brutto",
            category="Serwisowa",
            confidence=0.5,
            field_id="uuid-abc",
        )
        assert po.confidence == 0.5
        assert po.field_id == "uuid-abc"

    def test_paid_option_defaults(self):
        po = PaidOption(name="x", price="100", category="F")
        assert po.confidence == 1.0
        assert po.field_id == ""

    def test_paid_option_confidence_clamp(self):
        with pytest.raises(Exception):
            PaidOption(name="x", price="100", category="F", confidence=1.5)
        with pytest.raises(Exception):
            PaidOption(name="x", price="100", category="F", confidence=-0.1)

    def test_service_component_confidence(self):
        sc = ServiceComponentItem(
            name="Agregat", price_net="15000", price_gross="18450", confidence=0.8
        )
        assert sc.confidence == 0.8
        assert sc.field_id == ""

    def test_discount_breakdown_hitl_fields(self):
        db = DiscountBreakdown(
            rabat_type="kwotowo",
            rabat_basis="brutto",
            discount_scope=["base", "factory_options"],
        )
        assert db.rabat_type == "kwotowo"
        assert db.rabat_basis == "brutto"
        assert db.discount_scope == ["base", "factory_options"]

    def test_card_summary_confidence_breakdown_and_hallucinated(self):
        cs = CardSummary(
            financial_reasoning="x",
            base_price="100k",
            options_price="10k",
            total_price="110k",
            powertrain="dCi",
            vehicle_class="Dostawczy",
            fuel="Diesel",
            transmission="Manualna",
            body_style="Podwozie",
            trim_level="x",
            wheels="16",
            emissions="347",
            exterior_color="biały",
            standard_equipment=[],
            paid_options=[],
            available_powertrains=[],
            available_trims=[],
            starting_price="100k",
            key_technologies=[],
            confidence_breakdown={"base_price": 0.5},
            hallucinated_fields=["paid_options.7.price"],
        )
        assert cs.confidence_breakdown == {"base_price": 0.5}
        assert cs.hallucinated_fields == ["paid_options.7.price"]


# ── Post-process hallucination removal ───────────────────────────────────

class TestPostProcessHITLMetadata:
    def test_removes_paid_option_with_confidence_zero(self):
        cs = {
            "paid_options": [
                {"name": "real", "price": "100", "category": "F", "confidence": 0.5},
                {"name": "halu", "price": "999", "category": "F", "confidence": 0.0},
                {"name": "real2", "price": "50", "category": "F", "confidence": 1.0},
            ]
        }
        _post_process_hitl_metadata(cs)
        assert len(cs["paid_options"]) == 2
        assert [o["name"] for o in cs["paid_options"]] == ["real", "real2"]
        assert "paid_options.1:halu" in cs["hallucinated_fields"]

    def test_generates_field_id_for_surviving_options(self):
        cs = {
            "paid_options": [
                {"name": "a", "price": "100", "category": "F", "confidence": 0.5},
                {"name": "b", "price": "50", "category": "F", "confidence": 1.0},
            ]
        }
        _post_process_hitl_metadata(cs)
        ids = [o["field_id"] for o in cs["paid_options"]]
        assert all(len(i) == 36 for i in ids)  # uuid4 format
        assert ids[0] != ids[1]

    def test_preserves_existing_field_id(self):
        cs = {
            "paid_options": [
                {"name": "a", "price": "100", "category": "F", "confidence": 1.0, "field_id": "preset-id"},
            ]
        }
        _post_process_hitl_metadata(cs)
        assert cs["paid_options"][0]["field_id"] == "preset-id"

    def test_removes_service_component_with_confidence_zero(self):
        cs = {
            "service_equipment": {
                "name": "Kontener",
                "components": [
                    {"name": "agregat", "price_net": "15000", "price_gross": "18450", "confidence": 0.8},
                    {"name": "halu_comp", "price_net": "0", "price_gross": "0", "confidence": 0.0},
                ],
            }
        }
        _post_process_hitl_metadata(cs)
        assert len(cs["service_equipment"]["components"]) == 1
        assert cs["service_equipment"]["components"][0]["name"] == "agregat"
        assert "service_equipment.components.1:halu_comp" in cs["hallucinated_fields"]

    def test_removes_zero_confidence_top_level_keys(self):
        cs = {
            "confidence_breakdown": {
                "base_price": 0.9,
                "samar_category": 0.0,
                "body_style": 0.5,
            }
        }
        _post_process_hitl_metadata(cs)
        assert "samar_category" not in cs["confidence_breakdown"]
        assert cs["confidence_breakdown"]["base_price"] == 0.9
        assert cs["confidence_breakdown"]["body_style"] == 0.5
        assert "top_level:samar_category" in cs["hallucinated_fields"]

    def test_no_op_on_empty_card_summary(self):
        cs = {}
        _post_process_hitl_metadata(cs)
        assert cs.get("hallucinated_fields") is None

    def test_no_op_on_non_dict(self):
        _post_process_hitl_metadata(None)  # type: ignore[arg-type]
        _post_process_hitl_metadata("not a dict")  # type: ignore[arg-type]


# ── Validator penalty propagation ────────────────────────────────────────

class TestValidatorPenalties:
    def test_decrement_paid_option_confidence(self):
        cs = {"paid_options": [{"name": "x", "confidence": 1.0}]}
        _decrement_confidence(cs, "paid_options.0", 0.5)
        assert cs["paid_options"][0]["confidence"] == 0.5

    def test_decrement_paid_option_subpath(self):
        cs = {"paid_options": [{"name": "x", "confidence": 0.8}]}
        _decrement_confidence(cs, "paid_options.0.price", 0.2)
        assert cs["paid_options"][0]["confidence"] == pytest.approx(0.6)

    def test_decrement_service_component_confidence(self):
        cs = {"service_equipment": {"components": [{"name": "c", "confidence": 1.0}]}}
        _decrement_confidence(cs, "service_equipment.components.0", 0.2)
        assert cs["service_equipment"]["components"][0]["confidence"] == pytest.approx(0.8)

    def test_decrement_top_level_goes_to_confidence_breakdown(self):
        cs = {}
        _decrement_confidence(cs, "base_price", 0.5)
        assert cs["confidence_breakdown"]["base_price"] == 0.5

    def test_decrement_clamps_at_zero(self):
        cs = {"paid_options": [{"name": "x", "confidence": 0.1}]}
        _decrement_confidence(cs, "paid_options.0", 0.5)
        assert cs["paid_options"][0]["confidence"] == 0.0

    def test_decrement_ignores_empty_path(self):
        cs = {"paid_options": [{"name": "x", "confidence": 1.0}]}
        _decrement_confidence(cs, "", 0.5)
        assert cs["paid_options"][0]["confidence"] == 1.0

    def test_apply_penalties_from_validator_report(self):
        cs = {
            "paid_options": [
                {"name": "Zabudowa", "confidence": 1.0},
                {"name": "Agregat", "confidence": 1.0},
            ]
        }
        report = ValidationReport()
        report.warnings = [
            ValidationWarning(
                rule="DEALER_EXTRA_DETECTED",
                message="x",
                severity="INFO",
                field_path="paid_options.0,paid_options.1",
            ),
            ValidationWarning(
                rule="BASE_PLUS_OPTIONS_VS_TOTAL",
                message="x",
                severity="ERROR",
                field_path="total_price",
            ),
        ]
        _apply_validator_penalties(cs, report)
        # INFO penalty = 0.05 applied to both
        assert cs["paid_options"][0]["confidence"] == pytest.approx(0.95)
        assert cs["paid_options"][1]["confidence"] == pytest.approx(0.95)
        # ERROR penalty = 0.5 applied to top-level
        assert cs["confidence_breakdown"]["total_price"] == pytest.approx(0.5)

    def test_no_penalty_for_warning_without_field_path(self):
        cs = {"paid_options": [{"name": "x", "confidence": 1.0}]}
        report = ValidationReport()
        report.warnings = [
            ValidationWarning(rule="POWER_KW_HP_MISMATCH", message="m", severity="WARNING"),
        ]
        _apply_validator_penalties(cs, report)
        assert cs["paid_options"][0]["confidence"] == 1.0


# ── HITL trigger logic ───────────────────────────────────────────────────

class TestNeedsHITLReview:
    def test_no_review_for_clean_card_summary(self):
        cs = {
            "paid_options": [{"name": "a", "confidence": 1.0}],
            "confidence_breakdown": {"base_price": 1.0},
        }
        needs, reasons = _needs_hitl_review(cs)
        assert needs is False
        assert reasons == []

    def test_triggers_on_low_confidence_breakdown(self):
        cs = {"confidence_breakdown": {"base_price": 0.4}}
        needs, reasons = _needs_hitl_review(cs)
        assert needs is True
        assert any("base_price" in r for r in reasons)

    def test_triggers_on_low_paid_option_confidence(self):
        cs = {"paid_options": [{"name": "a", "confidence": 0.3}]}
        needs, reasons = _needs_hitl_review(cs)
        assert needs is True
        assert any("paid_options" in r for r in reasons)

    def test_triggers_on_hallucinated_fields(self):
        cs = {"hallucinated_fields": ["paid_options.5:phantom"]}
        needs, reasons = _needs_hitl_review(cs)
        assert needs is True
        assert any("hallucinated_fields" in r for r in reasons)

    def test_triggers_on_validator_error(self):
        cs = {
            "_validation": {
                "warnings": [
                    {"rule": "TOTAL_BELOW_BASE", "severity": "ERROR"},
                ]
            }
        }
        needs, reasons = _needs_hitl_review(cs)
        assert needs is True

    def test_triggers_on_blocking_warning_rule(self):
        cs = {
            "_validation": {
                "warnings": [
                    {"rule": "OPTION_PRICE_UNPARSEABLE", "severity": "WARNING"},
                ]
            }
        }
        needs, reasons = _needs_hitl_review(cs)
        assert needs is True

    def test_does_not_trigger_on_non_blocking_warning(self):
        cs = {
            "paid_options": [],
            "confidence_breakdown": {},
            "_validation": {
                "warnings": [
                    {"rule": "POWER_KW_HP_MISMATCH", "severity": "WARNING"},
                ]
            },
        }
        needs, reasons = _needs_hitl_review(cs)
        assert needs is False

    def test_triggers_on_legacy_requires_user_input(self):
        cs = {"_requires_user_input": ["base_price"]}
        needs, reasons = _needs_hitl_review(cs)
        assert needs is True

    def test_threshold_is_strict_inequality(self):
        # 0.7 exactly should NOT trigger
        cs = {"confidence_breakdown": {"base_price": 0.7}}
        needs, _ = _needs_hitl_review(cs)
        assert needs is False
        # 0.69 SHOULD trigger
        cs2 = {"confidence_breakdown": {"base_price": 0.69}}
        needs2, _ = _needs_hitl_review(cs2)
        assert needs2 is True

    def test_handles_non_dict_input(self):
        needs, reasons = _needs_hitl_review(None)  # type: ignore[arg-type]
        assert needs is False
        assert reasons == []
