---
name: fix-price-validator-mismatch
description: Debug `pipeline_price_validator` warnings — paid_options PLN-netto suffix drift, options_price aggregator duplicates.
---

# Fix a price-validator mismatch

## When to use

- `pipeline_price_validator` produces a `WARNING` or `ERROR` (see `ValidationWarning.severity`) after Vertex/Gemini extraction.
- `sum(paid_options) != declared options_price` (tolerance 0.2%).
- A single option exceeds 50% of base price (likely AI hallucination or mis-parsed line).
- Vehicle base price falls outside `[70_000, 3_000_000]` PLN range.

Memory note: `extractor_price_quirks` documents the two recurring root causes — `"PLN netto"` suffix mismatch and `service_equipment` duplicate aggregation.

## Prerequisites

- The card_summary JSON from extraction (find it in `vehicle_synthesis.card_summary` for the affected vehicle).
- `pipeline_price_validator.ValidationReport` output (already attached to row as `_validation`).

## Steps

### 1. Read the validation report

```python
from backend.core.pipeline_price_validator import validate_card_summary  # or similar entry point
report = validate_card_summary(card_summary, settings)
for w in report.warnings:
    print(w.severity, w.rule, w.message, w.expected, w.actual, w.diff_pct)
```

### 2. Classify the failure

| Rule | Likely cause | Fix location |
|---|---|---|
| `base_plus_options_mismatch` | LLM extracted a discount as negative option or merged two prices | `price_parser.py` parsing rules |
| `paid_options_sum_drift` | "PLN netto" suffix not stripped; or `service_equipment` aggregator double-counted | `price_parser.parse_price_string` |
| `single_option_too_large` | LLM took header row (subtotal) as an option | extraction prompt + `price_parser` filter |
| `unrealistic_base_price` | Wrong unit (PLN brutto vs netto, or thousands suffix dropped) | `price_parser` unit normalization |

### 3. Confirm root cause

- Don't write a `fix_X.py` script.
- Add a focused regression test in `backend/tests/test_price_validator.py` (already 53 KB — pattern is established).
- Make it RED with current parser. Fix `price_parser.py` / extraction prompt. Make it GREEN.

### 4. If the issue is the prompt (Vertex/Gemini)

- Update `backend/core/prompts.py` (currently in git status M).
- Re-run on the failing PDF via `verify-extraction-output` skill.
- Confirm new prompt doesn't regress other cases — run `pytest backend/tests/test_v1_parity_samar_rv.py` and any extraction test.

## Verification

- `pytest backend/tests/test_price_validator.py` passes (the new case + existing).
- Re-process the failing PDF — `ValidationReport.is_valid == True`.
- Spot-check 3-5 other recently-processed PDFs that previously passed — still pass.

## Common pitfalls

- ❌ Bumping `_SUM_TOLERANCE_PCT` to silence the warning. The tolerance is calibrated; warnings exist for a reason.
- ❌ "Fixing" by patching the card_summary post-validation. Fix the parser/prompt, not the data.
- ❌ Treating LLM output as authoritative. The validator runs because LLM extraction is fallible.
