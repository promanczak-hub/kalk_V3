# Multi-hypothesis price reconciliation (4-path + LLM judge)

## Context

Single-shot LLM price deduction (`backend/core/pipeline_price_deduction.py`) is fragile.
On a textbook-clean BMW X5 offer (Oferta 154627, Inchcape) it mis-deduces because the
LLM is asked to *reconstruct* `base + Σoptions − rabat` and the document sets traps:

- **"Cena katalogowa" 390 500 ≠ vehicle base.** It's base (312 000) + options (78 500).
  The base line "CV41 … 312 000" sits on p.1, far from the totals block → LLM grabs the
  prominent "Cena katalogowa 390 500" as base AND re-sums options → double count.
- A **negative option** (ZMQ −400) and a dozen **0,00 bundled** options add noise.

The PDF itself is fully self-consistent and prints every authoritative number:

| Label (domain) | Amount |
|---|---|
| Cena katalogowa (brutto) | 390 500 |
| Upust | −66 385 |
| Total cena brutto z VAT | 324 115 |
| Cena całkowita netto (bez VAT) | 263 508,14 |

`390 500 − 66 385 = 324 115`; `324 115 / 1,23 = 263 508,14`. Everything cross-foots.

**Decision (user, 2026-05-21):** replace the single guess with a **multi-hypothesis
reconciliation engine** — generate-and-test, the way invoice-reconciliation pipelines
work. Compute the breakdown under 4 net/gross hypotheses *deterministically in Python*,
score each by how well it reproduces **every** labeled number in the PDF, pick the best.
LLM **judges** the winner against the PDF on **every** offer (second pair of eyes), but
**never does VAT arithmetic and never injects numbers** — it can only confirm or flag for
HITL. Runs **automatically after extraction** AND on-demand via the Audyt-ceny panel.

## Approach

### The 4 paths (2×2, user's "4 dedukcje")

Two axes the user named: components read as netto/brutto × final price netto/brutto.

| Path | Components | Final |
|---|---|---|
| P1 | netto | netto |
| P2 | netto | brutto |
| P3 | brutto | netto |
| P4 | brutto | brutto |

Each path computes a **full breakdown** (base → discountable/non-discountable options →
service → rabat → total, net+gross) using the existing `split()` logic.

### Scoring (the part that must be correct)

Residual = Σ over **all** labeled lines from the PDF (`_raw_price_lines`), each compared in
**its printed domain**: catalog, upust, total-netto, total-brutto, base, options-total.
A single anchor is insufficient — e.g. BMW's "everything netto" path numerically hits
324 115 but predicts gross 398 661 ≠ printed 324 115, so summing across the net/gross
**pair** kills the false match. Winner = lowest residual; plausibility penalties
(negative pool, options>catalog, net>gross) added. P4 wins for BMW with residual ≈ 0.

Renault Master (domain mislabeled `netto`): the brutto path wins on arithmetic and
**overrides** the wrong label — exactly the [[price-domain-flip-deduction]] case.

### LLM judge (always, but bounded)

After the deterministic winner is chosen, one Gemini-Flash call gets the PDF + the 4
computed paths + residuals and answers: **agree** / **disagree(+which, why)** / **uncertain**.
- agree → keep winner, high confidence.
- disagree or uncertain → emit `PRICE_RECONCILIATION_AMBIGUOUS` → HITL.
- Judge **cannot** change numbers (respects [[feedback_no_calc_fallbacks]] + LLM-bad-at-÷1,23).

### Verdict → HITL plumbing (reuse, don't reinvent)

`reconcile_prices` emits a `ValidationWarning`-shaped dict merged into
`card["_validation"]["warnings"]`; `_needs_hitl_review` already routes any rule in
`_HITL_BLOCKING_RULES` to `needs_review` ([phase_2_mapping.py:99-108](backend/core/extraction_pipeline/phase_2_mapping.py)).
New blocking rules: `PRICE_RECONCILIATION_FAILED` (no path within tol),
`PRICE_RECONCILIATION_AMBIGUOUS` (tie / judge disagrees). Verdict `ok` → no warning →
flows to `completed`. Authoritative `card["_price_domain"]` set from the winning path.

### Module API

