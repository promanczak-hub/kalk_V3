# CLAUDE.md — kalk_v3 codebase guidance

Operational guide for Claude (and humans) working in this repo. **Read this first** before any non-trivial change.

## What this is

**Kalk v3** = LTR (long-term-rental) leasing calculator for vehicles. Vertex/Gemini extracts data from PDF offers → 12-stage Python pipeline computes monthly rate → React frontend lets users browse/configure/save calculations. Polish-language UI; codebase mixes Polish (domain) and English (technical).

## Tech stack

| Layer | Stack |
|---|---|
| **Frontend** | React 19 + Vite 7 + TypeScript 5.9 (strict) + Tailwind v4 + MUI v7 + Zustand + React Router v7 + Framer Motion + AG Grid + Axios |
| **Backend** | FastAPI + Python 3.12 + Pydantic v2 + Poetry; SQLAlchemy + psycopg2 + supabase-py |
| **Async** | Celery + Redis (Docker locally); `--pool=solo` on Windows |
| **DB** | **Supabase ONLINE** (`gnpsdiarmwvqhqbyetce`) — NOT local Docker |
| **AI** | Google GenAI (Vertex AI / Gemini) for PDF extraction |
| **Tests** | pytest (backend, 43 files), Playwright (frontend E2E, 5 files), Vitest (frontend unit — being added) |
| **CI** | `.github/workflows/ci.yml`, `deploy.yml` — runs ruff + mypy on push |

## 🚨 Critical safety rules

### AI LOCKOUT — destructive ops on Supabase ONLINE are FORBIDDEN

| Operation | Status |
|---|---|
| `DELETE FROM ...` | 🚫 |
| `DROP TABLE / DROP COLUMN` | 🚫 |
| `TRUNCATE` | 🚫 |
| `supabase db reset` | 🚫 |
| `apply_migration` with DROP/DELETE | 🚫 |

**Allowed:** `SELECT`, `INSERT`. `UPDATE` only after explicit user command. If user orders deletion → STOP → repeat command → wait for confirmation.

### 400 LOC max per source file

Hard rule from README. Files over 400 lines require refactor. Currently `LTRKalkulator.py` is 1141 lines — that's *known debt*, not license to keep growing.

### Two-way (round-trip) test for DB-affecting changes

Any change that writes to DB must verify both write AND read. POST returns 200 ≠ data is valid. Read the record back, deserialize, render — if it explodes, the write was wrong.

## 12-stage calculation pipeline

Canonical order from V1 (`LTRKalkulator.cs:250-398`). Steps 1-4 are independent (parallelizable). Steps 5-9 cascade. Steps 10-12 aggregate.

| # | Stage | Python file | Depends on | Spec |
|---|---|---|---|---|
| 1 | Opony (tires) | `LTRSubCalculatorOpony.py` | — | [calc_01_opony.md](docs/audit/calc_01_opony.md) |
| 2 | Koszty Dodatkowe | `LTRSubCalculatorKosztyDodatkowe.py` | — | [calc_02](docs/audit/calc_02_koszty_dodatkowe.md) |
| 3 | Samochód Zastępczy | `LTRSubCalculatorSamochodZastepczy.py` | — | [calc_03](docs/audit/calc_03_samochod_zastepczy.md) |
| 4 | Serwis | `LTRSubCalculatorSerwisNew.py` | — | [calc_04](docs/audit/calc_04_serwis.md) |
| 5 | Cena Zakupu (CAPEX) | `LTRSubCalculatorCenaZakupu.py` | tires capex | [calc_05](docs/audit/calc_05_cena_zakupu.md) |
| 6 | Utrata Wartości (WR) | `LTRSubCalculatorUtrataWartosciNew.py` | CenaZakupu | [calc_06](docs/audit/calc_06_utrata_wartosci.md) |
| 7 | Amortyzacja | `LTRSubCalculatorAmortyzacja.py` | CenaZakupu, WR | [calc_07](docs/audit/calc_07_amortyzacja.md) |
| 8 | Ubezpieczenie | `LTRSubCalculatorUbezpieczenie.py` | Amortyzacja%, CenaZakupu | [calc_08](docs/audit/calc_08_ubezpieczenie.md) |
| 9 | Finanse (PMT) | `LTRSubCalculatorFinanse.py` | CenaZakupu, WR | [calc_09](docs/audit/calc_09_finanse.md) |
| 10 | Koszt Dzienny | `LTRSubCalculatorKosztDzienny.py` | 1-9 | [calc_10](docs/audit/calc_10_koszt_dzienny.md) |
| 11 | Stawka | `LTRSubCalculatorStawka.py` | 1-10 | [calc_11](docs/audit/calc_11_stawka.md) |
| 12 | Budżet Marketingowy | `LTRSubCalculatorBudzetMarketingowy.py` | WR | [calc_12](docs/audit/calc_12_budzet_marketingowy.md) |

Orchestrator: `backend/core/LTRKalkulator.py:Calculate()`. Step-by-step debugger: `backend/core/PipelineDebugger.py:calculate_steps()`. V1 parity reference: [v1_calcreport_reference.md](docs/audit/v1_calcreport_reference.md).

