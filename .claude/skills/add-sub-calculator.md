---
name: add-sub-calculator
description: Add or replace a stage in the 12-step LTR pipeline. TDD-first with V1 parity test before code.
---

# Add a new LTRSubCalculator

## When to use

- New cost line to compute (e.g. depreciation insurance, new tax).
- Replacing an existing SubCalculator (e.g. `LTRSubCalculatorSerwisNew` succeeded `LTRSubCalculatorSerwis`).
- Re-implementing a V1 stage that wasn't yet ported.

## Prerequisites

- The V1 expected output for at least 2-3 vehicles (from `docs/audit/v1_calcreport_reference.md` or the legacy `LTRKalkulator.cs`).
- Knowledge of which DB tables/columns this stage reads (update [TABLE_REGISTRY.md](../../TABLE_REGISTRY.md) if introducing new ones).
- The stage's dependency position in the 12-step order (see CLAUDE.md).

## Steps

### 1. Write the parity test FIRST (RED)

```python
# backend/tests/test_v1_parity_stage_NN_<name>.py
import pytest
from core.LTRSubCalculatorXxx import XxxCalculator, XxxInput

def test_v1_parity_skoda_octavia_rs():
    inp = XxxInput(
        # ... V1 reference inputs
    )
    calc = XxxCalculator(inp)
    res = calc.calculate(months=48)
    assert res["monthly_xxx"] == pytest.approx(EXPECTED_V1_VALUE, rel=0.001)

def test_v1_parity_cupra_terramar():
    # second vehicle for distribution coverage
    ...
```

Existing pattern: `backend/tests/test_v1_parity_samar_rv.py`.

### 2. Stub the SubCalculator (test stays RED)

```python
# backend/core/LTRSubCalculatorXxx.py
from dataclasses import dataclass
from typing import Any

@dataclass
class XxxInput:
    # ... typed inputs
    pass

class XxxCalculator:
    def __init__(self, inp: XxxInput, settings: Any | None = None):
        self.inp = inp
        self.settings = settings

    def calculate(self, months: int) -> dict[str, float]:
        raise NotImplementedError  # test goes RED here
```

Add to `pipeline_price_validator`-style typing: mypy strict + ruff clean.

### 3. Implement until GREEN

- Read V1 logic. Port it line-by-line.
- For DB-dependent values, read from existing fetcher in `ltr_db_fetchers.py` — don't reach for `supabase.table(...)` ad-hoc.
- Watch the parity test go GREEN.

### 4. Wire into orchestrator

`backend/core/LTRKalkulator.py:Calculate()` — insert the call at the canonical position (see [CLAUDE.md](../../CLAUDE.md) 12-stage table for dependency ordering).

If stage produces outputs consumed by later stages (5-9 cascade or 10-12 aggregate), make sure dataflow is explicit — no global state, no monkey-patching.

### 5. Update PipelineDebugger

`backend/core/PipelineDebugger.py:calculate_steps()` — add the new stage to the returned list of 12 dicts so `diagnose-calculator-stage` skill works on it.

### 6. Update audit spec

Create or update `docs/audit/calc_NN_<name>.md` with formula, inputs, edge cases, V1 reference values.

### 7. Update CLAUDE.md table

Add the row to the 12-stage table in [CLAUDE.md](../../CLAUDE.md). Keep dependency arrows accurate.

## Verification

- `pytest backend/tests/test_v1_parity_stage_NN_*.py` all GREEN.
- `pytest` overall — no regressions in other parity tests.
- `mypy backend/core/LTRSubCalculatorXxx.py` clean.
- `ruff check backend/core/LTRSubCalculatorXxx.py` clean.
- File ≤400 LOC (CLAUDE.md hard rule). If longer, split.
- `PipelineDebugger.calculate_steps()` for a sample vehicle shows the new stage in the right position with sensible inputs/outputs.
- Reverse-search cache (`matrix_cache_job`) regenerated — old cached prices invalidated.

## Common pitfalls

- ❌ Writing the implementation before the test. The test pins V1 truth — if you reverse the order, you risk "fitting current code" rather than "matching V1".
- ❌ Reading DB tables outside `ltr_db_fetchers.py`. Concentrate I/O.
- ❌ Hard-coding brand-specific multipliers. Use DB tables (`samar_class_*`, `body_types`, `ltr_admin_*`).
- ❌ Adding `# type: ignore` to silence mypy. The 13 existing `# type: ignore` in LTRKalkulator.py are *legacy debt*, not a pattern to copy.
- ❌ Forgetting `matrix_cache_job` rerun — old cached prices won't reflect new stage.
