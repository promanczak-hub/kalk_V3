"""Pytest regression suite na realnym zbiorze 14 ofert Ford Trakcja.

Domyslnie pomijany jesli pliki nie znajduja sie w lokalizacji DISCOUNT_EVAL_PDF_DIR
(domyslnie C:/Users/proma/Downloads). To pozwala na szybki ci skip — testy
przechodza tylko jesli ktos lokalnie ma realne pliki.

Aby uruchomic na CI: ustaw DISCOUNT_EVAL_PDF_DIR i upewnij sie ze pliki sa dostepne.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from eval.discount_eval.fixtures import FIXTURES, DiscountFixture
from eval.discount_eval.runner import evaluate_one


def _pdf_dir() -> Path:
    return Path(os.environ.get("DISCOUNT_EVAL_PDF_DIR", "C:/Users/proma/Downloads"))


def _has_pdfs() -> bool:
    pdf_dir = _pdf_dir()
    if not pdf_dir.exists():
        return False
    return any((pdf_dir / fx.file_name).exists() for fx in FIXTURES)


pytestmark = pytest.mark.skipif(
    not _has_pdfs(),
    reason=(
        "Eval PDFs nie znalezione w DISCOUNT_EVAL_PDF_DIR. "
        "Ustaw zmienna srodowiskowa lub umiesc pliki w C:/Users/proma/Downloads"
    ),
)


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda fx: fx.file_name)
def test_real_pdf_discount_extraction(fixture: DiscountFixture) -> None:
    """Kazda oferta z fixture musi byc poprawnie zekstraktowana przez backfill.

    Jesli ktorykolwiek test FAIL — to znaczy ze regex/heurystyki sie zepsuly
    i prawdziwe oferty produkcyjne juz nie sa rozpoznawane prawidlowo.
    """
    pdf_dir = _pdf_dir()
    pdf_path = pdf_dir / fixture.file_name

    if not pdf_path.exists():
        pytest.skip(f"PDF nie znaleziony: {pdf_path}")

    result = evaluate_one(fixture, pdf_dir)

    if result.status == "ERROR":
        pytest.fail(f"Blad eval: {result.details}")

    assert result.status == "PASS", (
        f"Eval failed dla {fixture.file_name}: {result.details}\n"
        f"Oczekiwane: rabat={fixture.rabat_pln}, pct={fixture.expected_pct}%, "
        f"non_disc={fixture.expected_non_discountable}"
    )
