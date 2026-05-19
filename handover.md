# Handover — kalk_v3

> Plik przekazujący kontekst między sesjami Claude. **Aktualizować przed kompaktacją sesji i na koniec większej fazy.** Sekcje na górze są zawsze najbardziej aktualne — historię archiwizuj niżej, nie kasuj.

---

## Status aktualny

**Data:** 2026-05-19
**Aktywna gałąź:** master
**Aktywna faza:** brak dedykowanej — w toku porządkowanie pipeline kalkulacji (Rule 14, fail-fast LTR, HITL routing) + cherry-pick z `Claude_Code_Dev_Stack_V1` do CLAUDE.md
**Niescommitowane zmiany:** ~44 plików (M) + 1 (D) — głównie refactor pipeline + validator Rule 14 + frontend cleanup. Szczegóły: `git status`.

---

## Co zostało zrobione w ostatnich sesjach

> Sourced z `git log` — najnowsze na górze.

- `cba5b8e` — feat(validator): Rule 14 FULL_SUM_INTEGRITY — catch total_price missing service_equipment
- `bc0f102` — feat(pipeline): fail-fast w LTR calc — no silent fallbacks (per memory `feedback_no_calc_fallbacks`)
- `a363c22` — refactor(pipeline): per-cell calc extraction + validator Rules 12/13 + HITL routing
- `6d0c88e` — feat(offer): preflight enrichment cache — 38x faster XLSX generation
- `2a0945e` — feat(offer): standalone WYPOSAŻENIE STANDARDOWE section at bottom

---

## Następne kroki

1. **Commit cherry-pick z V1 dev stack** — CLAUDE.md (Karpathy + Priority order + Allow List) + nowy `handover.md`. Plan: `~/.claude/plans/c-users-proma-downloads-claude-code-dev-swift-tide.md`.
2. **Decyzja: `handover.md` w repo czy w `.gitignore`?** — jako shared SOT (commit) vs per-user (gitignore). Domyślnie: commit do repo.
3. **Faza D z planu SUPERPOWERS** — audyt 70+ skryptów w `backend/scripts/`, kategoryzacja keep/skill/delete. Plan: `~/.claude/plans/spojrsysz-na-maja-apliakcje-flickering-patterson.md`.
4. **Refactor `LTRKalkulator.py`** — 1141 linii (limit 400), known debt. Wymaga TDD: parity test V1 najpierw.

---

## Znane problemy / WIP

- `LTRKalkulator.py` ma 1141 linii — known debt, refactor pending z TDD.
- 70+ skryptów w `backend/scripts/` (`fix_*.py`, `repair_*.py`, `diagnose_*.py`) — audit i kategoryzacja w toku (Faza D z SUPERPOWERS planu).
- Skoda Octavia RS class-10 SAMAR: **61 046,00 PLN brutto** per current 2503 SOT (legacy Excel baseline `81 185,76 PLN` jest superseded; parity validator: `test_skoda_octavia_rs_v1_parity`).

---

## Pułapki techniczne (między sesjami)

> Z memory entries — streszczenie żeby nie trzeba było ich osobno szukać. Pełna lista w `~/.claude/projects/D--kalk-v3/memory/MEMORY.md`.

- **WR Krok 4 WYŁĄCZONY w `samar_rv.py`** per 2503 SOT — korekta przebiegu jest częścią `body_types.utrata_wartosci` (per body type). Re-enable bez zmiany body_types = podwójna korekta. Debug surface: `result.debug["krok4_korekta_disabled_per_sot"] == 1.0`. Memory: `body_types_sot`.
- **Mnożniki serwisowe = 1.0** — brand/fuel/drive/gearbox trzymane na 1.0; różnicowanie tylko w base rate. Memory: `feedback_service_multipliers_neutral`.
- **Trim level NIGDY nie nadpisuje SAMAR** — RS / GTI / AMG to oznaczenie wersji, nie sub-klasy. Memory: `feedback_trim_not_overrides_samar`.
- **Reverse Search używa cache, nie recompute** — `/api/batch-prices` czyta z `ltr_kalkulacje` / Redis, frontend dodaje margin via `price / (1 - marginPct/100)`. Nie tworzyć `_calc_exact_price` — divergi od `matrix_cache_job`.
- **Anon JWT używany w BE (94 imports) + FE** — direct UPDATE/DELETE na `vehicle_synthesis` z frontu. RLS deny-all rozwali oba. Memory: `backend_uses_anon_key_primary`.
- **Local dev: stack w dockerze + Vite na hoście :5180** — dockerowy prod frontend trzyma :5173. Memory: `local_dev_dockerized_stack`.
- **`control_center` jest EAV (key/value), NIE wide-row** — reads/writes przez `core/control_center.py` adapter. Memory: `control_center_eav`.
- **No silent fallbacks w pipeline kalkulacji** — brak `getattr(settings, "X", literal)` / `value or 0.0` / `multiplier or 1.0`. Brak danych = `raise ValueError`. Memory: `feedback_no_calc_fallbacks`.
- **Gemini response_schema ≠ `dict[str, X]`** — `additionalProperties` w Pydantic = ValueError przy starcie → pusta CardSummary. Workaround: `WithJsonSchema`. Memory: `gemini_no_additional_properties`.

---

## Zasady aktualizacji tego pliku

1. **Przed kompaktacją sesji** — update sekcje „Status aktualny" + „Co zrobione" + „Następne kroki".
2. **Po zakończeniu fazy** — pełny raport z deliverables + zwryfikowanymi metrykami.
3. **Niescommitowane zmiany** — wylistuj jawnie (jak `git status`), żeby kolejna sesja wiedziała co WIP, a co już merged.
4. **Nie kasuj historii** — nowe sekcje dodawaj na górze, stare archiwizuj niżej (kontekst dla przyszłych sesji).
5. **Decyzje techniczne z sesji** — jeśli podjęto decyzję która nie pójdzie do `memory/` (bo per-sesja), zapisz tutaj w sekcji „Decyzje".
