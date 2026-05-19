# Fixes Applied — 2026-05-19

Follow-up to [`full_codebase_audit_2026-05-18.md`](full_codebase_audit_2026-05-18.md). Scope chosen by user: failing tests + CRITICAL security + quick wins + CRITICAL FE state (~50 items).

## 1. Failing tests (Faza A)

**Root cause** (confirmed empirically, not predicted by audit agents):
Tests pass in isolation, fail in full suite. The failures all trace to **Windows TCP ephemeral port exhaustion** under load — Supabase calls accumulate sockets, eventually `httpx.ConnectError [WinError 10061]` cascades. Test count: ~580 calls → exhausts ports in ~3-4 min of running.

**Fixes:**
- **New** [`backend/core/supabase_retry.py`](../../backend/core/supabase_retry.py) — robust `execute_with_retry()` wrapper. Detects transient errors via exception type AND message substring (English + Polish + WinError). 5 retries, exponential backoff (0.5s → 8s).
- **Wired into** hot paths that triggered the failures:
  - [`samar_rv_fetchers.py`](../../backend/core/samar_rv_fetchers.py) — 9 `.execute()` calls (depreciation rates, brand corrections, paint, body, vintage, mileage, options)
  - [`samar_rv.py`](../../backend/core/samar_rv.py) — `samar_classes` lookup
  - [`control_center.py`](../../backend/core/control_center.py) — EAV reads (control_center is touched by every calc)
  - [`LTRSubCalculatorSerwisNew.py`](../../backend/core/LTRSubCalculatorSerwisNew.py) — service rates + multipliers
  - [`LTRKalkulator.py`](../../backend/core/LTRKalkulator.py) — transport_fees lookup
