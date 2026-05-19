# Full Codebase Audit — kalk_v3

**Date:** 2026-05-18
**Method:** 35 read-only Explore agents (1 mapping + 15 backend drill + 12 frontend drill + 6 cross-cutting + 1 retry) + empirical local toolchain run
**Scope:** entire repo (`backend/` + `frontend/` + `docs/` + config + `.github/`)
**Total findings:** ~210 (28 CRITICAL · 67 HIGH · ~90 MEDIUM · ~25 LOW)

---

## 1. Executive Summary

The kalk_v3 codebase is **operationally functional** but has accumulated significant technical debt and a few **production-impacting issues** that should be addressed urgently. The 12-stage LTR calculation pipeline is mostly compliant with the 2503 SOT and CLAUDE.md "Golden Rule" for WR — all eight CRITICAL anti-patterns in CLAUDE.md show **zero violations**. Domain logic is solid.

**Critical exception:** The V1 parity test that CLAUDE.md cites as the authoritative WR validator — `test_v1_parity_samar_rv.py::test_skoda_octavia_rs_v1_parity` — is currently **FAILING** alongside 4 other tests. This contradicts the read-only agent reports (which examined code, not runtime) and is the single most important finding to triage.

**Top 5 actions for today:**

1. **Investigate 5 failing pytest tests** (especially `test_v1_parity_samar_rv` — golden WR validator)
2. **Fix XSS** in `JsonViewerModal.tsx` and `VehicleComparisonModal.tsx` (`dangerouslySetInnerHTML` with unsanitized user/AI-supplied content)
3. **Remove hardcoded `postgres` password** in `backend/scripts/add_insurance_params.py:14`
4. **Upgrade axios** `1.13.5 → 1.16.1` (CVEs: SSRF via NO_PROXY, prototype pollution, CRLF injection)
5. **Strip stack traces from HTTP 500 responses** in `extract_routes.py:1215` (information disclosure to clients)

---

## 2. Empirical Baseline (Phase 5)

Local toolchain results — these are **ground truth** and supersede agent assumptions.

| Tool | Result | Detail |
|---|---|---|
| `pytest` | **5 FAIL** / 575 pass | See § 2.1 |
| `ruff check` | **38 errors** | Mostly `F541` (f-string no placeholder), `F841` (unused var), `F401` (unused import), `E722` (bare except) |
| `mypy` | **16 errors** | Missing type stubs (psycopg2, openpyxl, pymupdf4llm, dateutil) + dual-module ambiguity for `eval/discount_eval/fixtures.py` |
| `npm run lint` | **56 errors / 5 warnings** | Mostly `@typescript-eslint/no-explicit-any` |
| `npm run build` | ✅ built (22s) | **JS bundle: 5,023 kB** (warning: >500 kB threshold). `pdf.worker.min.mjs`: 1,239 kB. CSS: 356 kB. No code splitting. `apiClient.ts` and `config/env.ts` both statically + dynamically imported — defeats `import()` chunking. |
| `npm audit` | 12 vulnerabilities (9 moderate, 3 high) | See § 7 |
| `poetry check` | PASS | |

### 2.1 Failing tests (block release until resolved)

```
FAILED tests/test_golden_path_ltr_kalkulator.py::test_golden_path_standard_car
FAILED tests/test_pipeline_debugger.py::test_pipeline_debugger_no_overrides_matches_kalkulator
FAILED tests/test_pipeline_debugger.py::test_pipeline_debugger_with_override
FAILED tests/test_service.py::TestServiceCalculator::test_fake_brand_multiplier_falls_back_to_neutral
FAILED tests/test_v1_parity_samar_rv.py::test_skoda_octavia_rs_v1_parity
```

The last is referenced in CLAUDE.md as the **authoritative WR parity validator** (expected `61 046,00 PLN brutto`). PipelineDebugger no-override test failing means the debugger output diverges from the orchestrator — a regression in trace consistency.

---

## 3. CRITICAL Findings (28)

### 3.1 Failing tests / data correctness

| # | Issue | Where | Why critical |
|---|---|---|---|
| C-01 | V1 parity FAILS | [test_v1_parity_samar_rv.py](backend/tests/test_v1_parity_samar_rv.py) | CLAUDE.md "Golden Rule" validator broken |
| C-02 | PipelineDebugger diverges from LTRKalkulator | [test_pipeline_debugger.py](backend/tests/test_pipeline_debugger.py) | Debug surface lies about live calc state |
| C-03 | Golden path standard car fails | [test_golden_path_ltr_kalkulator.py](backend/tests/test_golden_path_ltr_kalkulator.py) | Baseline lease calc broken |
| C-04 | Service multiplier neutral-fallback regression | [test_service.py](backend/tests/test_service.py) | Memory `feedback_service_multipliers_neutral` rule broken |

### 3.2 Security (immediate)

