"""Tests for deterministic multi-vehicle fallback heuristic.

When Gemini Flash returns count=1 but the document text contains multiple
distinct calculation sections (e.g. "Kalkulacja dla Państwa firmy" appearing
twice for two Hilux variants), the fallback overrides the count to match
the number of sections.

Rationale: Flash sometimes mis-classifies same-model multi-variant offers
(2× Hilux, 2× Master) as a "general price list with engine versions" → 1
vehicle, dropping the multi-vehicle split. Section-count is a deterministic
ground truth.
"""

from __future__ import annotations

import pytest

from core.pipeline_multi_vehicle import (
    count_calculation_sections,
    _CALCULATION_SECTION_PATTERNS,
)


# ═══════════════════════════════════════════════════════════════════
# count_calculation_sections — regex counter
# ═══════════════════════════════════════════════════════════════════


class TestCountCalculationSections:
    def test_zero_sections_returns_zero(self) -> None:
        text = "To jest broszura modelu Hilux, bez kalkulacji handlowej."
        assert count_calculation_sections(text) == 0

    def test_single_kalkulacja_section(self) -> None:
        text = """
        Toyota Hilux 2.4 D-4D Executive

        KALKULACJA DLA Państwa firmy:
        Cena bazowa: 165 000 PLN netto
        Cena specjalna: 142 000 PLN netto
        """
        assert count_calculation_sections(text) == 1

    def test_two_kalkulacja_sections_one_pdf(self) -> None:
        """The actual user case: two Hilux variants in one PDF."""
        text = """
        Toyota Hilux MY24 Executive 2.4 D-4D

        Kalkulacja dla Państwa firmy
        Cena bazowa: 165 000 PLN netto
        Wybrane wyposażenie dodatkowe: 8 500 PLN netto
        Cena specjalna: 142 000 PLN netto

        ─────────────────────────────────────

        Toyota Hilux NG '26 Comfort 2.8 D-4D

        Kalkulacja dla Państwa firmy
        Cena bazowa: 175 000 PLN netto
        Wybrane wyposażenie dodatkowe: 12 000 PLN netto
        Cena specjalna: 155 000 PLN netto
        """
        assert count_calculation_sections(text) == 2

    def test_three_sections_returns_three(self) -> None:
        text = (
            "Kalkulacja dla firmy Acme — Renault Master\n"
            "Cena specjalna: 120 000 PLN\n\n"
            "Kalkulacja dla firmy Acme — Renault Trafic\n"
            "Cena specjalna: 95 000 PLN\n\n"
            "Kalkulacja dla firmy Acme — Renault Kangoo\n"
            "Cena specjalna: 75 000 PLN"
        )
        assert count_calculation_sections(text) == 3

    def test_case_insensitive(self) -> None:
        text = "kalkulacja dla państwa firmy\n... Kalkulacja Dla Państwa Firmy\n"
        assert count_calculation_sections(text) == 2

    def test_polish_diacritics_handled(self) -> None:
        text = (
            "Kalkulacja dla Państwa firmy: Wariant A\n"
            "Kalkulacja dla Państwa firmy: Wariant B\n"
        )
        assert count_calculation_sections(text) == 2

    def test_returns_max_of_multiple_signal_kinds(self) -> None:
        """Use the MAX of available signals (Kalkulacja dla, Cena specjalna, etc).

        A document might have 2 "Cena specjalna" but only 1 "Kalkulacja dla"
        header (header could be in a parent section). We trust the higher signal.
        """
        text = (
            "OFERTA HANDLOWA\n\n"
            "Wariant 1\nCena specjalna: 100 000 PLN\n\n"
            "Wariant 2\nCena specjalna: 120 000 PLN\n\n"
            "Wariant 3\nCena specjalna: 140 000 PLN\n"
        )
        assert count_calculation_sections(text) == 3

    def test_empty_or_none_returns_zero(self) -> None:
        assert count_calculation_sections("") == 0
        assert count_calculation_sections(None) == 0  # type: ignore[arg-type]

    def test_patterns_registered_for_polish_phrases(self) -> None:
        """Catalog assertion — these phrases MUST match at least one pattern."""
        required = (
            "Kalkulacja dla",
            "Cena specjalna",
            "Konfiguracja nr",
        )
        for phrase in required:
            matched = any(p.search(phrase) for p in _CALCULATION_SECTION_PATTERNS)
            assert matched, f"Pattern catalogue missing required phrase: {phrase!r}"


# ═══════════════════════════════════════════════════════════════════
# detect_and_split_vehicles — fallback integration
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def _two_hilux_text() -> str:
    return """
    Toyota Hilux MY24 Executive 2.4 D-4D

    Kalkulacja dla Państwa firmy
    Cena bazowa: 165 000 PLN netto
    Wybrane wyposażenie dodatkowe: 8 500 PLN netto
    Cena specjalna: 142 000 PLN netto

    ─────────────────────────────────────

    Toyota Hilux NG '26 Comfort 2.8 D-4D

    Kalkulacja dla Państwa firmy
    Cena bazowa: 175 000 PLN netto
    Wybrane wyposażenie dodatkowe: 12 000 PLN netto
    Cena specjalna: 155 000 PLN netto
    """