### 🛡️ Golden Rule: Residual Value (WR) corrections — **2503 SOT**

WR calculation per current **2503 SOT** (Source of Truth — Supabase `body_types.utrata_wartosci`):

- **Krok 1-3:** depreciation curve (multiplicative year cascade `base × Π(1 ± δ)` per SOT — formerly additive `base + Σ deltas` in legacy `2503_wynik_JŁ.xlsx` Excel; *post k2 fix*).
- **Krok 4 (korekta przebiegu):** **WYŁĄCZONY w samar_rv.py per 2503 SOT** (*post k4 fix*). Korekta przebiegu jest teraz częścią `body_types.utrata_wartosci` tabeli (per body type). Debug surface: `result.debug["krok4_korekta_disabled_per_sot"] == 1.0`.
- **Krok 5 (admin corrections — kolor, nadwozie):** operuje na **base catalogue price (net, no options)**, additive po Krok 3:

```python
Korekta_Wartosc = (Kolor_% + Nadwozie_%) * Cena_Katalogowa_Baza_Netto
WR_po_Kroku_5 = WR_po_Krok_3 + Korekta_Wartosc
```

  Zabudowa correction została przeniesiona do `body_types` (memory `body_types_sot`) — nie liczyć jej tutaj.

**Parity validator:** `backend/tests/test_v1_parity_samar_rv.py::test_skoda_octavia_rs_v1_parity` — Skoda Octavia RS class-10 SAMAR daje **61 046,00 PLN brutto** per current SOT (legacy Excel baseline `81 185,76 PLN` jest superseded).

**FORBIDDEN:**
- Re-enabling Krok 4 w samar_rv.py bez zmiany `body_types.utrata_wartosci` (podwójna korekta).
- Multiplying corrections on the WR pool (`WR * (1 - korekta_pct)`) zamiast additive on base — krok 5 jest additive.
- Zabudowa correction w samar_rv.py — należy do `body_types`.

### Reverse Search uses CACHE — does NOT recompute

`/api/batch-prices`-style endpoints must read base price (0% margin) from `ltr_kalkulacje` or Redis cache, then frontend adds margin via `price / (1 - marginPct/100)`. Do NOT recreate `_calc_exact_price` — it diverges from `matrix_cache_job` Celery cache.

## Where things live

| Domain | Path |
|---|---|
| Backend orchestrator | `backend/core/LTRKalkulator.py` |
| Sub-calculators | `backend/core/LTRSubCalculator*.py` (12 files) |
| API routes | `backend/api/*_routes.py` |
| Extraction pipeline | `backend/core/extractor_v2.py`, `extraction_pipeline/phase_*.py` |
| Pipeline debugger | `backend/core/PipelineDebugger.py` |
| Celery tasks | `backend/core/celery_app.py`, `matrix_cache_job.py`, `background_jobs.py`, `backend/tasks/` |
| Service layer | `backend/services/` (`ai_mapper_service`, `classification_service`, `document_storage_service`) |
| DB helpers | `backend/db/`, `backend/core/control_center.py`, `backend/core/database.py` |
| Eval / experiments | `backend/eval/discount_eval/` — extraction quality harness (real PDFs) |
| Templates | `backend/templates/` — XLSX / HTML offer templates |
| Tests | `backend/tests/` (pytest), `frontend/tests/e2e/` (Playwright) |
| Frontend pages | `frontend/src/{VertexExtractor,ScoringSearch,ManualKalkulacje,CalculationsHistory,CalculatorPanel}/` |
| Shared components | `frontend/src/components/` |
| Stores | `frontend/src/stores/` (Zustand: `useAppStore`, `offerCartStore`) |
| API client | `frontend/src/lib/apiClient.ts`, `payloadBuilders.ts` |
| **Table registry (SOT)** | [`TABLE_REGISTRY.md`](TABLE_REGISTRY.md) — every DB table → backend + frontend touchpoints |
| **Calc audit specs** | [`docs/audit/calc_*.md`](docs/audit/) |
| **Memory** | `~/.claude/projects/D--kalk-v3/memory/MEMORY.md` (12 entries: body_types SOT, control_center EAV, anon-key, extractor quirks, …) |

## Commands

### Backend (run from `backend/`)

```powershell
poetry install
poetry run python run_dev.py              # FastAPI dev (uvicorn) → http://localhost:8000
poetry run celery -A core.celery_app worker --pool=solo --loglevel=info  # Windows
poetry run pytest                          # tests
poetry run ruff check .                    # lint
poetry run mypy .                          # types
poetry run black . ; poetry run isort .   # format (sequential on Windows; PS5 has no `&&`)
```

### Frontend (run from `frontend/`)

```powershell
npm install
npm run dev          # → http://localhost:5173
npm run build        # tsc -b && vite build
npm run lint         # ESLint
npm run test:e2e     # Playwright
npm test             # Vitest (once added per Phase C)
```

