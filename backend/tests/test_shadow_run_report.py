"""Unit tests for the shadow-run report builder.

Pure logic over JSON entries — no filesystem dependency in this test.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from shadow_run_report import build_report  # noqa: E402


def test_empty_input_returns_placeholder() -> None:
    report = build_report([])
    assert "No shadow entries found" in report


def test_no_diff_no_errors() -> None:
    entries = [
        {"elapsed_s": 1.2, "errors": [], "field_diff": {}},
        {"elapsed_s": 0.8, "errors": [], "field_diff": {}},
    ]
    report = build_report(entries)
    assert "Total entries: **2**" in report
    assert "with errors: **0**" in report
    assert "No field-level divergences" in report


def test_field_divergence_counted() -> None:
    entries = [
        {
            "elapsed_s": 1.0,
            "errors": [],
            "field_diff": {
                "base_price_net": {"legacy": None, "v3": 100000.0},
            },
        },
        {
            "elapsed_s": 1.0,
            "errors": [],
            "field_diff": {
                "base_price_net": {"legacy": None, "v3": 120000.0},
                "_duplicate_flags": {"legacy": None, "v3": [{"a": 1}]},
            },
        },
    ]
    report = build_report(entries)
    assert "`base_price_net`" in report
    assert "`_duplicate_flags`" in report
    # 2/2 = 100% for base_price_net
    assert "100.0%" in report


def test_error_rate_decision() -> None:
    # >10% errors → fix root causes
    entries = [{"elapsed_s": 1.0, "errors": ["Boom"], "field_diff": {}}] * 5
    report = build_report(entries)
    assert "exceeds 10%" in report or "Error rate" in report


def test_clean_divergence_decision() -> None:
    entries = [
        {"elapsed_s": 1.0, "errors": [], "field_diff": {"base_price_net": {"legacy": None, "v3": 100.0}}}
    ] * 10
    report = build_report(entries)
    assert "Review samples" in report or "promote V3" in report


def test_no_diff_no_error_decision() -> None:
    entries = [{"elapsed_s": 0.5, "errors": [], "field_diff": {}}] * 3
    report = build_report(entries)
    assert "No divergences detected" in report or "identical" in report
