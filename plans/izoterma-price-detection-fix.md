# Izoterma price-detection fix — capture net/gross pair + offer-total semantics

## Context
Test upload of `izoterma_EX.pdf` (Renault Master, vehicle `3612dff1-…`) exposed a compound
price-detection failure. Reconciliation engine (`pipeline_price_reconciliation.py`) is correct
and unit-tested (12 green) but was starved of inputs on the live vehicle.

## Findings (evidence-backed)
1. **Stale container.** On-disk engine resolves the live card (ok/netto, base 167218.5); the
   deployed `kalk_v3-backend-1`/`celery_worker` stored all-zeros/ambiguous. They predate the
   reconciliation string-fallback + `_raw_price_lines` stash + v3 Pass A raw extraction.
   Live card has only `digital_twin.pricing` (3 bare "zł" numbers), `raw_prices`=null.
2. **Pass A never captures the PODSUMOWANIE pair.** `pipeline_raw_extraction.py:39` (Gemini Pro,
   schema `RawExtractionResult`); prompt = `prompts_v3/compose.py:26` (`frame.py` + auto field
   docs). `RawPriceLine.role` (`extractor_models.py:830-836`) is a singular `total_price`, no
   instruction to emit one line per labeled total. Legacy `prompts.py:100` framing "total_price =
   ostateczna cena **pojazdu**" leaks in. `_aggregate_role` (`pipeline_normalization.py:109`)
   takes the FIRST match per role → never builds a net+gross pair.
3. **izoterma-specific: vehicle-price-vs-offer-total.** PODSUMOWANIE prints vehicle netto 166 518 /
   brutto 204 817,14. Components (base 167 218,50 + options 2 029,50 + zabudowa 85 497,30 =
   254 745,30) don't sum to it. Extraction grabbed the vehicle brutto (204 817,14) as the whole-
   offer netto total → `discount` (computed_from_total = 49 928,16) is poisoned. `FULL_SUM_INTEGRITY`
   already flags this → `needs_review` (correct safety net). Even with the pair captured, izoterma
   may legitimately stay HITL unless the PDF prints a clean whole-offer net/gross total.

## Approach (3 layers, ordered)
### A. Safe code (no network, reversible) — DO FIRST (TDD RED→GREEN)
- **Test (RED):** reconciliation fixture WITH a net/gross total pair → assert engine corrects a
  CLEAN flip (label says netto, brutto path wins). New `_aggregate_role` test: two labeled
  `total_price` lines (netto + brutto) → populate BOTH `total_price_net` and `total_price_gross`.
- **Revise** `test_fallback_includes_service_equipment_zabudowa` — it currently codes the flipped
  reading (204817.14 netto) as correct. Either assert the corrected pair, or relabel it as the
  "single-anchor, no pair → accepts label" degenerate case (honest about what it tests).
- **Fix** `_aggregate_role` (`pipeline_normalization.py:109`): when multiple lines share a role,
  pick net-labeled → `_net`, gross-labeled → `_gross` (not first-match).

### B. Extraction prompt/schema (broad impact, Gemini-risky, needs re-extraction to validate)
- Instruct Pass A: when a summary prints netto+VAT+brutto, emit TWO `total_price` `RawPriceLine`s
  (label="netto", label="brutto"). Edit `RawPriceLine.role` description
  (`extractor_models.py:830-836`) + reinforce in `prompts_v3/frame.py`.
- Clarify `total_price` = WHOLE-OFFER total (vehicle + all options + zabudowa + services), NOT the
  vehicle price — to address the izoterma vehicle-vs-offer confusion.
- Risk: mind `additionalProperties` / "too many states" (memory). Cannot unit-test the LLM emitting
  two lines — only the downstream aggregation/reconciliation. Validate via re-extraction.

### C. Rebuild + e2e (action on user's stack — confirm before restart)
- `docker compose build` + restart `kalk_v3-backend-1` + `celery_worker`.
- Re-run `hitl_smoke_upload` izoterma; assert `raw_prices` populated, `_raw_price_lines` stashed,
  reconciliation verdict matches on-disk. izoterma may still land `needs_review` (acceptable if the
  PDF lacks a clean offer-total pair — that's the HITL safety net working).

## Verification
- `poetry run pytest tests/test_price_reconciliation.py tests/test_normalization_pipeline.py` green.
- `poetry run ruff check . ; poetry run mypy .` clean.
- e2e: rebuild, re-upload izoterma, two-way DB read of the reconciliation verdict.

## Out of scope
- Auto-resolving the vehicle-vs-offer-total semantics beyond capturing the pair + prompt clarity;
  if the PDF doesn't print a clean offer-total, HITL stays the answer.
- The frontend role-split (already shipped: PriceAuditCard PDF-only, DiscountAuditCard owns rabat).
