"""Unit tests for the multi-hypothesis price-reconciliation engine.

Pure dict logic — no DB, no network (run_judge=False). The engine computes the
full net/gross breakdown under 4 hypotheses (components netto/brutto × final
netto/brutto), scores each by how well it reproduces every labeled total in the
PDF, and picks the best. See plans/multi-hypothesis-price-reconciliation.md.
"""

from __future__ import annotations

from typing import Any

import pytest

from core import pipeline_price_reconciliation as ppr
from core.pipeline_price_reconciliation import reconcile_and_flag, reconcile_prices


# ── Real fixture: BMW X5 xDrive25d, Oferta 154627 (Inchcape) ──
# Everything labeled "cena brutto z VAT"; every total cross-foots:
#   base 312 000 + opcje 78 500 = katalog 390 500
#   390 500 − upust 66 385 = 324 115 brutto = 263 508,14 netto (÷1,23)
def _bmw_154627() -> dict[str, Any]:
    return {
        "brand": "BMW",
        "model": "X5 xDrive25d",
        "_raw_price_lines": [
            {"role": "base_price", "gross_amount": 312000.0, "net_amount": None, "label": "brutto", "vat_rate": 0.23},
            {"role": "options_total", "gross_amount": 78500.0, "net_amount": None, "label": "brutto", "vat_rate": 0.23},
            {"role": "discount", "gross_amount": 66385.0, "net_amount": None, "label": "brutto", "vat_rate": 0.23},
            {"role": "other", "quoted_text": "Cena katalogowa", "gross_amount": 390500.0, "net_amount": None, "label": "brutto", "vat_rate": 0.23},
            {"role": "total_price", "gross_amount": 324115.0, "net_amount": None, "label": "brutto", "vat_rate": 0.23},
            {"role": "total_price", "gross_amount": None, "net_amount": 263508.14, "label": "netto", "vat_rate": 0.23},
        ],
    }


def test_bmw_154627_picks_brutto_path():
    res = reconcile_prices(_bmw_154627(), run_judge=False)

    assert res.verdict == "ok"
    assert res.source_domain == "brutto"
    assert res.best.total_net == pytest.approx(263508.14, abs=1.0)
    assert res.best.total_gross == pytest.approx(324115.0, abs=1.0)
    assert res.best.hypothesis.source_domain == "brutto"
    assert len(res.all_paths) == 4
    assert res.warning is None  # ok verdict → flows to `completed`


def test_bmw_netto_source_path_loses():
    """The false-match guard: reading components as NETTO numerically hits the
    printed 324 115 (312000+78500-66385) but predicts gross 398 661 ≠ printed
    324 115. Scoring across the net/gross PAIR must reject it."""
    res = reconcile_prices(_bmw_154627(), run_judge=False)

    netto_paths = [p for p in res.all_paths if p.hypothesis.source_domain == "netto"]
    assert netto_paths, "expected netto-source hypotheses to exist"
    assert all(p.residual_pln > 1000 for p in netto_paths)
    assert res.best.hypothesis.source_domain == "brutto"


def test_domain_flip_brutto_wins_despite_netto_labels():
    """Renault-Master-style: components mislabeled 'netto' but the final net/gross
    PAIR only reconciles when components are read as BRUTTO. Arithmetic overrides
    the wrong label (memory price-domain-flip-deduction)."""
    card = {
        "_raw_price_lines": [
            {"role": "base_price", "gross_amount": None, "net_amount": 100000.0, "label": "netto", "vat_rate": 0.23},
            {"role": "options_total", "gross_amount": None, "net_amount": 23000.0, "label": "netto", "vat_rate": 0.23},
            # final pair printed verbatim — the trustworthy anchor:
            {"role": "total_price", "gross_amount": None, "net_amount": 100000.0, "label": "netto", "vat_rate": 0.23},
            {"role": "total_price", "gross_amount": 123000.0, "net_amount": None, "label": "brutto", "vat_rate": 0.23},
        ],
    }
    res = reconcile_prices(card, run_judge=False)

    assert res.verdict == "ok"
    assert res.source_domain == "brutto"
    assert res.best.total_net == pytest.approx(100000.0, abs=1.0)
    assert res.best.total_gross == pytest.approx(123000.0, abs=1.0)


