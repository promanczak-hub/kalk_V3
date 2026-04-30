"""Runner do uruchomienia eval-u na zbiorze realnych PDF-ow.

Uzycie:
    # Lokalnie (PDF-y w domyslnej lokalizacji Downloads):
    python -m eval.discount_eval.runner

    # Z customowym folderem:
    DISCOUNT_EVAL_PDF_DIR=/path/to/pdfs python -m eval.discount_eval.runner

    # Tylko jeden plik:
    python -m eval.discount_eval.runner --file OFERTA_nr_9142_2026_04_z_dnia_2026-04-02.pdf

Co robi:
1. Iteruje po `FIXTURES` (lista 14 ofert Ford Trakcja).
2. Dla kazdej: otwiera PDF, ekstrahuje tekst, buduje minimalny `card_summary` +
   `digital_twin` zgodny z tym co produkuje pipeline.
3. Wola `derive_discount_breakdown()` - to ten sam kod ktorego uzywa backfill
   produkcyjny.
4. Porownuje wynik z fixture (rabat_pln, computed_pct, non_discountable).
5. Drukuje tabele pass/fail i podsumowanie.

Brak zaleznosci od LLM ani Supabase.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure backend on path (when running as `python -m eval.discount_eval.runner`)
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from core.discount_backfill import derive_discount_breakdown  # noqa: E402
from eval.discount_eval.fixtures import FIXTURES, DiscountFixture  # noqa: E402

DEFAULT_PDF_DIR = Path("C:/Users/proma/Downloads")


def _build_synthetic_card_summary(fixture: DiscountFixture) -> dict:
    """Zbuduj minimalny `card_summary` ktory pipeline produkuje dla oferty Ford."""
    return {
        "base_price": f"{int(fixture.base_price)} PLN netto",
        "options_price": f"{int(fixture.factory_options_price)} PLN netto",
        "total_price": f"{int(fixture.cena_z_rabatem)} PLN netto",
        # paid_options puste - LLM tylko czasami je wypelnia. Pozwalamy backfillowi
        # polegac na regexie po digital_twin.
        "paid_options": [],
    }


def _read_pdf_text(pdf_path: Path) -> str:
    """Wyciagnij plain text z PDF-a uzywajac pymupdf (jak background_jobs.py)."""
    import pymupdf  # type: ignore

    doc = pymupdf.open(str(pdf_path))
    parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(parts)


def _build_digital_twin(pdf_text: str) -> dict:
    """Symulacja struktury `digital_twin` ktora trafia do `derive_discount_breakdown`."""
    return {"raw_text": pdf_text}


class EvalResult:
    def __init__(self, fixture: DiscountFixture, status: str, details: str = "") -> None:
        self.fixture = fixture
        self.status = status  # "PASS" | "FAIL" | "SKIP" | "ERROR"
        self.details = details


def evaluate_one(fixture: DiscountFixture, pdf_dir: Path) -> EvalResult:
    pdf_path = pdf_dir / fixture.file_name
    if not pdf_path.exists():
        return EvalResult(fixture, "SKIP", f"PDF nie znaleziony: {pdf_path}")

    try:
        pdf_text = _read_pdf_text(pdf_path)
    except Exception as e:
        return EvalResult(fixture, "ERROR", f"PDF read error: {e}")

    card_summary = _build_synthetic_card_summary(fixture)
    digital_twin = _build_digital_twin(pdf_text)

    breakdown = derive_discount_breakdown(card_summary, digital_twin)
    if breakdown is None:
        return EvalResult(fixture, "FAIL", "derive_discount_breakdown zwrocil None")

    issues: list[str] = []

    # Sprawdz rabat_pln (tolerancja 1 PLN)
    if breakdown.explicit_rabat_pln is None:
        issues.append("brak explicit_rabat_pln")
    elif abs(breakdown.explicit_rabat_pln - fixture.rabat_pln) > 1.0:
        issues.append(
            f"rabat_pln: oczekiwane {fixture.rabat_pln}, otrzymane {breakdown.explicit_rabat_pln}"
        )

    # Sprawdz computed_pct (tolerancja 0.5 pp)
    if breakdown.computed_pct is None:
        issues.append("brak computed_pct")
    elif abs(breakdown.computed_pct - fixture.expected_pct) > 0.5:
        issues.append(
            f"pct: oczekiwane {fixture.expected_pct}%, otrzymane {breakdown.computed_pct}%"
        )

    # Sprawdz extraction_method - dla Forda zawsze powinno byc explicit_amount
    if breakdown.extraction_method.value != "explicit_amount":
        issues.append(
            f"extraction_method: oczekiwane explicit_amount, otrzymane {breakdown.extraction_method.value}"
        )

    if issues:
        return EvalResult(fixture, "FAIL", "; ".join(issues))

    return EvalResult(
        fixture,
        "PASS",
        f"rabat={breakdown.explicit_rabat_pln:.0f} pct={breakdown.computed_pct}% "
        f"non_disc={breakdown.non_discountable_total_net or 0:.0f}",
    )


def run_eval(pdf_dir: Path, only_file: Optional[str] = None) -> int:
    fixtures_to_run = FIXTURES
    if only_file:
        fixtures_to_run = [f for f in FIXTURES if f.file_name == only_file]
        if not fixtures_to_run:
            print(f"Nie znaleziono fixture dla {only_file}")
            return 1

    print(f"\n{'='*100}")
    print(f"DISCOUNT EVAL — {len(fixtures_to_run)} fixtures, PDF dir: {pdf_dir}")
    print("=" * 100)
    print(f"{'STATUS':<8} {'FILE':<55} {'EXP_PCT':>8} {'EXP_NONDISC':>12} {'DETAILS'}")
    print("-" * 100)

    results: list[EvalResult] = []
    for fx in fixtures_to_run:
        res = evaluate_one(fx, pdf_dir)
        results.append(res)
        print(
            f"{res.status:<8} {fx.file_name[:55]:<55} {fx.expected_pct:>7.2f}% "
            f"{fx.expected_non_discountable:>12.0f} {res.details}"
        )

    print("-" * 100)
    counts = {s: sum(1 for r in results if r.status == s) for s in ("PASS", "FAIL", "ERROR", "SKIP")}
    print(
        f"PASS: {counts['PASS']}  FAIL: {counts['FAIL']}  "
        f"ERROR: {counts['ERROR']}  SKIP: {counts['SKIP']}"
    )

    return 0 if counts["FAIL"] == 0 and counts["ERROR"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default=os.environ.get("DISCOUNT_EVAL_PDF_DIR", str(DEFAULT_PDF_DIR)),
        help="Katalog z PDF-ami eval set",
    )
    parser.add_argument("--file", type=str, default=None, help="Pojedynczy plik z fixture")
    args = parser.parse_args()

    return run_eval(Path(args.pdf_dir), args.file)


if __name__ == "__main__":
    raise SystemExit(main())
