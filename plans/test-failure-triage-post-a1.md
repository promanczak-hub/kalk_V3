# Test failure triage — post-A1

**Date:** 2026-05-17
**Context:** Faza A1 (kalk_v3 przez pryzmat SUPERPOWERS) zamknięta — 24 commity na backup branch. `poetry run pytest tests/` reports **474 pass / 8 fail / 2 collection errors**.

Cel tego pliku: rozdzielić co JEST regression z A1 a co było broken przed A1, plus decyzja co z każdą sztuką.

---

## Collection errors (2) — FIX LANDED

| File | Why | Fix |
|---|---|---|
| `tests/api/test_features_extract_audio.py` | Bare `pytest` doesn't add backend root to sys.path → `from main import app` fails. NOT stale. | `[tool.pytest.ini_options] pythonpath = ["."]` w `pyproject.toml`. |
| `tests/pdf_pipeline/test_extractor.py` | Same sys.path root cause. `core.pdf_pipeline.extractor` **istnieje** — nie pomylić z `extraction_pipeline` (osobna paczka, też żyje). | Same fix. |

Po fixie pyproject.toml `poetry run pytest tests/` powinno collectować wszystko bez `--ignore`.

---

## Pre-existing failures (6 of 8) — NIE A1, do osobnej fazy