def test_degenerate_single_anchor_is_ambiguous():
    """One unlabeled total, no net/gross pair → both source domains reconcile
    equally → engine must NOT guess; verdict is ambiguous (→ HITL / judge)."""
    card = {
        "_raw_price_lines": [
            {"role": "base_price", "gross_amount": None, "net_amount": 100000.0, "label": None, "vat_rate": 0.23},
            {"role": "total_price", "gross_amount": None, "net_amount": 100000.0, "label": None, "vat_rate": 0.23},
        ],
    }
    res = reconcile_prices(card, run_judge=False)

    assert res.verdict == "ambiguous"
    assert res.warning is not None
    assert res.warning["rule"] == "PRICE_RECONCILIATION_AMBIGUOUS"


# ── Non-V3 fallback: card_summary stores prices as legacy strings ──


def test_fallback_parses_legacy_string_prices_no_raw_lines():
    """Real non-V3 shape (regression: this returned 0/0 → ambiguous before the fix).
    Prices are strings, no _raw_price_lines — the fallback must parse them."""
    card = {
        "base_price": "312 000,00 PLN brutto",
        "options_price": "78 500,00 PLN brutto",
        "total_price": "324 115,00 PLN brutto",
        "discount": {"explicit_rabat_pln": 66385.0},
        "_price_domain": "brutto",
    }
    res = reconcile_prices(card, run_judge=False)

    assert res.verdict == "ok"
    assert res.source_domain == "brutto"
    assert res.best.total_gross == pytest.approx(324115.0, abs=2.0)


def test_fallback_includes_service_equipment_zabudowa():
    """SINGLE-ANCHOR fallback: base+options alone miss the zabudowa (service_equipment);
    including it closes the sum (regression: was 'unreconcilable').

    NOTE: with only ONE total anchor (netto-labeled) and no net/gross pair, the engine
    has nothing to contradict the printed label, so it TRUSTS 'netto' — it cannot detect
    a domain flip here. For the real izoterma this netto reading is the suspected flip
    (204 817,14 is actually brutto), caught downstream by FULL_SUM_INTEGRITY → HITL. Flip
    CORRECTION needs the PODSUMOWANIE pair — see test_summary_pair_corrects_netto_label_flip."""
    card = {
        "base_price": "167 218.50 PLN netto",
        "options_price": "2 029.50 PLN netto",
        "total_price": "204 817.14 PLN netto",
        "discount": {"explicit_rabat_pln": 49928.16},
        "service_equipment": {"net_amount": 85497.30},
        "_price_domain": "netto",
    }
    res = reconcile_prices(card, run_judge=False)

    assert res.verdict == "ok"
    assert res.source_domain == "netto"  # single anchor → label trusted (NOT flip-corrected)
    assert res.best.total_net == pytest.approx(204817.14, abs=2.0)


def test_summary_pair_corrects_netto_label_flip():
    """Capturing the PDF PODSUMOWANIE as a PAIR flips the verdict the single-anchor
    fallback gets wrong. Izoterma-shaped components are mislabeled 'netto'; once both
    summary totals (netto 166 518 / brutto 204 817,14) are present as two total_price
    lines, only the BRUTTO reading reconciles against BOTH anchors, so the engine
    overrides the wrong label — total gross 204 817,14, net ~166 518."""
    card = {
        "_raw_price_lines": [
            {"role": "base_price", "net_amount": 167218.50, "label": "netto", "vat_rate": 0.23},
            {"role": "options_total", "net_amount": 2029.50, "label": "netto", "vat_rate": 0.23},
            {"role": "service_total", "net_amount": 85497.30, "label": "netto", "vat_rate": 0.23},
            {"role": "discount", "net_amount": 49928.16, "label": "netto", "vat_rate": 0.23},
            # PODSUMOWANIE pair — the trustworthy independent anchors:
            {"role": "total_price", "net_amount": 166518.00, "label": "netto", "vat_rate": 0.23},
            {"role": "total_price", "gross_amount": 204817.14, "label": "brutto", "vat_rate": 0.23},
        ],
    }
    res = reconcile_prices(card, run_judge=False)

    assert res.verdict == "ok"
    assert res.source_domain == "brutto"
    assert res.best.total_gross == pytest.approx(204817.14, abs=2.0)
    assert res.best.total_net == pytest.approx(166518.0, abs=2.0)