```python
# backend/core/pipeline_price_reconciliation.py  (deterministic core + judge)
@dataclass(frozen=True)
class Hypothesis: source_domain: str; final_domain: str

@dataclass
class PathResult:
    hypothesis: Hypothesis
    base_net/gross, discountable_options_net/gross, non_discountable_options_net/gross,
    service_net/gross, rabat_net, total_net/gross: float
    residual_pln: float; penalties: float; score: float

@dataclass
class ReconResult:
    verdict: str                 # "ok" | "ambiguous" | "unreconcilable"
    best: PathResult; all_paths: list[PathResult]
    source_domain: str; judge: JudgeVerdict | None
    warning: dict | None         # ValidationWarning-shaped → _validation.warnings

def reconcile_prices(card_summary: dict, *, known: dict | None = None,
                     pdf_bytes: bytes | None = None, run_judge: bool = True) -> ReconResult
```

Input adapter `_extract_raw(card_summary, known)` prefers `card["_raw_price_lines"]`
(the stashed PASS-A corpus); falls back to aggregated triples + `paid_options` + discount
for legacy vehicles with no raw lines. Per-option discountable/non-discountable split is
carried for the calc + panel but does **not** change the reconciliation identity
(`base + Σoptions − discount = final`, full-catalog discount as dealers print it).
`discount_scope` reserved as a future axis for subset-discount PDFs.

## Phases (TDD: RED first)

1. **Deterministic core + tests** (no network). New module sans judge. Tests build
   `ExtractedRaw` from real numbers and assert the winner:
   - BMW 154627 → P4 (brutto/brutto), total_net 263 508,14 / gross 324 115, residual≈0, verdict ok.
   - False-match guard: assert netto-source path loses (predicts gross 398 661 ≠ 324 115).
   - Renault-style domain flip: label netto, brutto path wins (override).
   - Degenerate single-anchor doc → tie → verdict `ambiguous`.
2. **LLM judge** (`run_judge=True`), mocked in unit tests; one live smoke test.
3. **Stash raw lines:** `card["_raw_price_lines"]` before `return card`
   ([pipeline_normalization.py:237](backend/core/pipeline_normalization.py)).
4. **Auto integration:** call `reconcile_prices` right after `validate_and_flag_prices`
   ([extractor_v2.py:124](backend/core/extractor_v2.py) + multi-vehicle :181); write
   `_reconciliation`, set `_price_domain`, append warning. Add 2 rules to
   `_HITL_BLOCKING_RULES` ([phase_2_mapping.py:35](backend/core/extraction_pipeline/phase_2_mapping.py)).
5. **On-demand route:** `POST /extract/price-reconcile/{vehicle_id}` mirroring
   `price_deduce` load ([extract_routes.py:643](backend/api/extract_routes.py)). `price_confirm`
   stays authoritative for persistence.
6. **Panel:** `PriceAuditCard.tsx` + `types.ts` — render the 4 paths w/ residuals + verdict
   + judge note; wire re-run button. Retire `deduce_prices` once panel migrated.

## Critical files

- NEW `backend/core/pipeline_price_reconciliation.py` — engine + judge.
- NEW `backend/tests/test_price_reconciliation.py` — parity tests (BMW/Renault/false-match/tie).
- `backend/core/pipeline_normalization.py:237` — stash `_raw_price_lines`.
- `backend/core/extractor_v2.py:124,181` — auto-run seam.
- `backend/core/extraction_pipeline/phase_2_mapping.py:35` — new blocking rules.
- `backend/api/extract_routes.py:643,694` — new reconcile route; confirm unchanged.
- `frontend/src/VertexExtractor/components/VehicleTableParts/PriceAuditCard.tsx`, `../../types.ts`.
- Reference inputs: `RawPriceLine` ([extractor_models.py:821](backend/core/extractor_models.py)),
  validator entry `validate_and_flag_prices` ([pipeline_price_validator.py:195](backend/core/pipeline_price_validator.py)).

## Verification

- `poetry run pytest backend/tests/test_price_reconciliation.py` — RED→GREEN per phase.
- `poetry run ruff check . ; poetry run mypy .` clean.
- Two-way DB test: confirm a reconciled price, read it back, render in panel.
- Frontend: `npm run build` (tsc) clean; open Audyt-ceny on a `needs_review` vehicle,
  verify 4 paths + verdict render and re-run works.
- Regression: existing `test_price_validator.py`, `test_price_confirm_soften.py` stay green.

## Out of scope

- Re-extraction: reconciliation reuses PASS-A `raw_prices`, no new read LLM call (only the judge).
- Subset/percentage-discount reconciliation (`discount_scope` axis) — framework allows it; not built now.
- Changing the 12-stage calc's discount-pool logic ([[nondiscountable-factory-options]]) — unaffected.
- Backfilling `_raw_price_lines` for already-extracted vehicles — engine falls back to aggregated triples.
