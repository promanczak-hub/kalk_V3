# 📋 Rejestr Nazw Tabel Supabase — Single Source of Truth

> [!CAUTION]
> **Przed JAKĄKOLWIEK zmianą nazwy tabeli, kolumny lub widoku — przeszukaj ten rejestr i wykonaj Impact Analysis.**
> Zaniedbanie tego kroku skutkuje błędami `relation does not exist` (backend) lub `404/empty data` (frontend).

## Zasady nazewnictwa

1. **Tabele DB** → `snake_case` po angielsku (np. `tyre_costs`, `samar_classes`)
2. **Nazwy w kodzie** → muszą **identycznie** odpowiadać nazwie w DB (zero aliasów!)
3. **Zmiana nazwy** = zmiana we WSZYSTKICH warstwach jednocześnie (migracja DB + backend + frontend)

---

## Tabele produkcyjne (schema: `public`)

| Tabela DB                          | Backend (`core/`)                                    | Frontend (`src/`)                                                  | Opis                              |
| ---------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------ | --------------------------------- |
| `vehicle_synthesis`                | `LTRKalkulator.py`, `background_jobs.py`, `extract_routes.py`, `kalkulacje_routes.py`, `scoring_search_routes.py`, `extraction_pipeline/phase_2_mapping.py` | `useVehicles.ts`, `VehicleRowCard.tsx`, `useDocumentProcessing.ts`, `useVehicleDataSync.ts`, `useVehicleMetaManager.ts`, `useVehicleOptionsManager.ts`, `CalculationsHistoryPage.tsx` | Główna tabela pojazdów z syntezą — anon JWT używany do `UPDATE/DELETE/INSERT` w FE (patrz §RLS) |
| `fleet_management_view`            | —                                                    | `useVehicles.ts`, `CalculationsHistoryPage.tsx`                    | Widok (VIEW) do zarządzania flotą |
| `samar_classes`                    | `samar_rv.py`, `samar_mapper.py`, `LTRKalkulator.py`, `scoring_search_routes.py` | `VehicleRowCard.tsx` (lista statyczna, sync z DB) | Klasy SAMAR (słownik)             |
| `samar_class_depreciation_rates`   | `samar_rv_fetchers.py`                               | —                                                                  | Stawki deprecjacji wg klasy SAMAR |
| `samar_class_mileage_corrections`  | `samar_rv_fetchers.py`                               | —                                                                  | Korekty przebiegowe SAMAR         |
| `samar_class_service_rates`        | `LTRSubCalculatorSerwisNew.py`                       | —                                                                  | Progi km × stawka serwisowa ASO/non-ASO (z GSheets) |
| `samar_class_options_rv`           | `samar_rv_fetchers.py`, `audit_sot_vs_db.py`         | —                                                                  | Stawka amortyzacji opcji per (samar_class, engine_type, year) |
| `samar_brand_corrections`          | `samar_rv_fetchers.py`, `audit_sot_vs_db.py`         | —                                                                  | Korekty WR per marka/model/silnik |
| `samar_service_brand_multipliers`  | `LTRSubCalculatorSerwisNew.py`, `param_preview.py`, `sync_service_multipliers.py` | —                                              | Mnożnik serwisowy per marka (default 1.0 per memory `feedback_service_multipliers_neutral`) |
| `samar_service_fuel_multipliers`   | `LTRSubCalculatorSerwisNew.py`, `param_preview.py`, `sync_service_multipliers.py` | —                                              | Mnożnik serwisowy per typ paliwa |
| `samar_service_drive_multipliers`  | `LTRSubCalculatorSerwisNew.py`, `param_preview.py`, `sync_service_multipliers.py` | `VertexExtractorPage.tsx` (initialData fetch) | Mnożnik serwisowy per napęd |
| `samar_service_gearbox_multipliers`| `LTRSubCalculatorSerwisNew.py`, `param_preview.py`, `sync_service_multipliers.py` | —                                              | Mnożnik serwisowy per skrzynia biegów |
| `tab_okres_final`                  | `samar_rv_fetchers.py`, `audit_sot_vs_db.py`, `check_tables.py` | —                                                       | Stawki RV per (klasa, silnik) × próg przebiegu — kluczowe dla kaskady WR |
| `transport_fees`                   | `LTRKalkulator.py`                                   | —                                                                  | Opłata transportowa per marka     |
| `engines`                          | `engine_mapper.py`, `classification_service.py`      | `VehicleRowCard.tsx`, `VertexExtractorPage.tsx` (initialData fetch) | Słownik napędów/silników          |
| `body_types`                       | `body_type_matcher.py`, `samar_rv_fetchers.py` (utrata_wartosci), `sync_body_types.py` | `BodyTypesCrudPanel.tsx`, `VertexExtractorPage.tsx` | Słownik typów nadwozia + korekta WR (kolumna utrata_wartosci, SOT: GSheet gid=484265370) |
| `paint_types`                      | `samar_rv_fetchers.py`, `ltr_vehicle_resolvers.py`   | `VertexExtractorPage.tsx`                                          | Typy lakieru (metalik itp.)       |
| `koszty_opon`                      | `LTRSubCalculatorOpony.py`                           | `TabelaOponCrudPanel.tsx`, `VehicleFinancialOptions.tsx`           | Macierz cen opon                  |
| `tabela_rabaty`                    | `pipeline_discounts.py`                              | `RabatyCrudPanel.tsx`                                              | Tabela rabatów dealerskich        |
| `control_center`                   | `core/control_center.py` (EAV adapter, **jedyne wejście**), `samar_rv.py`, `LTRSubCalculatorOpony.py`, `LTRSubCalculatorFinanse.py`, `LTRSubCalculatorSerwisNew.py`, `LTRSubCalculatorBudzetMarketingowy.py`, `sync_control_center_gsheet.py` | — | EAV (key/value) — wszystkie globalne parametry LTR; patrz memory `control_center_eav` |
| `ltr_admin_ubezpieczenia`          | `ltr_db_fetchers.py`                                 | —                                                                  | Stawki ubezpieczeniowe            |
| `ltr_admin_wspolczynniki_szkodowe` | `ltr_db_fetchers.py`                                 | —                                                                  | Współczynniki szkodowe            |
| `ltr_admin_korekta_wr_roczniks`    | `samar_rv_fetchers.py`                               | —                                                                  | Korekty WR wg rocznika            |
| `replacement_car_rates`            | `ltr_db_fetchers.py`                                 | —                                                                  | Stawki sam. zastępczego           |
| `calculation_jobs`                 | `kalkulacje_routes.py`, `matrix_cache_job.py`        | `VehicleActionButtons.tsx`, `CalculationJobsStatus.tsx`            | Status job-ów Celery (matrix cache builds) |
| `vehicle_matrix_cache`             | `kalkulacje_routes.py`, `oferty_routes.py`, `scoring_search_routes.py`, `matrix_cache_job.py` | (czytane przez backend, zwracane do FE)               | Pre-computed cache matryc LTR per (kalkulacja_id, duration, mileage) — fundament Reverse Search per CLAUDE.md ("uses CACHE, doesn't recompute") |
| `extraction_corrections`           | `extract_routes.py`, `pipeline_card_summary.py`      | —                                                                  | Audit log korekt HITL + Few-Shot prompt injection do extractora |
| `ltr_offers`                       | `oferty_routes.py`                                   | (eksport ofert XLSX)                                               | Wygenerowane oferty / quotation snapshots |

