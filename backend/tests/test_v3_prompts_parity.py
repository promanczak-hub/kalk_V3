"""Parity test for V3 extraction pipeline vs legacy on 14 Ford Trakcja fixtures.

SKELETON — requires real Vertex AI / Gemini credentials and PDF fixtures.
Marked `pytest.mark.gemini` (a custom marker) so it runs only with
`pytest -m gemini` after setting `EXTRACTION_PROMPTS_V3=1` + Vertex auth.

Pre-flight required:
  1. `gcloud auth application-default login`
  2. `export GOOGLE_CLOUD_PROJECT=express-handlorz`
  3. Have 14 Ford fixture PDFs in backend/eval/discount_eval/pdfs/
  4. Run: `pytest -m gemini tests/test_v3_prompts_parity.py -v`

When the parity test passes (±0.5pp on `discount.computed_pct` for all 14),
it's safe to flip `EXTRACTION_PROMPTS_V3` to default `1`.

Outside of gemini-marked runs, the test is SKIPPED so CI stays green.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from eval.discount_eval.fixtures import FIXTURES, DiscountFixture

_PDF_DIR = Path(__file__).resolve().parent.parent / "eval" / "discount_eval" / "pdfs"
_PARITY_TOLERANCE_PP = 0.5  # percentage points


@pytest.fixture(autouse=True)
def _set_v3_env(monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROMPTS_V3", "1")


def _pdf_for_fixture(fx: DiscountFixture) -> Path:
    return _PDF_DIR / fx.file_name


@pytest.mark.gemini
@pytest.mark.parametrize("fx", FIXTURES, ids=lambda f: f.file_name)
def test_v3_pipeline_discount_pct_parity(fx: DiscountFixture) -> None:
    """V3 pipeline must produce discount.computed_pct within ±0.5pp of fixture."""
    pdf_path = _pdf_for_fixture(fx)
    if not pdf_path.is_file():
        pytest.skip(f"PDF fixture missing: {pdf_path}")

    if not os.environ.get("GOOGLE_CLOUD_PROJECT") and not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("Vertex AI / Gemini credentials not configured")

    from core.extractor_v2 import extract_vehicle_data_v2

    pdf_bytes = pdf_path.read_bytes()
    result_json = extract_vehicle_data_v2(pdf_bytes)
    result = json.loads(result_json)

    card = result.get("card_summary") or {}
    discount = card.get("discount") or {}
    computed_pct = discount.get("computed_pct")

    assert computed_pct is not None, f"V3 returned no computed_pct for {fx.file_name}"
    diff = abs(computed_pct - fx.expected_pct)
    assert diff <= _PARITY_TOLERANCE_PP, (
        f"{fx.file_name}: V3 computed_pct={computed_pct} differs from "
        f"expected {fx.expected_pct} by {diff:.2f}pp (tolerance {_PARITY_TOLERANCE_PP})"
    )
