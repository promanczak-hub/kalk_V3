---
name: verify-extraction-output
description: Run Vertex/Gemini extractor on a test PDF and compare against expected JSON.
---

# Verify extraction output

## When to use

- After changing `backend/core/prompts.py` or extraction logic in `extractor_v2.py` / `extraction_pipeline/phase_*.py`.
- Investigating a specific PDF that produces wrong card_summary.
- Before merging a feature that touches the extraction pipeline.

## Prerequisites

- `.env` with Google GenAI credentials (Vertex AI / Gemini).
- A test PDF (reuse fixtures from `backend/tests/fixtures/` if present, or grab a known-good PDF from Supabase storage `raw-vehicle-pdfs`).
- Expected card_summary JSON (either committed alongside the fixture or a previous good run).

## Steps

### 1. Pick a fixture PDF + expected output

If none committed yet, do this:
- Run extraction on a PDF for a vehicle whose final calculation already matches V1 within tolerance — that's your "known good".
- Save PDF to `backend/tests/fixtures/extraction/<vehicle_id_short>.pdf` and expected JSON to `<vehicle_id_short>.expected.json`.

### 2. Run extraction in isolation

```python
# In a test file (NOT a fix_xxx.py script).
from backend.core.extractor_v2 import extract_vehicle_data_v2
from pathlib import Path

pdf_bytes = Path("backend/tests/fixtures/extraction/<id>.pdf").read_bytes()
result = extract_vehicle_data_v2(pdf_bytes, settings=...)
```

For progress / cancel testing, pass `on_progress` and `is_cancelled` callbacks (added 2026-03-04 per README changelog).

### 3. Run price validator

```python
from backend.core.pipeline_price_validator import validate_card_summary
report = validate_card_summary(result["card_summary"], settings)
assert report.is_valid, report.warnings
```

### 4. Diff vs expected JSON

```python
import json, deepdiff
expected = json.loads(Path("...expected.json").read_text())
diff = deepdiff.DeepDiff(expected, result, ignore_order=True, significant_digits=2)
assert not diff, diff
```

### 5. If divergence

- Don't update `expected.json` to silence the failure unless you intentionally improved extraction. If you do, commit the new expected alongside the prompt/code change with a `[CHANGED]` note in README changelog.
- If extraction got worse: fix `prompts.py` or `phase_2_mapping.py`, re-run. Don't accept regressions.

### 6. Run on adjacent fixtures

A prompt change is global — verify 3-5 other fixtures still pass. Add to CI if not already.

## Verification

- All fixture extractions match their expected JSONs within tolerance.
- `pipeline_price_validator` returns `is_valid=True` for all.
- New extraction features (voice extraction, saved filters — recent additions) don't break legacy fixtures.

## Common pitfalls

- ❌ Running extraction on production data without saving the input PDF. Without the PDF you can't reproduce.
- ❌ Updating `expected.json` to make tests pass. If extraction got *better*, document it. If it got *worse*, fix the regression.
- ❌ Skipping the price validator. LLM hallucinations slip through silent until reverse-search or a calculation triggers them.
- ❌ Adding fix scripts in `backend/scripts/`. The fix lives in `prompts.py` / `phase_2_mapping.py`.
