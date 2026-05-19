# Strategic Fixes — 2026-05-19

Follow-up to [`fixes_applied_2026-05-19.md`](fixes_applied_2026-05-19.md), tackling the 8 items previously parked as "out of scope / multi-day":

## Summary

| # | Item | Status | Where |
|---|---|---|---|
| S1 | 11 missing tables in TABLE_REGISTRY.md | ✅ done (+4 service multipliers + ghost section) | [TABLE_REGISTRY.md](../../TABLE_REGISTRY.md) |
| S2 | Authorization review — `AUTH_ENABLED` + anon-key writes | ✅ done | [docs/SECURITY.md](../SECURITY.md) |
| S3 | Frontend code splitting — 5MB → 1.37MB initial (-73%) | ✅ done | `App.tsx`, `vite.config.ts`, `VehicleRowCard.tsx` |
| S4 | Sentry BE+FE + request_id correlation | ✅ done | `core/sentry_init.py`, `src/lib/sentryInit.ts`, `main.py`, `apiClient.ts`, `ErrorBoundary.tsx` |
| S5 | xlsx CVE — turned out unused; package removed (12→5 CVEs) | ✅ done | `frontend/package.json` |
| S6 | Refactor `LTRKalkulator.py` 1159 → **357 LOC** | ✅ done | new `core/ltr_cell_calculator.py` (488 LOC) |
| S7 | Split `scoring_search_routes.py` 2584 → **1995 LOC** | ⚠️ partial (helpers extracted, main router still big) | new `api/scoring_search_helpers.py` (629 LOC) |
| S8 | Frontend Vitest scaffolding — +19 tests | ✅ done | `apiClient.test.ts`, `sentryInit.test.ts`, `payloadBuilders.test.ts` |

---

## S1 — TABLE_REGISTRY.md completeness

Added the 11 missing tables flagged by Agent 4A-2 (`calculation_jobs`, `extraction_corrections`, `feature_aliases`, `ltr_offers`, `reverse_search_saved_filters`, `samar_brand_corrections`, `samar_class_options_rv`, `tab_okres_final`, `transport_fees`, `vehicle_features_summary_view`, `vehicle_matrix_cache`) **plus** 4 service multiplier tables that were also unregistered (`samar_service_brand/fuel/drive/gearbox_multipliers`). Backend + frontend touchpoints filled in based on grep verification.

Added a new "⚠️ Tabele OBSERWOWANE — bez aktywnych referencji" section listing 4 ghost tables (`samar_klasa_wr`, `ltr_admin_korekta_wr_markas`, `vehicle_feature_state`, `feature_import_runs`) — code-search came back empty. DB-side verification still owed.

## S2 — Authorization review

Created [`docs/SECURITY.md`](../SECURITY.md). Key points documented:

- `AUTH_ENABLED=false` by default → `get_current_user()` returns `None` → **every route is publicly callable**.
- Even at `AUTH_ENABLED=true`, no route uses `require_role()` → every authenticated user has identical privileges; the admin/operator/viewer split exists in code but is unwired.
- Frontend ships the Supabase **anon JWT** in the bundle and uses it for direct UPDATE/DELETE/INSERT on `vehicle_synthesis` from **16+ call sites** (including a `delete()` fallback in `VehicleRowCard.tsx:605`). All such writes rely entirely on Supabase RLS.
- Recommended hardening path is in §1.

## S3 — Frontend code splitting

`App.tsx` now uses `React.lazy()` + `Suspense` for the three top-level routes (`VertexExtractorPage`, `ScoringSearchPage`, `CalculationsHistoryPage`). `BrochureBuilderModal` is also lazy-loaded inside `VehicleRowCard.tsx` (only mounts when the user opens the brochure builder — eliminates the ~1 MB `@react-pdf/renderer` from the critical path for normal users).

`vite.config.ts` now defines `manualChunks` grouping vendor libs by purpose: `react-vendor`, `mui-vendor`, `pdf-vendor`, `grid-vendor`, `chart-vendor`, `framer-vendor`, `supabase-vendor`.

**Bundle math:**

| Chunk | Before | After |
|---|---|---|
| Initial JS shipped on `/` | 5,023 kB | ~1,372 kB (index 255 + react 49 + mui 416 + supabase 172 + VertexExtractorPage 481) |
| Cached PDF worker | 1,239 kB | unchanged (still lazy) |
| Initial reduction | — | **−73%** |
| Per-route incremental | n/a | CalculationsHistoryPage 8 kB, ScoringSearch 118 kB + chart-vendor 404 kB on first visit, brochure modal 20 kB + pdf-vendor 1,977 kB only when opened |

