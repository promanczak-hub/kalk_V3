---
name: diagnose-calculator-stage
description: Isolate which of the 12 LTR pipeline stages diverged from V1 reference output for a given vehicle.
---

# Diagnose a calculator stage divergence

## When to use

- A LTR calculation result looks wrong (Rata Netto, WR, ubezpieczenie, etc.) and you need to find **which of the 12 stages** is the culprit.
- A new vehicle (e.g. specific brand/model/trim) produces drift vs V1 (the legacy Excel/C# reference).
- You're about to write yet another `calc_xxx_debug.py` in `backend/scripts/` — STOP and use this skill instead.

This replaces the ad-hoc scripts: `diagnose_calculators.py`, `calc_tavascan.py`, `calc_tavascan2.py`, `calc_tavascan_debug.py`, `run_terramar_calc.py`, `find_v1_wr_terramar.py`, `verify_calc.py`, `check_terramar.py`.

## Prerequisites

- Backend env up (Poetry installed, `.env` configured for Supabase ONLINE).
- Redis + Celery NOT required for this — `PipelineDebugger` runs synchronously.
- A `vehicle_id` (UUID) from `vehicle_synthesis` or a fully-formed `LTRKalkulatorInput`.

## Steps

### 1. Get vehicle context

```python
# In a pytest test or a notebook scratchpad — NOT a new fix_X.py script.
from backend.core.ltr_db_fetchers import fetch_vehicle_input, fetch_settings
input_data = fetch_vehicle_input(vehicle_id="...")
settings = fetch_settings()
```

### 2. Run the step-by-step debugger

```python
from backend.core.PipelineDebugger import PipelineDebugger

dbg = PipelineDebugger(input_data, settings)
steps = dbg.calculate_steps(months=48, overrides={})  # 12 dicts: {step, name, inputs, outputs}
for s in steps:
    print(s["step"], s["name"], "→", s["outputs"])
```

`calculate_steps` returns 12 dicts: each has `step`, `name`, `inputs`, `outputs`. You can also override any step's input mid-run via the `overrides` dict (keys like `step_1_tires_base`, `step_1_tires_capex`).

### 3. Compare against V1 reference

Open `docs/audit/v1_calcreport_reference.md` and the per-stage spec [`docs/audit/calc_NN_*.md`](../../docs/audit/) for the stage you suspect. Compare:
- For WR stage: catalogue base (must be pre-discount full catalogue), depreciation curve, mileage correction, **then** additive color/body/zabudowa correction (Golden Rule — see CLAUDE.md).
- For Finanse: PMT formula inputs (CAPEX, WR, WIBOR, margin).
- For Ubezpieczenie: rate from `ltr_admin_ubezpieczenia`, damage coefficient from `ltr_admin_wspolczynniki_szkodowe`.

### 4. If divergence found in stage N

- Add a **parity test** in `backend/tests/test_v1_parity_stage_NN_<name>.py` that pins V1 expected vs current actual.
- Verify it goes RED with current code.
- Fix the SubCalculator. Verify it goes GREEN.
- DO NOT add a `fix_xxx.py` script — the fix goes in the actual SubCalculator + a regression test.

## Verification

- `pytest backend/tests/test_v1_parity_stage_NN_*.py` passes.
- For at least 2 other vehicles (different brand/class), `PipelineDebugger.calculate_steps()` output for the fixed stage stays within tolerance of V1.
- Run reverse-search query that hits this vehicle — price doesn't drift.

## Common pitfalls

- **Don't recompute prices in reverse-search.** The cache (`ltr_kalkulacje` + Redis) is source of truth. See CLAUDE.md "Reverse Search uses CACHE".
- **WR stage 5 corrections MUST be additive, not multiplicative.** `WR * (1 - korekta_pct)` is the bug pattern — drift on RS/Terramar.
- **`trim_level` does NOT override SAMAR class.** If you see "RS / GTI / AMG" branching, that's wrong root cause.
- **Steps 1-4 are independent.** If stage 1 (Opony) inputs into stage 5 (CenaZakupu via `tires_capex`), changing stage 1 ripples — debugger output shows this explicitly.