def test_fallback_overrides_when_flash_misses_split(
    monkeypatch, _two_hilux_text
) -> None:
    """Flash returns 1 but PDF text has 2 "Kalkulacja dla" → split into 2."""
    from core import pipeline_multi_vehicle as pmv

    # Mock Flash to say "1 vehicle" (the bug we're fixing)
    monkeypatch.setattr(pmv, "detect_vehicle_count", lambda *a, **kw: 1)

    extract_calls: list[int] = []

    def _fake_extract(document_data, mime_type, expected_count, text_data=None):
        extract_calls.append(expected_count)
        return [
            {"brand": "Toyota", "model": "Hilux", "trim_level": "Executive"},
            {"brand": "Toyota", "model": "Hilux", "trim_level": "Comfort"},
        ]

    monkeypatch.setattr(pmv, "extract_multi_vehicle_twins", _fake_extract)

    result = pmv.detect_and_split_vehicles(
        b"fake_pdf_bytes",
        mime_type="application/pdf",
        text_data=_two_hilux_text,
    )

    assert result is not None, "Fallback did not engage — expected 2 vehicles"
    assert len(result) == 2
    # Pro was asked for 2 vehicles (override from Flash's 1)
    assert extract_calls and extract_calls[0] == 2


def test_no_fallback_when_only_one_section(monkeypatch) -> None:
    """Single calculation section → trust Flash's count=1 → no split."""
    from core import pipeline_multi_vehicle as pmv

    text = "Toyota Hilux\nKalkulacja dla Państwa firmy\nCena specjalna: 142000 PLN"
    monkeypatch.setattr(pmv, "detect_vehicle_count", lambda *a, **kw: 1)

    result = pmv.detect_and_split_vehicles(
        b"fake_pdf_bytes",
        mime_type="application/pdf",
        text_data=text,
    )
    assert result is None


def test_no_fallback_when_text_data_missing(monkeypatch) -> None:
    """No PDF text → can't run heuristic → trust Flash."""
    from core import pipeline_multi_vehicle as pmv

    monkeypatch.setattr(pmv, "detect_vehicle_count", lambda *a, **kw: 1)
    result = pmv.detect_and_split_vehicles(
        b"fake_pdf_bytes", mime_type="application/pdf", text_data=None
    )
    assert result is None


def test_flash_count_wins_when_higher_than_fallback(monkeypatch) -> None:
    """Flash says 3, fallback finds 2 → trust Flash (Flash > heuristic)."""
    from core import pipeline_multi_vehicle as pmv

    text = "Kalkulacja dla A\nCena specjalna: 100\n\nKalkulacja dla B\nCena specjalna: 200"
    monkeypatch.setattr(pmv, "detect_vehicle_count", lambda *a, **kw: 3)

    extract_calls: list[int] = []

    def _fake_extract(*args, expected_count, **kw):
        extract_calls.append(expected_count)
        return [{"brand": "X"}, {"brand": "Y"}, {"brand": "Z"}]

    monkeypatch.setattr(pmv, "extract_multi_vehicle_twins", _fake_extract)

    result = pmv.detect_and_split_vehicles(
        b"fake_pdf_bytes", mime_type="application/pdf", text_data=text
    )
    assert result is not None
    assert len(result) == 3
    assert extract_calls[0] == 3  # Flash count wins


# ═══════════════════════════════════════════════════════════════════
# Wiring regression — background_jobs must forward text_data
# ═══════════════════════════════════════════════════════════════════


def test_background_jobs_forwards_text_data_to_detector() -> None:
    """The call site in background_jobs.process_and_save_document_bg must pass
    text_data to detect_and_split_vehicles, otherwise the deterministic
    "Cena specjalna" / "Kalkulacja dla" counter cannot override a Flash
    miscount on same-model multi-variant offers (e.g. 2× Hilux in one PDF).
    """
    import ast
    import inspect

    from core import background_jobs

    tree = ast.parse(inspect.getsource(background_jobs))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "detect_and_split_vehicles"
    ]

    assert calls, "Expected detect_and_split_vehicles to be called in background_jobs"
    for call in calls:
        kwargs = {kw.arg for kw in call.keywords}
        assert "text_data" in kwargs, (
            "detect_and_split_vehicles must be called with `text_data=...` "
            "so the deterministic anchor counter can override a Flash miscount. "
            "Without it, 2× same-model offers (2× Hilux, 2× Master) get merged "
            "into a single Frankenstein vehicle."
        )