## S4 — Sentry integration

### Backend
- New [`core/sentry_init.py`](../../backend/core/sentry_init.py) — no-op when `SENTRY_DSN` unset. Integrations: `FastApiIntegration`, `CeleryIntegration`, `LoggingIntegration`. `before_send` scrubs request bodies, headers, query strings, and recursively redacts keys matching `password / token / secret / authorization / api_key / cookie`.
- `main.py` calls `init_sentry()` before FastAPI app creation.
- New `request_id_middleware` in `main.py`: generates / honours `X-Request-ID`, binds to structlog contextvars AND Sentry scope tag, echoes back in response header. Cross-cuts FE↔BE↔Celery.

### Frontend
- New [`src/lib/sentryInit.ts`](../../frontend/src/lib/sentryInit.ts) — no-op when `VITE_SENTRY_DSN` unset. `beforeSend` drops `request.data` + `request.cookies`. Uses `browserTracingIntegration` + `browserApiErrorsIntegration`.
- `src/main.tsx` calls `initSentry()` before mount.
- `ErrorBoundary.tsx` `componentDidCatch` now ships the error to Sentry (`Sentry.captureException` + `componentStack` extras), with a dynamic `import('./lib/sentryInit')` so the dependency is conditional.
- `apiClient.ts` now auto-attaches an `X-Request-ID` header on every fetch (using `crypto.randomUUID()`), honouring caller-supplied IDs.

Both ends scrub PII at the same layer; setting the DSN in both `backend/.env` and `frontend/.env.production` is now the only deployment step needed.

## S5 — xlsx CVE

The audit flagged `xlsx@0.18.5` (prototype pollution + ReDoS, **no upstream fix**) as needing a library migration. Investigation: `grep -rn "from 'xlsx'"` came back **empty** in `frontend/src/`. The only mention was a `/api/features/admin/${type}/import-xlsx` URL string. The package was installed transitively or as leftover — `npm uninstall xlsx` clean removed it. Result: 12 vulns → 5 (remaining 5 are all `vite/vitest/esbuild` dev-server CVEs, not production-shipped).

## S6 — LTRKalkulator refactor

Before: 1,159 LOC in one file. ~500 LOC of `build_matrix()` ↔ `build_reverse_search_matrix()` was 90 % copy-paste; VAT-parsing logic was duplicated 3×; engine + power validation 2×; 7 `print()` calls in the per-cell hot loop.

After:
- [`core/LTRKalkulator.py`](../../backend/core/LTRKalkulator.py): **357 LOC** — thin orchestrator (init, vehicle loading, override application, capex/WR pre-compute, public API)
- [`core/ltr_cell_calculator.py`](../../backend/core/ltr_cell_calculator.py): **488 LOC** — `calculate_cell()` + grid builders + helpers (`resolve_vat_multiplier`, `fetch_transport_fee_net`, `resolve_engine_and_power`, `build_grid_full`, `build_grid_reverse`)
- `CellContext` dataclass freezes per-call inputs so `calculate_cell()` stays pure and reusable
- `include_full_output: bool` toggle switches between the full UI/export shape and the minimal reverse-search shape (Okres/Przebieg/PrzebiegKontrakt/LacznaStawka)
- `print()` debug statements replaced with `logger.debug(...)` on a single line per cell
- Tests updated: `test_pipeline_debugger.py` + `test_golden_path_ltr_kalkulator.py` patch points moved from `core.LTRKalkulator.X` → `core.ltr_cell_calculator.X` where appropriate
- `PipelineDebugger.py` + `scripts/diagnose_calculators.py` updated to import the DB fetchers directly from `core.ltr_db_fetchers` (the canonical location), removing the implicit re-export through `LTRKalkulator`

**Verification:** all 14 critical tests pass in isolation (`test_v1_parity_samar_rv`, `test_golden_path_ltr_kalkulator`, `test_pipeline_debugger`, `test_service`). Pipeline behaviour is bit-for-bit identical — the refactor is purely structural.

## S7 — scoring_search_routes split (partial)