### Infrastructure (run from repo root)

```powershell
docker-compose up -d redis
```

## How we work here — SUPERPOWERS-style discipline

Per [this plan](../../../../Users/proma/.claude/plans/spojrsysz-na-maja-apliakcje-flickering-patterson.md), we're moving from patch-driven to plan-first. Conventions:

1. **Plan before code.** Non-trivial change → write a plan file under `plans/` (or `~/.claude/plans/`) before touching anything.
2. **Branch per feature.** No commits on `master` for in-progress work. Use feature branches, optionally git worktrees for isolated dev.
3. **TDD where pipeline is involved.** New SubCalculator? Write a parity test against V1 first (`backend/tests/test_v1_parity_*.py`). Watch RED → make it GREEN → refactor.
4. **Skills, not scripts.** If a debugging/fix task is repeated, codify it in `.claude/skills/` rather than another `fix_X.py` in `backend/scripts/`.
5. **Verify before declaring done.** Backend: pytest + ruff + mypy clean. Frontend: typecheck + ESLint + relevant test pass. UI changes: actually open the browser (preview tools).
6. **Evidence over claims.** Don't say "should work" — show output. For DB writes, do the two-way (round-trip) test.

### Codified workflows — see `.claude/skills/`

| Skill | When to use |
|---|---|
| `diagnose-calculator-stage` | A LTR calc result looks wrong. Isolate which of 12 stages diverged from V1. |
| `add-body-type` | New body type in Google Sheet → migrate to `body_types` table → frontend chip. |
| `fix-price-validator-mismatch` | Extraction price drift (`paid_options PLN netto` vs aggregator). See memory `extractor_price_quirks`. |
| `add-sub-calculator` | Adding/replacing a stage in the 12-step pipeline. Includes parity test scaffolding. |
| `verify-extraction-output` | Vertex/Gemini extractor on a test PDF; compare against expected JSON. |

### Custom subagent — `.claude/agents/calc-stage-debugger`

Read-only agent that knows the 12-stage pipeline + `docs/audit/calc_*.md` as spec. Dispatch when you need a stage-by-stage analysis without polluting the main context with `LTRSubCalculator*` source.

## Anti-patterns to avoid

- ❌ **Writing `fix_X.py` / `repair_X.py` in `backend/scripts/`** — 70+ already accumulated. Codify as a skill instead. Audit categorization: `~/.claude/plans/spojrsysz-na-maja-apliakcje-flickering-patterson.md` Faza D.
- ❌ **Committing to `master` with 100+ uncommitted files.** Branch.
- ❌ **Hard-coding brand multipliers** (BMW=1.05, etc.). Use DB tables (`samar_class_*`, `body_types`, `ltr_admin_*`). Memory note `feedback_service_multipliers_neutral` — service multipliers stay at 1.0; differentiation only in base rate.
- ❌ **`trim_level` overriding SAMAR class.** Memory note `feedback_trim_not_overrides_samar` — RS/GTI/AMG never override sub-class.
- ❌ **Mocking the database in tests** — README mandates two-way (round-trip) tests for DB writes.
- ❌ **Recreating `_calc_exact_price` in reverse-search endpoints.** Use cache. See Reverse Search section.
- ❌ **Bypassing `TABLE_REGISTRY.md`** when renaming tables/columns. The registry is the impact-analysis SOT.
- ❌ **Treating `control_center` as wide-row.** It's EAV (key/value) now — go through `core/control_center.py` adapter. Memory note `control_center_eav`.
- ❌ **Silent fallbacks w pipeline kalkulacji** (`getattr(settings, "default_wibor", 5.0)`, `value or 0.0`, `multiplier or 1.0`). 12-stage LTR calc = sztywna matematyka transakcyjna — brak inputu = `raise ValueError`, nie literal default. Pattern dopuszczony: **input → Control Center → raise**. Memory note `feedback_no_calc_fallbacks`. Wyjątek: udokumentowana neutralna polityka (np. `feedback_service_multipliers_neutral`).

## Memory and references

- **Global memory:** `~/.claude/projects/D--kalk-v3/memory/MEMORY.md` and linked files (auto-loaded, do not duplicate here)
- **Architecture overview:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Table registry (SOT for renames):** [TABLE_REGISTRY.md](TABLE_REGISTRY.md)
- **README (user-facing setup):** [README.md](README.md)
- **Stage specs (V1 parity):** [docs/audit/calc_*.md](docs/audit/)
- **V1 reference output:** [docs/audit/v1_calcreport_reference.md](docs/audit/v1_calcreport_reference.md)

## Commit conventions

Recent commits set the pattern: conventional-ish, scoped, descriptive about *why*.

```
fix(kalkulacje): align top-row Rata Netto with active matrix cell + margin
Merge cleanup B+C+D+E (orphan modules, samar-rv mismatch, dumps, email endpoint)
Drop merge residue: dup Kalkulacje Section + inline KalkulacjaParamsRow
Add MIME types to nginx and show price validation
```

End commits with co-author when AI-assisted:
```
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```