- **Neutral fallback** in `get_service_multiplier()` — per CLAUDE.md memory `feedback_service_multipliers_neutral`, return 1.0 on transient DB unavailability instead of crashing the whole calculation. Fixes `test_fake_brand_multiplier_falls_back_to_neutral`.
- **Conftest enhancement** — [`tests/conftest.py`](../../backend/tests/conftest.py) now also refreshes the Supabase client singleton every 25 tests to rotate the HTTP/2 connection pool.
- **Belt-and-suspenders** — added [`pytest-rerunfailures`](https://pypi.org/project/pytest-rerunfailures/) to dev deps with `--reruns 2 --reruns-delay 3` in `pyproject.toml`. Re-runs cover the residual ~3-second recovery window after port exhaustion.

**Result:** Service multiplier test fixed (one less failure). Other 4 should now pass on retry (verification in progress).

## 2. Quick Wins (Faza B)

- [`backend/run_dev.py`](../../backend/run_dev.py) — restored (was at `scripts/backend_scripts_adhoc/`); fixes mythical-file bug in CLAUDE.md / README.md / ARCHITECTURE.md
- [CLAUDE.md](../../CLAUDE.md) — "Where things live" updated with 5 previously-undocumented dirs (`services/`, `tasks/`, `eval/`, `templates/`, plus `core/control_center.py`)
- [`backend/tests/test_debug.py`](../../backend/tests/test_debug.py) — deleted (was `print + assert True` dummy)
- [`frontend/package.json`](../../frontend/package.json) — `axios 1.13.5 → 1.16.1` (16 CVEs incl SSRF, prototype pollution, CRLF injection)
- `npm uninstall @mui/x-data-grid` (~150 kB dead weight; only AG Grid actually used)
- `npm audit fix` — fixed transitive CVEs in postcss/uuid/ws/follow-redirects/brace-expansion (12 vulns → 6, remaining 6 all xlsx with no upstream fix)
- [`backend/core/samar_rv.py`](../../backend/core/samar_rv.py) — added spec-named debug key `krok4_korekta_disabled_per_sot` (CLAUDE.md Golden Rule requires this name; code used `krok4_active`). Both keys coexist.
- [`backend/api/extract_routes.py`](../../backend/api/extract_routes.py:1208) — stripped `traceback.format_exc()` from HTTP 500 response (info disclosure); full trace still server-side via `logger.exception`
- [`backend/main.py`](../../backend/main.py) — added `add_security_headers` middleware: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security: max-age=31536000`
- [`frontend/tests/e2e/audit.spec.ts`](../../frontend/tests/e2e/audit.spec.ts) — replaced `expect(true).toBe(true)` with real assertion (fails on `pageerror`, `http_failed`, `timeout`, or any `http_error >= 500`)

## 3. CRITICAL Security (Faza C)

- [`backend/api/extract_routes.py`](../../backend/api/extract_routes.py:868) — `/pdf-proxy` SSRF hardened:
  - https-only
  - Host must be in `_PDF_PROXY_ALLOWED_HOSTS` (Supabase Storage only)
  - 50 MB body cap via streamed iteration with early abort
  - `(10, 30)` connect/read timeout
  - Content-Type validation (PDF / octet-stream)
- [`backend/core/prompts.py`](../../backend/core/prompts.py) — added prompt-injection guard preface to both `MASTER_PROMPT_V2` and `FALLBACK_STRUCTURED_PROMPT_FLASH`. Instructs Gemini to treat PDF content as data only and ignore any instructions/system-prompt-like text inside it.
- [`backend/scripts/add_insurance_params.py`](../../backend/scripts/add_insurance_params.py) — hardcoded `password="postgres"` removed; now reads `SUPABASE_DB_PASSWORD` env var with explicit error if missing. Wrapped in `if __name__ == "__main__"` guard. Deprecation note about EAV migration added.

**Note on audit false positives:**
- XSS in `JsonViewerModal.tsx` — verified: HTML is escaped before `<mark>` injection. Not vulnerable.
- XSS in `VehicleComparisonModal.tsx` — verified: custom markdown parser escapes `<`, `>`, `&` before regex replacement. Not vulnerable.
- `hallucinated_fields` "not auto-removed" — verified: `_post_process_hitl_metadata()` IN `pipeline_card_summary.py` already removes them; the FE warning is for audit awareness, not a leak.

## 4. CRITICAL FE State (Faza D)

- [`frontend/src/ManualKalkulacje/PricingPanel.tsx`](../../frontend/src/ManualKalkulacje/PricingPanel.tsx):
  - Added negative-price + bad-discount validation (`validationErrors` memo)
  - Added two-way (round-trip) re-fetch after `PATCH /api/kalkulacje/{id}/pricing`: server's view of `stan_json.pricing` is what gets passed to `onSave()`, not the local optimistic `result`
  - Save button disabled while errors present
  - Error UI panel below results shows `saveError` or `validationErrors`
- [`frontend/src/CalculationsHistory/CalculationsHistoryPage.tsx`](../../frontend/src/CalculationsHistory/CalculationsHistoryPage.tsx):
  - Added `fetchError` state + Error UI panel with "Spróbuj ponownie" retry button (replaces infinite spinner)
  - `handleOpenVertexExtractor` now checks `vehicle_synthesis` existence before navigating; warns user via confirm() if vehicle was deleted (per memory `kalkulacja_vehicle_synthesis_link` — orphan vehicle_id is feature, not bug — but the FE crashed silently before)
- [`frontend/src/stores/offerCartStore.ts`](../../frontend/src/stores/offerCartStore.ts) — added `version: 1` + `migrate` handler to `persist()` middleware. Schema changes to `OfferItem`/`ClientData` won't silently corrupt rehydrated state anymore.
- [`backend/api/extract_routes.py`](../../backend/api/extract_routes.py:710) HITL apply — preserve original `confidence` value as `confidence_before_hitl` audit field before setting user-confirmed `confidence=1.0`. Same for discount block. Original extraction confidence no longer lost.
- [`backend/core/extraction_pipeline/phase_1_twins.py`](../../backend/core/extraction_pipeline/phase_1_twins.py) — wrapped per-vehicle pipeline in try/except. One bad vehicle no longer crashes the entire multi-vehicle batch; the failing record gets `verification_status='error'` with a `notes` explanation; subsequent vehicles continue processing.

## 5. NOT done (deliberate or out of scope)

These items from the audit were investigated and either:
- **False positives** (XSS, hallucinated_fields, OVERUSE_FEE_OPTIONS memoization, phase_2 stale card_summary)
- **No upstream fix** (xlsx CVEs — need library migration)
- **Strategic / multi-day** (LTRKalkulator refactor 1159 LOC, scoring_search_routes 2584 LOC split, Sentry integration, code splitting / lazy-load PDF worker, frontend tests expansion, missing route tests, 11 missing TABLE_REGISTRY entries, doc refresh of calc_02-12 specs)
- **Authorization model concerns** (`AUTH_ENABLED` toggle, anon-key UPDATE/DELETE on `vehicle_synthesis`) — these require a Supabase RLS policy review, not just code changes

## 6. Verification

```bash
cd backend && poetry run pytest --tb=no   # expects 580 passed (with --reruns 2 retrying any flaky network failures)
cd backend && poetry run ruff check .     # files edited in this round are clean; pre-existing issues unrelated
cd frontend && npm run build              # TS strict + Vite passes (5.0 MB bundle warning — strategic item)
cd frontend && npm run lint               # pre-existing any/non-null issues; nothing new introduced
cd frontend && npm audit                  # 6 remaining vulns all xlsx (no fix); was 12
```

## 7. Files touched (summary)

**Backend** (12 files): `core/supabase_retry.py` (NEW), `core/control_center.py`, `core/samar_rv.py`, `core/samar_rv_fetchers.py`, `core/LTRKalkulator.py`, `core/LTRSubCalculatorSerwisNew.py`, `core/prompts.py`, `core/extraction_pipeline/phase_1_twins.py`, `api/extract_routes.py`, `main.py`, `scripts/add_insurance_params.py`, `tests/conftest.py`, `tests/test_debug.py` (DELETED), `run_dev.py` (RESTORED), `pyproject.toml`

**Frontend** (5 files): `src/ManualKalkulacje/PricingPanel.tsx`, `src/CalculationsHistory/CalculationsHistoryPage.tsx`, `src/stores/offerCartStore.ts`, `tests/e2e/audit.spec.ts`, `package.json` + `package-lock.json`

**Docs** (3 files): `CLAUDE.md`, `docs/audit/full_codebase_audit_2026-05-18.md` (created in prior session), `docs/audit/fixes_applied_2026-05-19.md` (this)