| # | Issue | Where | Why critical |
|---|---|---|---|
| C-05 | Traceback in HTTP 500 JSON response | [extract_routes.py:1215](backend/api/extract_routes.py) | Information disclosure (internal paths, function names) |
| C-06 | Hardcoded `postgres` password | [add_insurance_params.py:14](backend/scripts/add_insurance_params.py) | Credential in repo; no `__main__` guard |
| C-07 | XSS via `dangerouslySetInnerHTML` (JSON highlight) | [JsonViewerModal.tsx:227](frontend/src/VertexExtractor/components/JsonViewerModal.tsx) | Unsanitized `<mark>` injection from regex |
| C-08 | XSS via `dangerouslySetInnerHTML` (markdown) | [VehicleComparisonModal.tsx:117-119](frontend/src/VertexExtractor/components/VehicleComparisonModal.tsx) | Custom MD parser without sanitization |
| C-09 | SSRF in `/api/pdf-proxy` | [extract_routes.py:868-895](backend/api/extract_routes.py) | Fetches arbitrary URLs without validation |
| C-10 | Prompt injection — PDF text into Gemini system prompt | [prompts.py](backend/core/prompts.py) + [pipeline_digital_twin.py:259-261](backend/core/pipeline_digital_twin.py) | Attacker-controlled PDF can override instructions |
| C-11 | Anon JWT used for `UPDATE`/`DELETE`/`INSERT` on `vehicle_synthesis` | 9+ sites; e.g., [VehicleRowCard.tsx:605](frontend/src/VertexExtractor/components/VehicleTableParts/VehicleRowCard.tsx), [useVehicles.ts:254-256](frontend/src/VertexExtractor/hooks/useVehicles.ts) | RLS is the only gate; one mis-policy = data corruption |
| C-12 | `axios 1.13.5` known CVEs | [package-lock.json](frontend/package-lock.json) | SSRF (NO_PROXY bypass), proto pollution, CRLF injection — fix: `axios@1.16.1` |
| C-13 | `xlsx 0.18.5` proto pollution + ReDoS, no fix available | [package.json](frontend/package.json) | Must audit usage / sanitize input or migrate |
| C-14 | `AUTH_ENABLED` toggle disables ALL auth globally | [auth_middleware.py:21-30](backend/core/auth_middleware.py), [main.py:33](backend/main.py) | One env-var flip = no auth on any route |

### 3.3 Frontend data loss / state corruption

| # | Issue | Where | Why critical |
|---|---|---|---|
| C-15 | Save without read-back (silent server reject) | [PricingPanel.tsx:96-104](frontend/src/ManualKalkulacje/PricingPanel.tsx) | Violates CLAUDE.md two-way (round-trip) test mandate at FE layer |
| C-16 | Negative price not validated | [PricingPanel.tsx:147-149](frontend/src/ManualKalkulacje/PricingPanel.tsx) | HTML5 `min=0` only; backend not enforced in FE code path |
| C-17 | Orphan `vehicle_id` navigation crashes | [CalculationsHistoryPage.tsx:305-306](frontend/src/CalculationsHistory/CalculationsHistoryPage.tsx) | Memory says orphan is "feature, not bug" — but FE has no error handling |
| C-18 | No error UI on PATCH/POST failure | [PricingPanel.tsx:96-103](frontend/src/ManualKalkulacje/PricingPanel.tsx), [extract_routes async](backend/api/extract_routes.py) | Try/catch swallows; user thinks "saved" |
| C-19 | `useAppStore ↔ apiClient` circular runtime coupling | [apiClient.ts:96](frontend/src/lib/apiClient.ts), [useAppStore.ts:2](frontend/src/stores/useAppStore.ts) | Hidden error propagation; hard to test in isolation |
| C-20 | `offerCartStore` persisted state has no migration handler | [offerCartStore.ts:76-128](frontend/src/stores/offerCartStore.ts) | Schema change → silent corruption on rehydrate |

### 3.4 Pipeline / extraction correctness

| # | Issue | Where | Why critical |
|---|---|---|---|
| C-21 | Confidence score loss on HITL apply | [extract_routes.py:660-836](backend/api/extract_routes.py) | All corrections set `confidence=1.0`; original extraction confidence lost |
| C-22 | HITL apply not idempotent | [extract_routes.py apply endpoint](backend/api/extract_routes.py) | Two saves diverge state |
| C-23 | Hallucinated fields NOT auto-removed | [HITLWizardDialog.tsx:205-217](frontend/src/VertexExtractor/components/HITLWizard/HITLWizardDialog.tsx) | Only warning shown; user can promote hallucination to confidence=1.0 |
| C-24 | Stale `card_summary` reference after AI mapping | [phase_2_mapping.py:211](backend/core/extraction_pipeline/phase_2_mapping.py) | Exception between line 211 and 369 → wrong data persisted |
| C-25 | Silent JSON parse failure crashes multi-vehicle loop | [phase_1_twins.py:76-95](backend/core/extraction_pipeline/phase_1_twins.py) | One bad vehicle → all subsequent skipped, orphan rows |
| C-26 | Phase 2 persists DB twice with divergent state | [phase_2_mapping.py:456-472](backend/core/extraction_pipeline/phase_2_mapping.py) | No transaction; partial retry overwrites prior save |
| C-27 | `phase_2_mapping.py` exceeds 400 LOC (617) | [phase_2_mapping.py](backend/core/extraction_pipeline/phase_2_mapping.py) | Hard rule violation in critical path |
| C-28 | Direct `psycopg2` UPDATE bypasses RLS | [extract_routes.py:238-278](backend/api/extract_routes.py) `_direct_update_synthesis()` | Built-in workaround for "PostgREST default schema = reverse_search" issue; bypasses RLS entirely |

