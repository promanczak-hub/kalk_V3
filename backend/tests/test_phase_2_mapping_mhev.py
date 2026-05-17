"""Unit tests for ``detect_mhev_fuel_override`` (Fix B for m-HEV mapping bug).

Background: Gemini Pro extraction occasionally drops the m-HEV/mHEV/"miękka
hybryda" marker from card_summary fields, which caused Skoda Octavia 1.5 TSI
m-HEV to map to engine_id=1 (Benzyna PB) instead of engine_id=3 (Benzyna mHEV).
This module guards against that by scanning the raw extraction fields for the
mHEV signal before the downstream AI mapper runs.
"""

from core.extraction_pipeline.phase_2_mapping import detect_mhev_fuel_override


def test_mhev_in_powertrain_overrides_to_pb_mhev():
    cs = {"powertrain": "1.5 TSI m-HEV 150 KM", "engine_designation": "TSI", "fuel": "Benzyna"}
    assert detect_mhev_fuel_override({}, cs, "Benzyna (PB)") == "Benzyna mHEV (PB-mHEV)"


def test_mhev_in_engine_marketing_name_overrides():
    cs = {
        "powertrain": "1.5 TSI 150 KM",
        "engine_designation": "TSI",
        "fuel": "Benzyna",
        "engine_marketing_name": "m-HEV",
    }
    assert detect_mhev_fuel_override({}, cs, "Benzyna (PB)") == "Benzyna mHEV (PB-mHEV)"


def test_miekka_hybryda_phrasing_overrides():
    """PDF Dane techniczne uses 'mHEV – miękka hybryda' phrasing."""
    cs = {"powertrain": "1.5 TSI 150 KM", "fuel": "mHEV – miękka hybryda"}
    assert detect_mhev_fuel_override({}, cs, "Benzyna (PB)") == "Benzyna mHEV (PB-mHEV)"


def test_diesel_mhev_overrides_to_on_mhev():
    cs = {"powertrain": "2.0 TDI mHEV 150 KM", "fuel": "Diesel"}
    assert detect_mhev_fuel_override({}, cs, "Diesel (ON)") == "Diesel mHEV (ON-mHEV)"


def test_plain_pb_no_mhev_returns_none():
    cs = {"powertrain": "2.0 TSI 245 KM", "engine_designation": "TSI", "fuel": "Benzyna"}
    assert detect_mhev_fuel_override({}, cs, "Benzyna (PB)") is None


def test_plain_diesel_no_mhev_returns_none():
    cs = {"powertrain": "2.0 TDI 150 KM", "engine_designation": "TDI", "fuel": "Diesel"}
    assert detect_mhev_fuel_override({}, cs, "Diesel (ON)") is None


def test_mhev_signal_in_parsed_data_only():
    """When card_summary is empty but parsed_data carries the m-HEV marker."""
    cs = {"fuel": "Benzyna"}
    parsed = {"engine_designation": "TSI m-HEV", "fuel": "Benzyna"}
    assert detect_mhev_fuel_override(parsed, cs, "Benzyna (PB)") == "Benzyna mHEV (PB-mHEV)"


def test_already_mhev_fuel_still_returns_mhev_canonical():
    """If mapped fuel was already mHEV (rare), guard still returns canonical name."""
    cs = {"powertrain": "1.5 TSI m-HEV 150 KM", "fuel": "Benzyna mHEV (PB-mHEV)"}
    result = detect_mhev_fuel_override({}, cs, "Benzyna mHEV (PB-mHEV)")
    assert result == "Benzyna mHEV (PB-mHEV)"


def test_capacity_dict_powertrain_does_not_crash():
    """Edge case: when powertrain is a dict (legacy shape) with mHEV in a value."""
    cs = {"powertrain": {"engine_designation": "TSI m-HEV", "power": "150"}, "fuel": "Benzyna"}
    assert detect_mhev_fuel_override({}, cs, "Benzyna (PB)") == "Benzyna mHEV (PB-mHEV)"


def test_document_markdown_scan_catches_mhev_when_structured_lost_it():
    """Gemini Pro re-extraction (CS99NRMW, 2026-05-17) dropped m-HEV from all
    card_summary fields. The raw document_markdown still contains the marker.
    This test pins the markdown-scan rescue path."""
    cs = {"powertrain": "1.5 TSI 150 KM", "engine_designation": "TSI", "fuel": "Benzyna"}
    markdown = (
        "Octavia Combi Sportline\n"
        "1,5 TSI m-HEV (150 KM) 110 kW 7-biegowa automatyczna\n"
        "...\n"
        "Dane techniczne\n"
        "Paliwo: mHEV – miękka hybryda\n"
    )
    assert (
        detect_mhev_fuel_override({}, cs, "Benzyna (PB)", document_markdown=markdown)
        == "Benzyna mHEV (PB-mHEV)"
    )


def test_document_markdown_without_mhev_does_not_trigger_false_positive():
    """A non-mHEV PDF with similar 'hybryd' words should not trigger override."""
    cs = {"powertrain": "2.0 TSI 245 KM", "fuel": "Benzyna"}
    markdown = (
        "Volkswagen Golf GTI\n"
        "2.0 TSI 245 KM 7-biegowa automatyczna\n"
        "(Notice: hybryda Plug-in NOT available for this trim.)\n"  # 'hybryda' but no m-HEV
    )
    assert (
        detect_mhev_fuel_override({}, cs, "Benzyna (PB)", document_markdown=markdown)
        is None
    )


def test_document_markdown_only_signal_diesel_mhev():
    """When only the markdown has the m-HEV signal, and base fuel is Diesel."""
    cs = {"powertrain": "2.0 TDI 150 KM", "engine_designation": "TDI", "fuel": "Diesel"}
    markdown = "2.0 TDI mHEV – miękka hybryda diesel"
    assert (
        detect_mhev_fuel_override({}, cs, "Diesel (ON)", document_markdown=markdown)
        == "Diesel mHEV (ON-mHEV)"
    )