Before: 2,584 LOC. Extracted **~615 LOC of helpers** to [`api/scoring_search_helpers.py`](../../backend/api/scoring_search_helpers.py): normalisation (`normalize_transmission`, `normalize_drive_type`), Redis-down-tolerant cache (`redis_get`, `redis_set`, `params_hash`), coercion (`coerce_float`, `coerce_bool`), Supabase retry (`supabase_execute_with_retry`), snapshot fetcher (`fetch_kalkulacja_snapshot_params`, `attach_kalkulacja_snapshot_to_matches`), price parsing (`resolve_price_domain`, `parse_price_numeric`, `parse_price_to_net`, `parse_price_pair`), option line item extraction (`extract_option_line_items`), similar-vehicle row builder (`build_similar_vehicle_match`), body-style + candidate ID resolution (`resolve_candidate_vehicle_ids`), `percentile`, `parse_numeric`. Constants `VAT_RATE`, `TTL_*`, `BODY_TYPE_FIELDS`, `PRESENT_STATUSES` also moved.

Routes file now imports each as `from api.scoring_search_helpers import X as _X` so the in-file callsite naming stays stable.

**Result:** `scoring_search_routes.py` 2584 → 1995 LOC; `scoring_search_helpers.py` 629 LOC.

**Still open:** the giant `/scoring-search/search` endpoint (~750 LOC by itself) is the main reason routes is still big. Splitting that into `scoring_search_similar.py` + `scoring_search_prices.py` + `scoring_search_snapshot.py` is the natural next pass — out of scope here because each move requires a careful test-redirection (the existing tests patch fully-qualified module paths).

**Verification:** all 8 redis-cache tests + critical pipeline tests pass after updating 3 monkeypatch targets to also patch `api.scoring_search_helpers._get_client` (the alias rebinding subtlety — `from X import Y` captures Y by value at import time).

## S8 — Vitest scaffolding

Added 19 new tests across 3 files:

### `src/lib/apiClient.test.ts` — 13 tests (was 0)
Most-imported FE module, untested pre-refactor. Coverage:
- URL prefixing (relative vs absolute)
- Content-Type defaults (JSON vs FormData)
- X-Request-ID auto-attach + caller override (S4 wiring)
- ApiError construction from 4xx/5xx with parsed `detail` / `message` / FastAPI validation array
- Fallback to `response.statusText` for non-JSON error bodies
- `skipGlobalError` flag bypasses Zustand `setGlobalError`
- `timeoutMs` aborts hung requests with the Polish timeout message
- Caller-supplied AbortSignal recognised as manual abort (no global error)

### `src/lib/payloadBuilders.test.ts` — 3 new tests (was 2 with `@ts-nocheck`)
Removed `@ts-nocheck`, kept types strict in the test itself. Added:
- `pricingMarginPct` override preserved outside `base_cost_only` mode
- Extra fields via index signature survive the spread
- Input not mutated

### `src/lib/sentryInit.test.ts` — 3 tests (was 0)
- Returns `false` and skips `Sentry.init` when `VITE_SENTRY_DSN` is missing
- Reads environment + release env vars when DSN is set
- `beforeSend` strips `request.data` + `request.cookies` (S4 PII contract)

Total Vitest count: **58 passed / 58 total** (was 39 / 39).

---

## What's open after this pass

Items the audit listed as strategic and that genuinely need more than the morning:

- **LTRKalkulator `print()` removal in callers** — `LTRKalkulator.py` itself is clean now, but `calculation_service.py` (12 prints), `samar_mapper.py` (9), and `extract_routes.py` (13) still log via `print()` instead of structlog.
- **scoring_search_routes.py main `/search` endpoint** — still 750 LOC inside one function. Splitting requires extracting filter resolution, query building, and result post-processing into a dedicated `scoring_search_query.py`.
- **Authorization rollout** — flipping `AUTH_ENABLED=true` requires the FE to attach Bearer tokens (apiClient is now extensible enough to add this, but `supabaseClient.ts` direct calls bypass apiClient entirely → §S2 §3 must be tackled first).
- **RLS policy review** — out of scope for code; needs Supabase SQL access.
- **Frontend Vitest expansion** — apiClient, payloadBuilders, sentryInit covered. Still untested: 14 React components, all HITLWizard pieces, MatrixHeatmapView, ReversePriceLookup. Each is its own multi-test investment.

## Verification commands

```powershell
# Backend tests (use --reruns from earlier session to absorb Windows port flakes)
cd backend; poetry run pytest --tb=no -q
# Frontend tests
cd frontend; npx vitest run
# Frontend build (verifies code splitting kicks in + check chunk sizes)
cd frontend; npm run build
# Frontend lint (verifies no new any/non-null issues introduced)
cd frontend; npm run lint
# Supply-chain
cd frontend; npm audit
```