## Tabele produkcyjne (schema: `reverse_search`)

| Tabela DB                      | Backend (`core/`)                                                            | Frontend | Opis                     |
| ------------------------------ | ---------------------------------------------------------------------------- | -------- | ------------------------ |
| `universal_features`           | `features_routes.py`, `feature_enrichment.py`, `feature_cross_reference.py` | —        | Cechy uniwersalne        |
| `universal_feature_categories` | `features_routes.py`                                                        | —        | Kategorie cech           |
| `universal_feature_aliases`    | `features_routes.py`                                                        | —        | Aliasy nazw cech         |
| `feature_aliases`              | `feature_enrichment.py`                                                     | —        | Aliasy cech używane przez enrichment (NIE mylić z `universal_feature_aliases`) |
| `vehicle_feature_evidence`     | `features_routes.py`, `feature_enrichment.py`                               | —        | Dowody przypisania cech  |
| `vehicle_catalog_matches`      | `features_routes.py`, `feature_cross_reference.py`                          | —        | Dopasowania katalogowe   |
| `vehicle_features_summary_view`| `features_routes.py`                                                        | —        | VIEW agregujący cechy do podsumowania per pojazd |
| `model_document_sources`       | `extraction_pipeline/phase_2_mapping.py`                                    | —        | Źródła dokumentów modeli |
| `reverse_search_saved_filters` | `features_routes.py` (5 CRUD ops)                                           | —        | Zapisane filtry użytkownika dla reverse search |