def test_fallback_total_price_net_gross_pair_corrects_flip():
    """digital_twin-enrichment path: Pro now captures the PODSUMOWANIE pair into
    numeric card_summary.total_price_net + total_price_gross. The fallback must
    build BOTH as anchors so the brutto reading wins and the netto-label flip is
    corrected — same outcome as the _raw_price_lines pair, via aggregated fields."""
    card = {
        "base_price": "167 218.50 PLN netto",
        "options_price": "2 029.50 PLN netto",
        "service_equipment": {"net_amount": 85497.30},
        "discount": {"explicit_rabat_pln": 49928.16},
        "total_price_net": 166518.00,
        "total_price_gross": 204817.14,
        "_price_domain": "netto",
    }
    res = reconcile_prices(card, run_judge=False)

    assert res.verdict == "ok"
    assert res.source_domain == "brutto"
    assert res.best.total_gross == pytest.approx(204817.14, abs=2.0)


def test_parse_price_string_handles_polish_and_dot_decimals():
    assert ppr._parse_price_string("312 000,00 PLN brutto") == (312000.0, "brutto")
    assert ppr._parse_price_string("167 218.50 PLN netto") == (167218.5, "netto")
    assert ppr._parse_price_string("1 234,56")[0] == pytest.approx(1234.56)
    assert ppr._parse_price_string("") == (None, "unknown")


# ── LLM judge (mocked — no network) ──


def test_judge_disagreement_downgrades_ok_to_ambiguous(monkeypatch):
    """An 'ok' deterministic verdict flips to ambiguous (→ HITL) when the judge
    disagrees with the winning source domain. Numbers are never altered."""
    monkeypatch.setattr(
        ppr,
        "_judge",
        lambda best, paths, pdf_bytes, pdf_mime: {
            "agrees_with_winner": False,
            "chosen_source_domain": "netto",
            "reasoning": "PDF wskazuje netto",
            "confidence": 0.8,
        },
    )
    res = reconcile_prices(_bmw_154627(), pdf_bytes=b"%PDF-fake", run_judge=True)

    assert res.verdict == "ambiguous"
    assert res.warning is not None and res.warning["rule"] == "PRICE_RECONCILIATION_AMBIGUOUS"
    assert res.judge is not None and res.judge["agrees_with_winner"] is False
    # Deterministic numbers untouched by the judge.
    assert res.best.total_gross == pytest.approx(324115.0, abs=1.0)


def test_judge_agreement_keeps_ok(monkeypatch):
    monkeypatch.setattr(
        ppr,
        "_judge",
        lambda best, paths, pdf_bytes, pdf_mime: {
            "agrees_with_winner": True,
            "chosen_source_domain": "brutto",
            "reasoning": "Etykiety 'cena brutto z VAT' potwierdzają brutto",
            "confidence": 0.97,
        },
    )
    res = reconcile_prices(_bmw_154627(), pdf_bytes=b"%PDF-fake", run_judge=True)

    assert res.verdict == "ok"
    assert res.judge is not None and res.judge["agrees_with_winner"] is True


def test_judge_skipped_without_pdf_bytes(monkeypatch):
    """No PDF → no judge call (and no network), verdict stands."""
    monkeypatch.setattr(
        ppr, "_judge", lambda *a, **k: (_ for _ in ()).throw(AssertionError("judge must not run"))
    )
    res = reconcile_prices(_bmw_154627(), run_judge=True)  # pdf_bytes=None

    assert res.verdict == "ok"
    assert res.judge is None


# ── In-place flag contract (auto-run integration) ──


def test_reconcile_and_flag_mutates_card_on_ok():
    card = _bmw_154627()
    res = reconcile_and_flag(card, run_judge=False)

    assert res is not None and res.verdict == "ok"
    assert card["_reconciliation"]["verdict"] == "ok"
    assert card["_price_domain"] == "brutto"  # authoritative domain from the winner
    # ok → no blocking warning injected.
    warnings = (card.get("_validation") or {}).get("warnings") or []
    assert not any(w.get("rule", "").startswith("PRICE_RECONCILIATION") for w in warnings)


def test_reconcile_and_flag_appends_warning_on_ambiguous():
    card = {
        "_validation": {"warnings": []},
        "_raw_price_lines": [
            {"role": "base_price", "net_amount": 100000.0, "label": None, "vat_rate": 0.23},
            {"role": "total_price", "net_amount": 100000.0, "label": None, "vat_rate": 0.23},
        ],
    }
    res = reconcile_and_flag(card, run_judge=False)

    assert res is not None and res.verdict == "ambiguous"
    rules = [w["rule"] for w in card["_validation"]["warnings"]]
    assert "PRICE_RECONCILIATION_AMBIGUOUS" in rules
    assert "_price_domain" not in card  # ambiguous → don't assert a domain
