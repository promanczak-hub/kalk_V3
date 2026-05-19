"""Multi-vehicle PDF split: 3 different vehicles → 3 separate digital twins.

SKELETON — requires real Gemini call + a multi-vehicle PDF fixture. Marked
`pytest.mark.gemini` so default `pytest` runs skip it.

To run:
  1. `gcloud auth application-default login`
  2. Put a 3-vehicle PDF at backend/eval/multi_vehicle/sample_3.pdf
     (e.g. VW Caddy 1.5 TSI + Caddy 2.0 TDI + Transporter 2.0 TDI from one offer)
  3. `pytest -m gemini tests/test_multi_vehicle_split.py -v`
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_MV_DIR = Path(__file__).resolve().parent.parent / "eval" / "multi_vehicle"
_SAMPLE_3 = _MV_DIR / "sample_3.pdf"


@pytest.mark.gemini
def test_three_vehicle_pdf_yields_three_twins() -> None:
    """PDF with 3 different vehicles must produce 3 vehicle_synthesis records."""
    if not _SAMPLE_3.is_file():
        pytest.skip(f"Multi-vehicle PDF fixture missing: {_SAMPLE_3}")
    if not os.environ.get("GOOGLE_CLOUD_PROJECT") and not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("Vertex AI / Gemini credentials not configured")

    from core.extraction_pipeline.phase_1_twins import process_multi_vehicle_phase

    pdf_bytes = _SAMPLE_3.read_bytes()
    twins = process_multi_vehicle_phase(pdf_bytes)

    assert isinstance(twins, list)
    assert len(twins) == 3, f"Expected 3 twins, got {len(twins)}"

    for idx, twin in enumerate(twins):
        synthesis = twin.get("synthesis_data") or {}
        card = synthesis.get("card_summary") or {}
        assert card.get("brand"), f"twin[{idx}] missing brand"
        assert card.get("model"), f"twin[{idx}] missing model"
        # base_price must be present and non-trivial
        base = (card.get("base_price") or "").lower()
        assert base and "brak" not in base, (
            f"twin[{idx}] has no base_price — MULTI_VEHICLE_TWIN_INCOMPLETE"
        )


@pytest.mark.gemini
def test_three_vehicle_pdf_validator_warnings_empty() -> None:
    """After 3-twin split, no MULTI_VEHICLE_TWIN_INCOMPLETE warning fires."""
    if not _SAMPLE_3.is_file():
        pytest.skip(f"Multi-vehicle PDF fixture missing: {_SAMPLE_3}")
    if not os.environ.get("GOOGLE_CLOUD_PROJECT") and not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("Vertex AI / Gemini credentials not configured")

    from core.extraction_pipeline.phase_1_twins import process_multi_vehicle_phase
    from core.pipeline_validator_v3 import check_multi_vehicle_twin_completeness

    pdf_bytes = _SAMPLE_3.read_bytes()
    twins = process_multi_vehicle_phase(pdf_bytes)

    # Extract just the card_summary from each twin for validator
    cards = [
        (t.get("synthesis_data") or {}).get("card_summary") or {}
        for t in twins
    ]
    warnings = check_multi_vehicle_twin_completeness(cards)
    assert warnings == [], (
        "Multi-vehicle extraction produced incomplete twins: "
        + json.dumps([w.to_dict() for w in warnings], ensure_ascii=False)
    )