## Tabele OBSERWOWANE — w rejestrze ale BEZ aktywnych referencji w kodzie

> [!WARNING]
> Te tabele były wcześniej w rejestrze. Audit 2026-05-18 nie znalazł aktywnych referencji (`.table()` / `.from()`).
> Weryfikacja DB wymagana — może być artefakt historyczny do skasowania w migracji.

| Tabela DB                          | Ostatnie znane użycie                | Status                                |
| ---------------------------------- | ------------------------------------ | ------------------------------------- |
| `samar_klasa_wr`                   | (brak referencji)                    | ⚠️ ghost — zweryfikuj czy istnieje w DB |
| `ltr_admin_korekta_wr_markas`      | (brak referencji)                    | ⚠️ ghost — zastąpione przez `samar_brand_corrections`? |
| `vehicle_feature_state`            | (brak referencji)                    | ⚠️ ghost — może obsolete po refactorze feature pipeline |
| `feature_import_runs`              | (brak referencji)                    | ⚠️ ghost — log table, prawdopodobnie tylko historyczny |

## Storage Buckets

| Bucket             | Backend                                  | Frontend                   |
| ------------------ | ---------------------------------------- | -------------------------- |
| `raw-vehicle-pdfs` | `background_jobs.py`, `parser_routes.py` | `useDocumentProcessing.ts` |

---

## 🔍 Procedura Impact Analysis przy zmianie nazwy

Wykonaj **PRZED** jakąkolwiek zmianą nazwy tabeli/kolumny:

```bash
# 1. Przeszukaj CAŁY projekt pod kątem starej nazwy
grep -rn "stara_nazwa" backend/ frontend/src/ supabase/migrations/

# 2. Sprawdź widoki SQL zależne od tabeli
# W Supabase SQL Editor:
SELECT viewname, definition FROM pg_views WHERE definition LIKE '%stara_nazwa%';

# 3. Sprawdź RLS policies
SELECT tablename, policyname, qual FROM pg_policies WHERE qual LIKE '%stara_nazwa%';
```

> [!IMPORTANT]
> **Checklist zmiany nazwy tabeli:**
>
> - [ ] Migracja SQL (`ALTER TABLE ... RENAME TO ...`)
> - [ ] Aktualizacja WSZYSTKICH plików backend z listy powyżej
> - [ ] Aktualizacja WSZYSTKICH plików frontend z listy powyżej
> - [ ] Aktualizacja widoków SQL zależnych
> - [ ] Aktualizacja tego pliku `TABLE_REGISTRY.md`
> - [ ] Uruchomienie testów (`pytest`)
> - [ ] Test manualny endpointów