---

## 4. HIGH Findings (67)

### 4.1 Backend API & pipeline

- **[H-01]** [LTRKalkulator.py:741-757](backend/core/LTRKalkulator.py) — 7 `print(f"[DEBUG_LTR_*]")` calls in per-cell hot loop (212-cell grid × 7 = 1484 stdout lines/request)
- **[H-02]** [LTRKalkulator.py:354-881 vs 883-1159](backend/core/LTRKalkulator.py) — ~500 LOC of `build_matrix()` vs `build_reverse_search_matrix()` is ~90% copy-paste. Extract `_calculate_cell()` helper.
- **[H-03]** [LTRKalkulator.py:508-517](backend/core/LTRKalkulator.py) — Comment says "Instantiate RV calculator once" but actually creates `LTRSubCalculatorUtrataWartosciNew(...)` per cell
- **[H-04]** [LTRKalkulator.py:485-493, 491-493, 727-729](backend/core/LTRKalkulator.py) — VAT rate resolution code duplicated 3×
- **[H-05]** [LTRKalkulator.py:559-589, 1004-1026](backend/core/LTRKalkulator.py) — Engine + power validation duplicated; broad `except Exception:` swallows real DB timeouts
- **[H-06]** [kalkulacje_routes.py:903-1029](backend/api/kalkulacje_routes.py) — `smart-advisor` calls `build_matrix()` **3×** without caching (perf regression contradicting CLAUDE.md cache rule)
- **[H-07]** [oferty_routes.py:64](backend/api/oferty_routes.py) `VAT_RATE = 1.23` hardcoded (also in `scoring_search_routes.py:288`)
- **[H-08]** [oferty_routes.py:148-164](backend/api/oferty_routes.py) `_TRANSMISSION_BRAND_PATTERNS` hardcoded regex dict (should be DB-driven)
- **[H-09]** Stage 4 (Serwis) — **missing "Przeglądy Podstawowe" (basic inspections)** from V1, causes underbilled service contracts; see [LTRSubCalculatorSerwisNew.py](backend/core/LTRSubCalculatorSerwisNew.py) vs [calc_04_serwis.md](docs/audit/calc_04_serwis.md) L167-180
- **[H-10]** Stage 2 (KosztyDodatkowe) — `ElementyRyczałtowe` + `KosztZabudowy` from V1 silently ignored (no error, no log); see [calc_02_koszty_dodatkowe.md](docs/audit/calc_02_koszty_dodatkowe.md)
- **[H-11]** `samar_service_brand/fuel/drive/gearbox_multipliers` tables used in stage 4 (`LTRSubCalculatorSerwisNew.py:474-485`) but **missing from TABLE_REGISTRY.md**
- **[H-12]** Stage 4 — `normatywny_przebieg_mc` hardcoded default `1666` instead of reading `control_center` ([LTRSubCalculatorSerwisNew.py:130-136](backend/core/LTRSubCalculatorSerwisNew.py))
- **[H-13]** Stage 11 (Stawka) — Python `round()` (banker's) vs V1 `Math.Ceiling()` → ±1 PLN drift per contract ([LTRKalkulator.py:769](backend/core/LTRKalkulator.py))
- **[H-14]** Stage 6 (samar_rv) — debug key `krok4_active` doesn't match CLAUDE.md spec `krok4_korekta_disabled_per_sot`; one test asserts the spec name, code emits another
- **[H-15]** `pipeline_price_validator.py` self-healing treats null `options`/`rabat` as 0, can pass a bogus `base = total` ([pipeline_price_validator.py:259-386](backend/core/pipeline_price_validator.py))
- **[H-16]** `pipeline_card_summary.py` Few-Shot injection does NOT de-dupe `extraction_corrections` rows; duplicates inflate tokens and may conflict ([pipeline_card_summary.py:570-602](backend/core/pipeline_card_summary.py))
- **[H-17]** `PipelineDebugger.py` HTML renderer doesn't escape `step.metadata`/`step.trace` dict values (XSS if user input in trace) ([PipelineDebugger.py:677-776](backend/core/PipelineDebugger.py))
- **[H-18]** [PipelineDebugger.py:270-368](backend/core/PipelineDebugger.py) — WR can go negative if `czynsz_inicjalny > residual_value`; no `max(0, …)` guard
- **[H-19]** [composite_body_style.py:39-54](backend/core/composite_body_style.py) — Unmapped cabin variant + LLM fallback fail = silent `None` (breaks `rental_vehicle.body_style`)

### 4.2 Extraction / HITL

- **[H-20]** `PaidOption.price` is STRING ("2750 PLN netto"); deterministic price-domain override in `extractor_v2.py:62-77` can't correct per-option ([extractor_models.py:304-338](backend/core/extractor_models.py))
- **[H-21]** `prompts.py` price-domain detection scans only explicit netto/brutto keywords, misses parenthetical markers like "ceny w branży (netto)"
- **[H-22]** [phase_2_mapping.py:24-44](backend/core/extraction_pipeline/phase_2_mapping.py) `_HITL_CONFIDENCE_THRESHOLD = 0.7` hardcoded; should be `control_center` setting
- **[H-23]** [phase_2_mapping.py:248-261](backend/core/extraction_pipeline/phase_2_mapping.py) — mHEV preservation guard is fragile; multiple re-tries can diverge
- **[H-24]** [phase_2_mapping.py:478-492](backend/core/extraction_pipeline/phase_2_mapping.py) — Nested field precedence is undocumented (`card_summary` vs `parsed_data` vs `mapped_data`)
- **[H-25]** HITL zabudowa bucket reassignment drops `price_type` / `vat_rate` / `category` ([extract_routes.py:790-800](backend/api/extract_routes.py))
- **[H-26]** HITL preview stale under rapid edits (400ms debounce, no version stamp) ([useHITLWizard.ts:255-282](frontend/src/VertexExtractor/hooks/useHITLWizard.ts))
- **[H-27]** Drag-drop bucket: unassigned-items zone not droppable, silent failure ([BucketZone.tsx](frontend/src/VertexExtractor/components/HITLWizard/BucketZone.tsx))
- **[H-28]** Supabase Realtime opens HITL dialog before data ready (race) ([useHITLWizard.ts:316-339](frontend/src/VertexExtractor/hooks/useHITLWizard.ts))

### 4.3 Infrastructure

- **[H-29]** [matrix_cache_job.py:528-535](backend/core/matrix_cache_job.py) — Partial chunk failure marks job "failed" but leaves cells partially cached, no rollback
- **[H-30]** [matrix_cache_job.py 696 LOC](backend/core/matrix_cache_job.py) exceeds 400 LOC
- **[H-31]** [enrichment_tasks.py:322-429](backend/tasks/enrichment_tasks.py) — Backfill calls `_do_generate_embeddings()` with NO retry on Vertex 429/500
- **[H-32]** [matrix_tasks.py:31, 51](backend/tasks/matrix_tasks.py) — Tasks `.raise()` on exception; with `task_reject_on_worker_lost=True` + no max-retries = **infinite retry loop** for permanent errors
- **[H-33]** [celery_app.py](backend/core/celery_app.py) — `REDIS_URL` falls back to `127.0.0.1:6379/0`; production silently uses localhost on missing env
- **[H-34]** [ltr_vehicle_resolvers.py:129-146](backend/core/ltr_vehicle_resolvers.py) — `_resolve_samar_class_id_from_name()` fetches full `samar_classes` table on every call despite `@redis_cache` decorator
- **[H-35]** `extract_routes.py:267` — `db_url = f"postgresql://postgres:{password}@db.{ref}.supabase.co:5432/postgres"` — password baked into URL string
- **[H-36]** `extract_routes.py:239` — comment claims PostgREST default schema is `reverse_search` (ignoring `Content-Profile: public`); whole `_direct_update_synthesis()` workaround built on this assumption — needs prod verification

### 4.4 Tests

- **[H-37]** 18 of 47 test files mock the database (CLAUDE.md anti-pattern); worst offenders: [test_samar_rv.py:32-94](backend/tests/test_samar_rv.py), [test_hitl_endpoints.py:103-118](backend/tests/test_hitl_endpoints.py), [test_golden_path_ltr_kalkulator.py:82-120](backend/tests/test_golden_path_ltr_kalkulator.py)
- **[H-38]** Zero tests for `phase_0_router.py`, `phase_1_twins.py`, `matrix_cache_job.py`, `scoring_search_routes.py`
- **[H-39]** 11 route files lack dedicated test files (`features_admin`, `homologation`, `body_types`, `param_preview`, `semantic`, `admin`, `ltr_manual`, `kalkulacje`, `oferty`, …)
- **[H-40]** [test_debug.py:3](backend/tests/test_debug.py) is `assert True` (pure dummy)
- **[H-41]** [test_v1_parity_samar_rv.py:13](backend/tests/test_v1_parity_samar_rv.py) — execution-order dependent (monkeypatches Redis cache; comment notes ~1664 PLN brutto divergence if run after other tests)
- **[H-42]** Hardcoded golden numbers without external spec citation (`expected_rv_gross = 63076.20`, `Excel Baseline ~3298 → V3 Baseline 4574`)
- **[H-43]** Frontend tests: 9 E2E + 39 Vitest for 157 source files (0.03 ratio); [audit.spec.ts](frontend/tests/e2e/audit.spec.ts) asserts `expect(true).toBe(true)` — useless for CI

### 4.5 Frontend perf / quality

- **[H-44]** **JS bundle 5,023 kB** + pdf.worker 1,239 kB + CSS 356 kB, **no code splitting** ([vite.config.ts](frontend/vite.config.ts))
- **[H-45]** No `React.lazy()` anywhere; routes all eager-loaded
- **[H-46]** `apiClient.ts` + `config/env.ts` both statically AND dynamically imported → defeats `import()` chunking (vite build warning)
- **[H-47]** MatrixHeatmapView re-computes margin for all cells every render ([MatrixHeatmapView.tsx:272-274, 201, 353-354](frontend/src/CalculatorPanel/MatrixHeatmapView.tsx))
- **[H-48]** [OfferCartDrawer.tsx:24](frontend/src/components/OfferCart/OfferCartDrawer.tsx) `OVERUSE_FEE_OPTIONS` not memoized; recreated per render
- **[H-49]** AG Grid + MUI X DataGrid both installed; only AG Grid used (~150 kB dead weight)
- **[H-50]** [VertexExtractorPage.tsx:108-129](frontend/src/VertexExtractor/VertexExtractorPage.tsx) — Direct Supabase reads of 4 lookup tables with no error recovery, no fallback
- **[H-51]** [VehicleCalculationsList.tsx:247-248](frontend/src/VertexExtractor/components/VehicleTableParts/VehicleCalculationsList.tsx) — Auto-select on every silent refresh can overwrite user's manual selection
- **[H-52]** Currency formatting inconsistent across `VehicleTableParts/` (some `1234,56 PLN`, others `1234,56 zł`, others no space)
- **[H-53]** [VehicleEquipmentCard.tsx:96](frontend/src/VertexExtractor/components/VehicleTableParts/VehicleEquipmentCard.tsx) — Cell edits not persisted on blur; user can lose changes if forgets to click Save
- **[H-54]** [VertexExtractorPage.tsx:232](frontend/src/VertexExtractor/VertexExtractorPage.tsx) — File upload no MIME validation, no size limit, no filename sanitization
- **[H-55]** 9+ direct frontend `.update()` calls on `vehicle_synthesis` table with no server-side validation (see § C-11)
- **[H-56]** [useVehicleFinancing.ts](frontend/src/VertexExtractor/hooks/useVehicleFinancing.ts) — 8× `as any` on `synthesis_data` (schema not strongly typed)
- **[H-57]** [VehicleResultCard.tsx](frontend/src/ScoringSearch/components/Results/VehicleResultCard.tsx) — 84 non-null assertions (highest single-file count); fragile null safety
- **[H-58]** No global error boundary covers async errors / unhandled rejections; `ErrorBoundary` only catches render-time
- **[H-59]** [vehicleMappings.ts](frontend/src/VertexExtractor/utils/vehicleMappings.ts) — `ALL_SAMAR_CLASSES` / `ALL_ENGINE_TYPES` hardcoded; last sync `2026-03-18`, 2 months stale, no runtime validation
- **[H-60]** [useVehicleFeaturesCache.ts:28-44](frontend/src/VertexExtractor/hooks/useVehicleFeaturesCache.ts) — Unbounded queue growth if feature fetches fail
- **[H-61]** [BrochureBuilderModal.tsx](frontend/src/VertexExtractor/components/brochure/BrochureBuilderModal.tsx) — `@react-pdf/renderer` imported globally; blocks main thread, no lazy-load or Web Worker

### 4.6 Config / docs / observability

- **[H-62]** CLAUDE.md, README.md, ARCHITECTURE.md all reference `poetry run python run_dev.py` — **file does not exist**; actual entry is `backend/main.py`
- **[H-63]** ARCHITECTURE.md line 26 claims `main.py` AND `run_dev.py` both exist (latter doesn't)
- **[H-64]** CLAUDE.md "400 LOC max" notes only `LTRKalkulator.py` as debt; actual count is **31 files** > 400 LOC
- **[H-65]** CLAUDE.md "Where things live" missing 6 dirs: `backend/services/`, `backend/eval/`, `backend/output/`, `backend/scratch/`, `backend/templates/`, `backend/intercepted_data/`
- **[H-66]** TABLE_REGISTRY.md missing 11 tables actively used in code (incl. `calculation_jobs`, `extraction_corrections`, `ltr_offers`, `samar_brand_corrections`, `samar_class_options_rv`, `tab_okres_final`, `transport_fees`, `vehicle_matrix_cache`, `vehicle_features_summary_view`, `feature_aliases`, `reverse_search_saved_filters`)
- **[H-67]** `docs/audit/calc_02-12.md` 11/12 specs last touched 2026-03-05 (>2 months stale); only `calc_01_opony.md` refreshed 2026-05-17

---

## 5. MEDIUM Findings (selected, grouped thematically)

### 5.1 Error swallowing
- 29 instances of broad `except Exception:` in `backend/core/` + `backend/api/`. Worst offenders: `scoring_search_routes.py` (7), `ltr_vehicle_resolvers.py` (3), `extractor_v2.py` (3), `brochure_mapper.py` (2), `LTRKalkulator.py` (2)
- 286 `print()` in backend (scripts OK; concerning in prod code: `extract_routes.py:13`, `parser_routes.py:6`, `calculation_service.py:12`, `samar_mapper.py:9`, `LTRKalkulator.py:9`)
- 93 `console.*` calls across 39 frontend files (heaviest: `useVehicleMetaManager.ts:11`, `useVehicles.ts:8`, `useVehicleDataSync.ts:7`)

### 5.2 Type weakness
- `frontend/src/VertexExtractor/types.ts:72` — `[key: string]: any` on `FleetVehicleView`
- `frontend/src/lib/apiClient.ts:7, 13` — `data?: any` on `ApiError`
- 342 non-null assertions (`!`) across 68 files; localized to post-guard patterns mostly
- 25 `as any` / 44 `:any` annotations; mainly around `synthesis_data` access
- `frontend/src/lib/payloadBuilders.test.ts:1` — `@ts-nocheck` (the only one)

### 5.3 Code duplication
- `parsePriceToNumber()` duplicated in `PriceDualFormat.tsx` and `calculations.utils.ts`
- VAT-rate resolution duplicated 3× in `LTRKalkulator.py` + once in `LTRSubCalculatorUtrataWartosciNew.py`
- `_supabase_execute_with_retry()` duplicated in `kalkulacje_routes.py` + `scoring_search_routes.py`
- `normalize_transmission()` + `normalize_drive_type()` duplicated `scoring_search_routes.py` ↔ `oferty_routes.py`
- `compute_matrix_breakdown` recomputes per-item in `oferty_routes.py:976` (offer generation), opposite of cache rule

### 5.4 Sensitive artifacts in git
- `database_dump_2026-03-12.sql` (8.3 MB) — DB dump committed
- `_archive/test_out.txt` (20.8 MB) — test artifact, `_archive/` is .gitignore'd but this file pre-dates
- `kalk_v3_claude_pack.zip` (9 MB)
- `backend/dummy.pdf` (3.1 MB), `backend/passat_test.pdf` (933 kB), `backend/kolor_tab.png`, `screenshot1.png` (1.2 MB), `screenshot2.png`
- `backend/intercepted_data/zapytanie_*.txt` — verified: ONLY Google search autocomplete data (no OAuth tokens; prior agent worry was unfounded)
- `scripts/tmp_old_calc.py`, `scripts/tmp_old_wrapper.py` — UTF-16 orphan tmp files

### 5.5 Tests / coverage
- Coverage matrix (BE): 12/12 calc stages have tests; 11/16 route files lack tests; 3/3 extraction phases lack tests; matrix_cache_job has zero tests
- Coverage matrix (FE): critical flows untested — PDF→extraction→HITL→save, reverse search, matrix selection, manual kalk save, offer cart export
- Two stage-4 test files: `test_finanse.py` + `test_finance.py` — naming conflict, unclear which is canonical

### 5.6 Design system fragmentation
- `ConfirmModal.tsx` uses Tailwind exclusively; rest of app uses MUI `sx`. ConfirmModal will look wrong if MUI theme switches mode
- Dark mode hardcoded to `"light"` in `App.tsx:257`; conditional dark styles in code are dead
- `tailwind.config.ts` doesn't exist (Tailwind v4 defaults only); no shared theme with MUI palette
- `FieldLabel.tsx:16` hardcodes `color: "#333"` instead of theme variable

### 5.7 Polish/English naming
- URLs mix Polish (`/kalkulacje`, `/oferty`) and English (`/scoring-search`, `/calculate-matrix`) without documented policy
- ~60-80 hardcoded Polish UI strings; no i18n framework (i18next, react-intl)
- `MASTER_PROMPT_V2` + `FALLBACK_STRUCTURED_PROMPT_FLASH` are all-Polish system prompts
- Field naming: BE Polish snake_case; FE local camelCase converted in `payloadBuilders.ts:26-44` — boundary undocumented at file top
- Class status enums hardcoded Polish: `szkic_vertex`, `w_opracowaniu`, `gotowa`, `wyslana`, `archiwum`

### 5.8 Dependencies
- `google-genai` 11 minor versions behind (`1.64.0 → 2.4.0`)
- `cryptography` 2 minor behind (`46.0.5 → 48.0.0`)
- `@mui/material` + `@mui/icons-material` 1 MAJOR behind (`v7 → v9`); v8 skipped
- Supabase JS 8 minor behind (`2.98.0 → 2.106.0`); Python/JS Supabase wildly out of sync
- `recharts` 1 MAJOR behind
- esbuild dev-server CVE (transitive via vite/vitest); `npm audit fix` available
- `postcss < 8.5.10` XSS; `npm audit fix`
- `uuid 13.0.0`, `ws 8.*`, `brace-expansion`, `follow-redirects` — all transitive, all fixable via `npm audit fix`

### 5.9 Observability
- `structlog` configured with JSON output + correlation IDs, but `generate_correlation_id()` never called from middleware → orphan
- No `X-Request-ID` header anywhere; can't trace user action across FE→BE→Celery→DB
- Celery tasks don't propagate trace IDs; can't filter logs by `vehicle_id`
- No Sentry / Datadog / OpenTelemetry integration; all logs go to stdout only
- No frontend performance monitoring (LCP, INP, FID)

---

## 6. LOW Findings (counts only)

- ~12 Tailwind/MUI minor inconsistencies
- ~15 dead props / unused vars (caught by ruff F841, eslint no-unused-vars)
- ~10 stale comments / outdated dates
- 1 unowned TODO (`LTRSubCalculatorKosztyDodatkowe.py:84` — `Mock — czynsz za czas przygotowania do sprzedaży`)
- 2 frontend TODOs (`SimilarVehiclesPanel.tsx:518, :618` — both non-user-facing per agent)
- Various naming inconsistencies (folder `/CalculatorSections/` plural vs `/OptionsManager/` singular, etc.)

---

## 7. Systemic Patterns (cross-cutting)

These themes appeared in 3+ independent agent reports — promote them in any refactor plan:

| Pattern | Where it shows up | Recommended fix |
|---|---|---|
| **Broad `except Exception:` swallowing real errors** | API routes, LTRKalkulator, extraction pipeline, scripts | Replace with specific exception types; add structured log with `request_id` + context before re-raise |
| **Hardcoded constants that should be DB-driven** | `VAT_RATE = 1.23` ×2, `_HITL_CONFIDENCE_THRESHOLD = 0.7`, `normatywny_przebieg_mc = 1666`, `MIN_VALID_BASE_PRICE`, margin thresholds in `MatrixHeatmapView` | Move to `control_center` EAV table (already the SOT adapter) |
| **Code duplication >100 LOC** | `build_matrix`↔`build_reverse_search_matrix`, VAT helpers, `_supabase_execute_with_retry`, price/transmission normalizers | Extract shared helpers in `backend/core/utils.py` (currently doesn't exist for common code) |
| **Direct FE→Supabase writes bypassing FastAPI** | 9+ sites on `vehicle_synthesis` table | Route through dedicated API endpoints; add Pydantic validation; preserve audit trail |
| **No two-way (round-trip) test after writes** | FE save flows, BE direct psycopg2 update | After every `update`/`insert` in tests AND in FE save handlers, read record back and assert shape |
| **Missing observability context** | No request_id, no trace_id, no Sentry, no per-task vehicle_id binding | Single-day investment yields 10× faster triage |
| **Stale or missing docs** | run_dev.py mythical file, 6 undocumented dirs, 11 missing TABLE_REGISTRY tables, 11/12 calc specs >2mo stale | Doc-as-code discipline; CI gate that fails on doc drift |

---

## 8. Quick Wins (<30 min each)

1. **Delete** `scripts/tmp_old_calc.py`, `scripts/tmp_old_wrapper.py` (UTF-16 orphans)
2. **Add to `.gitignore`**: `*.sql` (except `supabase/migrations/`), `*.png` (except `public/`), `*.pdf` (test PDFs), `backend/intercepted_data/`
3. **Fix `run_dev.py` reference** in CLAUDE.md, README.md, ARCHITECTURE.md (replace with actual `main.py` command)
4. **`npm audit fix`** — covers postcss XSS, brace-expansion DoS, uuid buffer, ws memory disclosure, follow-redirects header leak
5. **Remove `@mui/x-data-grid`** from `package.json` — unused, ~150 kB
6. **Delete `test_debug.py`** (1-line assert True)
7. **Convert top-5 print() → logger** in `extract_routes.py`, `LTRKalkulator.py`, `calculation_service.py`
8. **Add `--Confirm:$false` or env-driven password** to `add_insurance_params.py` OR delete the script
9. **`npm install axios@1.16.1`** — fixes 16 CVEs
10. **Replace `expect(true).toBe(true)`** in `audit.spec.ts` with proper assertions (or delete)
11. **Rename debug key** `krok4_active` → `krok4_korekta_disabled_per_sot` (or update CLAUDE.md spec) so test/code/spec agree
12. **Lazy-load `@react-pdf/renderer`** in BrochureBuilderModal (`React.lazy(() => import('@react-pdf/renderer'))`) — saves ~1.2 MB initial
13. **Memoize `OVERUSE_FEE_OPTIONS`** outside component
14. **Add `Content-Security-Policy` + `X-Frame-Options`** middleware in `main.py`
15. **Rewrite top-3 ruff F541 / F841** in scripts (5 min each)

---

## 9. Strategic Items (multi-day projects)

### 9.1 Stop the bleeding (1-2 days)
- **Triage 5 failing tests** — start with `test_v1_parity_samar_rv` (golden validator). Run `pytest -x --tb=long tests/test_v1_parity_samar_rv.py` and follow the trace. Likely culprit: a refactor in samar_rv.py / samar_rv_fetchers.py between 2026-05-15 (memory `body_types_sot` consolidation) and today.
- **Patch CRITICAL security holes** — XSS (2 sites), SSRF (`/pdf-proxy`), prompt injection (PDF text into prompts), traceback disclosure

### 9.2 Reliability investment (3-5 days)
- **Add request_id middleware + Sentry** (backend Python SDK + frontend React SDK)
  - Backend: `pip install sentry-sdk[fastapi,celery]`, init in `main.py`, attach to structlog context
  - Frontend: `@sentry/react`, wrap `ErrorBoundary`, capture unhandled rejections
- **Add Celery task tracing** — propagate `vehicle_id` + `request_id` as task kwargs, log structured

### 9.3 Test recovery (1 week)
- **Replace DB mocks with real-DB integration tests** for top-5 most-mocked files (CLAUDE.md mandate)
- **Add tests for `phase_0_router`, `phase_1_twins`, `matrix_cache_job`, `scoring_search_routes`** — these are critical paths with zero coverage
- **Fix execution-order dependency** in `test_v1_parity_samar_rv.py`
- **Add frontend Vitest unit tests** for `apiClient`, `payloadBuilders`, top-3 hooks
- **Replace dummy E2E assertions** with real outcome checks

### 9.4 Architecture (2-4 weeks)
- **Refactor `LTRKalkulator.py` 1159 LOC → ~400** by extracting `_calculate_cell()` helper (eliminates ~400 LOC duplication)
- **Split `scoring_search_routes.py` 2584 LOC** into ~4 modules: search/filters/results/comparison
- **Split `pipeline_price_validator.py` 1391 LOC** into `price_domain_detector.py` + `price_self_healer.py` + rule registry
- **Frontend code splitting**: `React.lazy()` per route; lazy-load PDF renderer and AG Grid; target 1.5 MB initial bundle (down from 5 MB)
- **Migrate 9 direct FE→Supabase writes** to backend endpoints
- **Add Zod schema validation** at FE-BE boundary for top-5 payloads (start with `vehicle_synthesis` shape)

### 9.5 Documentation (1 week)
- **Refresh `docs/audit/calc_02-12.md`** specs (11 files, 2+ months stale)
- **Add 11 missing tables to TABLE_REGISTRY.md** + add `Owner` column + spot-check FE touchpoints
- **Update CLAUDE.md** "Where things live" with 6 missing dirs
- **Document i18n strategy** (or commit to single language)
- **Document FE↔BE naming convention** (Polish snake_case BE / camelCase FE conversion layer)

---

## 10. What Was NOT Audited (honest limits)

- **Runtime profiling** — no actual load test, no flame graph, no real perf baseline (only bundle size + static smell analysis)
- **Supabase RLS policies** — agents read the code, not the DB; "anon JWT for UPDATE" CRITICAL findings ASSUME RLS could be misconfigured
- **Gemini prompts in production** — no real-world prompt injection attack attempted
- **Browser test of actual UI** — agents read code; no Playwright `preview_*` verification of the actual user flow
- **Mobile / responsive layout** — not assessed
- **Accessibility (WCAG)** — only spot-checked; no full audit
- **Performance regression vs prior versions** — no historical baseline
- **CI/CD pipeline (`deploy.yml`, `ci.yml`)** — only mentioned, not deep-read
- **`backend/core/feature_enrichment.py` (1218 LOC)** + **`backend/api/features_routes.py` (1140 LOC)** + **`backend/api/oferty_routes.py` (1069 LOC)** — covered at high level by 2A-1 but not line-by-line
- **`backend/eval/discount_eval/`** — surface-touched only

---

## 11. Compliance Scorecard

| CLAUDE.md rule | Status | Notes |
|---|---|---|
| AI LOCKOUT: no DELETE/DROP/TRUNCATE on Supabase ONLINE | ✅ COMPLIANT | Only `sync_service_multipliers.py` + `import_serwis_baza.py` use TRUNCATE/DELETE, both manual-only |
| 400 LOC max per file | ❌ 31 violations | Includes `scoring_search_routes.py` 2584, `pipeline_price_validator.py` 1391, `LTRKalkulator.py` 1159, `extract_routes.py` 1266 |
| Two-way (round-trip) test for DB writes | ❌ Inconsistent | FE save flows lack readback; 18/47 backend tests mock DB |
| 12-stage canonical order | ✅ COMPLIANT | Per agent 2A-2 deep read of LTRKalkulator.py |
| Golden Rule WR (2503 SOT) | ⚠️ MOSTLY COMPLIANT | Code paths correct per agent 2B-2; HOWEVER golden parity test FAILS (C-01) — investigate why |
| Reverse Search uses CACHE | ✅ COMPLIANT | Per agent 3B-2; no `_calc_exact_price` recreations found |
| No hardcoded brand multipliers | ✅ COMPLIANT | DB-driven via `samar_service_*_multipliers` tables |
| No `trim_level` overriding SAMAR class | ✅ COMPLIANT | trim_level used for matching/display only |
| No mocking DB in tests | ❌ 18 violations | Anti-pattern widespread |
| No recreating `_calc_exact_price` | ✅ COMPLIANT | No matches |
| No `control_center` wide-row reads | ✅ COMPLIANT | All access via `core/control_center.py` adapter |
| No fix_X/repair_X script proliferation | ✅ COMPLIANT | Only 1 `repair_vehicle_metadata.py` (acceptable) |
| Never bypass TABLE_REGISTRY for renames | ⚠️ PARTIAL | 11 tables in code missing from registry — bypass already happened silently |
| Never commit to master with 100+ uncommitted files | ⚠️ CURRENTLY | 46 changes uncommitted on master (31 mod + 12 add + 3 untracked) |

---

## 12. Appendix: Agent Reports Index

Generated by 35 read-only Explore agents in 4 waves:

- Phase 1 — Mapping (1 agent)
- Wave 1 (9 agents): Backend API routes, LTRKalkulator deep read, Pipeline support, 12-stage parity ×3, Extractor core, Extraction phases, HITL wizard
- Wave 2 (6 agents): Celery infra, DB layer & services, Scripts audit, Test coverage, Anti-pattern hunt, Security audit
- Wave 3 (12 agents): VertexExtractor flow ×3, Calculator+Matrix, ScoringSearch, ManualKalk+History, Zustand stores, apiClient+lib, Shared components, TS strictness, Frontend tests, Frontend perf
- Wave 4 (6 agents): Doc drift, TABLE_REGISTRY cross-check, Dead code & orphans, Dependency audit, Naming consistency, Observability

Phase 5 — Empirical toolchain (pytest, ruff, mypy, eslint, vite build) ran in parallel with Wave 1.

Each agent received: scope file list, CLAUDE.md anti-pattern list, relevant memory excerpts, severity rubric, output format spec. Output budgets were enforced (500-700 words per agent) so reports are dense.

---

*Audit generated 2026-05-18. Findings are point-in-time; the codebase is actively changing (46 files uncommitted at start of audit). Re-run before any major release.*
