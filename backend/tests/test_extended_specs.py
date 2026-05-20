"""Tests for the isolated extended-specs Flash pass (pipeline_extended_specs).

Contract under test:
  - NON-FATAL: any client error → {} (never raises, never breaks primary twin).
  - Feature flag EXTRACTION_EXTENDED_SPECS=0 → skip entirely (return {}).
  - Schema round-trips real-world shapes (tire labels, engine, towing, chassis).
  - Phase C: option codes carried digital_twin.optional_equipment → paid_options.
"""

from __future__ import annotations

import json

import pytest

from core.pipeline_deterministic_normalize import normalize_card_summary_from_digital_twin
from core.pipeline_extended_specs import (
    ExtendedVehicleSpecs,
    extract_extended_specs,
)


# ═══════════════════════════════════════════════════════════════════
# Schema validation
# ═══════════════════════════════════════════════════════════════════


class TestExtendedVehicleSpecsSchema:
    def test_all_optional_empty_instantiation(self) -> None:
        # Everything optional → empty instance must be valid (tire_labels=[])
        spec = ExtendedVehicleSpecs()
        assert spec.tire_labels == []
        assert spec.engine is None
        assert spec.model_year is None

    def test_full_roundtrip_audi_a5_shape(self) -> None:
        spec = ExtendedVehicleSpecs(
            model_year=2025,
            production_year=2025,
            offer_valid_until="27.10.2025",
            salesperson="Jan Kowalski, 538441919, jan@dealer.pl",
            client_name="ACME Sp. z o.o.",
            configurator_url="https://www.audi.pl/AF0CS6LR",
            engine={
                "cylinders": 4,
                "max_torque_nm": 280,
                "max_power_rpm": "3900-6000",
                "max_torque_rpm": "1400-3600",
                "top_speed_kmh": 216,
                "acceleration_0_100_s": 9.8,
                "emission_standard": "Euro 6e",
            },
            transmission={"name": "7-biegowa S tronic", "gears": 7, "clutch": "mokre podwójne"},
            towing={
                "trailer_braked_kg": 1700,
                "trailer_unbraked_kg": 750,
                "roof_load_kg": 90,
                "hitch_load_kg": 80,
            },
            chassis={"turning_radius_m": 12.1, "front_suspension": "5-wahaczowa", "rear_suspension": "5-wahaczowa"},
            wltp={"low": 9.9, "medium": 7.2, "high": 5.9, "very_high": 6.6, "combined": 6.9},
            tire_labels=[
                {"manufacturer": "Bridgestone", "name": "Turanza", "size": "245/40 R19 98Y",
                 "fuel_class": "C", "wet_grip_class": "A", "noise_class": "B", "noise_db": 69,
                 "snow": False, "ice": False},
            ],
        )
        dumped = spec.model_dump(exclude_none=True)
        assert dumped["engine"]["max_torque_nm"] == 280
        assert dumped["towing"]["trailer_braked_kg"] == 1700
        assert dumped["wltp"]["combined"] == 6.9
        assert dumped["tire_labels"][0]["fuel_class"] == "C"

    def test_schema_has_no_additionalproperties_dict(self) -> None:
        # Guard against the gemini_no_additional_properties footgun:
        # no field should serialize to a free dict[str, X].
        schema = json.dumps(ExtendedVehicleSpecs.model_json_schema())
        # `additionalProperties: true` is the dangerous shape; Pydantic emits
        # false/absent for BaseModel sub-objects, which is fine.
        assert '"additionalProperties": true' not in schema


# ═══════════════════════════════════════════════════════════════════
# extract_extended_specs — isolation contract
# ═══════════════════════════════════════════════════════════════════


class _RaisingClient:
    """Stand-in Gemini client whose call path blows up."""


class TestExtractExtendedSpecsContract:
    def test_feature_flag_off_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXTRACTION_EXTENDED_SPECS", "0")
        # Should short-circuit BEFORE touching the client at all.
        assert extract_extended_specs(client=_RaisingClient(), contents=[]) == {}

    @pytest.mark.parametrize("flag", ["off", "false", "0"])
    def test_feature_flag_variants_off(self, monkeypatch: pytest.MonkeyPatch, flag: str) -> None:
        monkeypatch.setenv("EXTRACTION_EXTENDED_SPECS", flag)
        assert extract_extended_specs(client=_RaisingClient(), contents=[]) == {}

    def test_non_fatal_on_client_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Flag ON (default) but the underlying call raises → must return {}.
        monkeypatch.setenv("EXTRACTION_EXTENDED_SPECS", "1")

        def _boom(*args, **kwargs):
            raise RuntimeError("gemini exploded")

        monkeypatch.setattr(
            "core.pipeline_extended_specs.generate_content_with_retry", _boom
        )
        # Must NOT raise — isolation guarantee.
        assert extract_extended_specs(client=_RaisingClient(), contents=[]) == {}

    def test_parses_valid_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXTRACTION_EXTENDED_SPECS", "1")

        class _Resp:
            text = json.dumps({"model_year": 2026, "tire_labels": []})

        monkeypatch.setattr(
            "core.pipeline_extended_specs.generate_content_with_retry",
            lambda **kwargs: _Resp(),
        )
        out = extract_extended_specs(client=_RaisingClient(), contents=[])
        assert out["model_year"] == 2026


# ═══════════════════════════════════════════════════════════════════
# Phase C — option code carry-through (deterministic_normalize)
# ═══════════════════════════════════════════════════════════════════


class TestOptionCodeCarryThrough:
    def test_option_code_flows_to_paid_options(self) -> None:
        card: dict = {"paid_options": []}
        twin = {
            "brand": "AUDI",
            "model": "A5",
            "optional_equipment": [
                {"name": "Hak holowniczy", "price": "5650.00 zł", "code": "1D4"},
            ],
        }
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["paid_options"][0]["option_code"] == "1D4"

    def test_missing_code_yields_none(self) -> None:
        card: dict = {"paid_options": []}
        twin = {
            "brand": "AUDI",
            "model": "A5",
            "optional_equipment": [{"name": "Pakiet zima", "price": "1200.00 zł"}],
        }
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["paid_options"][0]["option_code"] is None

    def test_blank_code_normalized_to_none(self) -> None:
        card: dict = {"paid_options": []}
        twin = {
            "brand": "AUDI",
            "model": "A5",
            "optional_equipment": [{"name": "Coś", "price": "100.00 zł", "code": "   "}],
        }
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["paid_options"][0]["option_code"] is None