| Test | Why broken pre-A1 | Suggested fix |
|---|---|---|
| `test_redis_cache_search.py::test_cache_miss_calls_rpc_and_stores` | Test mockuje `sb.rpc("rpc_get_scoring_initial_data")`, ale `get_initial_data()` przepisane na `sb.table("vehicle_synthesis").select(...)` *przed* baseline 5b95a2c. Docstring potwierdza. | Przerobić mock na `sb.table(...).select(...).execute()` returning fake rows. |
| `test_redis_cache_search.py::test_redis_unavailable_fallthrough` | Same — `run_scoring_search` od dawna nie używa rpc(). | Same. |
| `test_feature_enrichment.py::test_llm_match_returns_only_high_confidence` | `_llm_match_equipment` woła `_get_aliases()` przed Gemini. Jeśli alias `felga aluminiowa` w cache → early return, Gemini nigdy nie odpalone, test nie weryfikuje confidence. | Patch `core.feature_enrichment._get_aliases` żeby zwracał `{}` w teście. |
| `test_feature_enrichment.py::test_llm_match_fallback_on_error` | Identyczny mechanizm — Gemini raise nigdy nie odpala. | Same. |
| `test_pipeline_debugger.py::test_pipeline_debugger_no_overrides_matches_kalkulator` | `ServiceCalculator._calculate_progressive_service_total` → `get_service_multiplier("UNKNOWN")` raises `ValueError` (fail-fast, brak fallback POZOSTAŁE w DB). Same on baseline. | Monkeypatch `get_service_multiplier` na 1.0 albo stub `ServiceCalculator.calculate`. |
| `test_pipeline_debugger.py::test_pipeline_debugger_with_override` | Same root cause. | Same. |
| `test_service.py::TestServiceCalculator::test_fake_brand_multiplier_survives` | `get_service_multiplier` jest fail-fast od *przed* baseline. Test docstring obiecuje "stosuje mnożnik bazowy 1.0", ale prod zawsze raise. Test był aspirational (a może produkcję ktoś zaostrzył bez update'u testu). | Albo: (a) softening prod do return 1.0 on miss, albo (b) flip test → `assertRaises(ValueError)`. |

**Status:** wszystkie 6 to test-side bugs (stale mocki + brak `_get_aliases` mock + niezgodność z fail-fast prod). NIE A1. Mogą być fix'owane w osobnej fazie ("A2: test maintenance — 6 broken mocks").

---

## Final state — 2026-05-17 (evening)

After Faza A2 + Skoda cache isolation fix:

- **489 → 491 pass** (after pyproject pythonpath unlocked 2 collection errors → +15 tests visible, then 5 A2 fixes recovered the 5 pre-existing failures)
- **6 → 1 expected failure (or 0 with cache-bust)** — Skoda parity now busts `samar_rv:*` Redis at test start to avoid order-dependent pollution from `test_feature_enrichment`
- Vitest: **39 tests / 4 files** (from 2 / 1 pre-A1) — 19.5× discipline lift on frontend

## REGRESSION FROM A1 (1 of 8) — **RESOLVED 2026-05-17 (user decision: #2 accept new SOT)**

**User decision:** "nie możesz robić żadnej regresji na Skodzie. ostatnie fixy k2 + k4 powodowały że wszystko liczy się dobrze" — k2 + k4 changes są intencjonalne, current code jest correct, test był stale. Wybrana ścieżka **#2** (accept regression jako nowy SOT, update test + Golden Rule + memory note).

**Co zostało zrobione:**
- `tests/test_v1_parity_samar_rv.py` — `expected_rv_gross: 81185.76 → 61046.00`, mileage assertion z `-2307.76 → 0.00`, dodano defense-in-depth assertion dla `krok4_korekta_disabled_per_sot == 1.0`, rewrite docstring (2503 SOT supersedes legacy `2503_wynik_JŁ.xlsx`)
- `CLAUDE.md` Golden Rule — przepisany: krok 4 wyłączony per SOT, krok 1-3 multiplicative cascade, zabudowa w `body_types`, FORBIDDEN section zaktualizowana
- `~/.claude/projects/D--kalk-v3/memory/body_types_sot.md` — dodano post-k2+k4 section z linkami
- Test status: **PASSED** w 0.93s

---

## (archiwum) Pierwotny opis regression przed decyzją user'a

| Test | Likely A1 commit | Root cause |
|---|---|---|
| `test_v1_parity_samar_rv.py::test_skoda_octavia_rs_v1_parity` | **`ee035ca refactor(pipeline): 12-stage calculator + samar + supporting infra against control_center EAV`** | 3 zmiany w `backend/core/samar_rv.py`: (1) `get_wr_percent_for_year` z **additive** `base_rate_4y + Σ deltas` na **multiplicative cascade** `base_rate_4y × Π(1±δ)`; (2) **Krok 4 mileage correction hard-coded do 0.0** (komentarz "nieaktywna per 2503 SOT"); (3) zabudowa correction usunięta (przeniesiona do `body_types`). |

**Drift:** test oczekiwał `81 185.76 PLN`, HEAD zwraca `61 046.00 PLN`. **≈ -24.8% / -20 140 PLN** na benchmark calc.

### Konflikt z dokumentacją

- **CLAUDE.md Golden Rule:**
  > Korekta_Wartosc = (Kolor_% + Nadwozie_% + Zabudowa_%) * Cena_Katalogowa_Baza_Netto
  > WR_po_Kroku_5 = WR_po_Korekcie_za_Przebieg + Korekta_Wartosc
  >
  > **FORBIDDEN:** Multiplying the amortized WR pool by correction %'s (e.g. `WR * (1 - korekta_pct)`).
  > Causes ~1000 PLN drift vs V1 (verified on Skoda Octavia RS, Cupra Terramar).

  A1 zmiana wprowadziła multiplicative cascade — dokładnie to co Golden Rule zabrania. **Skoda Octavia RS jest *kanonicznym* przykładem złamania Golden Rule.**

- **MEMORY note `body_types_sot`:**
  > kalk_v3: korekta WR per nadwozie w body_types.utrata_wartosci; SOT GSheet body_types tab; konsolidacja 2026-05-16.

  Konsolidacja jest faktem — ALE to nie znaczy że Krok 4 (mileage) ma być wyłączony. Memory note mówi tylko o *zabudowie* przeniesionej do body_types, nie o mileage correction.

### Trzy interpretacje

1. **A1 to bug.** Komentarz "nieaktywna per 2503 SOT" to nieuzasadnione założenie autora commitu. Mileage correction nadal jest częścią V1 parity, Golden Rule nadal obowiązuje. **Fix: revert Krok 4 + revert multiplicative → additive cascade w `samar_rv.py`.**

2. **A1 to zamierzona zmiana**, 2503 SOT zastępuje stary V1 reference. Wtedy:
   - Test parity musi być przepisany na nowe wartości (61 046.00 PLN albo cokolwiek 2503 mówi)
   - Memory note `body_types_sot` musi być rozszerzona o "mileage correction also moved (deactivated 2026-05-XX per 2503)"
   - CLAUDE.md Golden Rule MUSI być rewritten — obecnie aktywnie kłamie

3. **A1 to częściowa zmiana** — niektóre rzeczy (zabudowa → body_types) są intencjonalne, inne (cascade additive→multiplicative) to side-effect refactoru. Wtedy mix fix: revert cascade i Krok 4, zachować zabudowa zmianę.

**Domyślnie polecam #1** — bo Golden Rule jest twarda zasada, mileage correction nie była częścią "2503 SOT" o ile mi wiadomo, a CLAUDE.md wyraźnie wskazuje Skoda Octavia RS jako weryfikator additive. Ale potrzebuję business decyzji.

### Plan działania (gdy decyzja zapadnie)

**Jeśli #1 (revert):**
```bash
# Na osobnym branchu — nie na master
git checkout -b fix/samar-rv-additive-cascade-revert
# Inspect what changed:
git show ee035ca -- backend/core/samar_rv.py | less
# Revert just samar_rv.py changes:
git checkout 5b95a2c -- backend/core/samar_rv.py
# Verify Skoda parity passes:
poetry run pytest tests/test_v1_parity_samar_rv.py -v
# Then check OTHER tests didn't break (Cupra Terramar etc.):
poetry run pytest tests/test_v1_parity_*.py -v
# Commit + open MR
```

**Jeśli #2 (accept regression, update test+docs):**
- Update `test_v1_parity_samar_rv.py` expected values
- Update `~/.claude/projects/D--kalk-v3/memory/MEMORY.md` `body_types_sot` note
- Update `D:\kalk_v3\CLAUDE.md` Golden Rule section
- Document `docs/audit/v1_calcreport_reference.md` change (2503 supersedes prior)

---

## Verification po fixie collection errors

```powershell
cd D:\kalk_v3\backend
poetry run pytest tests/ --tb=short -q
# Expected:
# - Collection: zero errors (pyproject pythonpath in effect)
# - Pre-existing failures: still 6 (need plan A2)
# - Skoda parity: still failing 1 (need business decision)
# - Total: ~474 pass / 7 fail (was 8 — one Skoda is the regression, rest stayed)
```

(Note: collection error fix może odsłonić MORE tests które wcześniej w ogóle nie ruszały — np. `test_features_extract_audio` z 10 testami. Mogą tam być kolejne pre-existing issues.)
