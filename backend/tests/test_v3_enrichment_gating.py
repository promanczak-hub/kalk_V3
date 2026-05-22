"""Regression test: V3 enrichment must be SKIPPED when env var is unset.

Bug history (2026-05-19): early implementation defaulted to SHADOW mode, which
ran an extra Gemini 2.5 Pro call on every upload — roughly doubling extraction
time and visibly hanging the UI on "Bliźniak cyfrowy w fazie tworzenia".

This test pins the fix: by default, `apply_v3_enrichment_or_shadow` must NOT
be called by `extract_vehicle_data_v2`. It is only invoked when
`EXTRACTION_PROMPTS_V3` is one of {"1", "live", "shadow"}.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def _mock_pipeline_externals():
    """Stub the heavy Gemini-call functions so extract_vehicle_data_v2 returns fast."""
    twin = {"card_summary": {"base_price": "100000 PLN netto"}, "digital_twin": {}}
    with patch("core.extractor_v2.extract_digital_twin_from_pdf", return_value=twin), \
         patch("core.extractor_v2.generate_card_summary_from_twin", side_effect=lambda x: x), \
         patch("core.extractor_v2.validate_and_flag_prices", side_effect=lambda x: x), \
         patch("core.extractor_v2.match_fleet_discount", side_effect=lambda x: x):
        yield


def test_v3_enrichment_skipped_when_env_unset(_mock_pipeline_externals, monkeypatch):
    """No env var → V3 enrichment NOT called (zero overhead per upload)."""
    monkeypatch.delenv("EXTRACTION_PROMPTS_V3", raising=False)
    from core.extractor_v2 import extract_vehicle_data_v2

    with patch("core.extractor_v2.apply_v3_enrichment_or_shadow") as mock_v3:
        extract_vehicle_data_v2(b"fake_pdf_bytes", mime_type="application/pdf")

    mock_v3.assert_not_called()


def test_v3_enrichment_skipped_when_env_zero(_mock_pipeline_externals, monkeypatch):
    """EXTRACTION_PROMPTS_V3=0 → still SKIP (no shadow run)."""
    monkeypatch.setenv("EXTRACTION_PROMPTS_V3", "0")
    from core.extractor_v2 import extract_vehicle_data_v2

    with patch("core.extractor_v2.apply_v3_enrichment_or_shadow") as mock_v3:
        extract_vehicle_data_v2(b"fake_pdf_bytes")

    mock_v3.assert_not_called()


def test_v3_enrichment_skipped_when_env_empty_string(_mock_pipeline_externals, monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROMPTS_V3", "")
    from core.extractor_v2 import extract_vehicle_data_v2

    with patch("core.extractor_v2.apply_v3_enrichment_or_shadow") as mock_v3:
        extract_vehicle_data_v2(b"fake_pdf_bytes")

    mock_v3.assert_not_called()


def test_v3_live_mode_when_env_is_1(_mock_pipeline_externals, monkeypatch):
    """EXTRACTION_PROMPTS_V3=1 → V3 enrichment IS called with live=True."""
    monkeypatch.setenv("EXTRACTION_PROMPTS_V3", "1")
    from core.extractor_v2 import extract_vehicle_data_v2

    with patch("core.extractor_v2.apply_v3_enrichment_or_shadow", side_effect=lambda x, **kw: x) as mock_v3:
        extract_vehicle_data_v2(b"fake_pdf_bytes")

    mock_v3.assert_called_once()
    _, kwargs = mock_v3.call_args
    assert kwargs["live"] is True


def test_v3_live_mode_when_env_is_live_keyword(_mock_pipeline_externals, monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROMPTS_V3", "live")
    from core.extractor_v2 import extract_vehicle_data_v2

    with patch("core.extractor_v2.apply_v3_enrichment_or_shadow", side_effect=lambda x, **kw: x) as mock_v3:
        extract_vehicle_data_v2(b"fake_pdf_bytes")

    mock_v3.assert_called_once()
    _, kwargs = mock_v3.call_args
    assert kwargs["live"] is True


def test_v3_shadow_mode_when_env_is_shadow(_mock_pipeline_externals, monkeypatch):
    """EXTRACTION_PROMPTS_V3=shadow → V3 IS called with live=False."""
    monkeypatch.setenv("EXTRACTION_PROMPTS_V3", "shadow")
    from core.extractor_v2 import extract_vehicle_data_v2

    with patch("core.extractor_v2.apply_v3_enrichment_or_shadow", side_effect=lambda x, **kw: x) as mock_v3:
        extract_vehicle_data_v2(b"fake_pdf_bytes")

    mock_v3.assert_called_once()
    _, kwargs = mock_v3.call_args
    assert kwargs["live"] is False


def test_v3_skipped_for_string_input(_mock_pipeline_externals, monkeypatch):
    """Text-only input (str) → V3 skipped even with live mode (VLM needs PDF bytes)."""
    monkeypatch.setenv("EXTRACTION_PROMPTS_V3", "1")
    from core.extractor_v2 import extract_vehicle_data_v2

    with patch("core.extractor_v2.apply_v3_enrichment_or_shadow") as mock_v3:
        extract_vehicle_data_v2("plain text content", mime_type="text/plain")

    mock_v3.assert_not_called()
