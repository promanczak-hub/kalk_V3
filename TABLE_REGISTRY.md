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
| `vehicle_synthesis`                | `LTRKalkulator.py`, `background_jobs.py`             | `useVehicles.ts`, `VehicleRowCard.tsx`, `useDocumentProcessing.ts` | Główna tabela pojazdów z syntezą  |
| `fleet_management_view`            | —                                                    | `useVehicles.ts`                                                   | Widok (VIEW) do zarządzania flotą |
| `samar_classes`                    | `samar_rv.py`, `samar_mapper.py`, `LTRKalkulator.py` | —                                                                  | Klasy SAMAR (słownik)             |
| `samar_class_depreciation_rates`   | `samar_rv.py`                                        | —                                                                  | Stawki deprecjacji wg klasy SAMAR |
| `samar_class_mileage_corrections`  | `samar_rv.py`                                        | —                                                                  | Korekty przebiegowe SAMAR         |
| `samar_service_costs`              | `LTRSubCalculatorSerwisNew.py`                       | —                                                                  | Koszty serwisowe SAMAR            |
| `samar_klasa_wr`                   | `LTRKalkulator.py`                                   | —                                                                  | Klasa WR (wartość rezydualna)     |
| `engines`                          | `engine_mapper.py`                                   | `VehicleRowCard.tsx`                                               | Słownik napędów/silników          |
| `body_types`                       | `body_type_matcher.py`                               | —                                                                  | Słownik typów nadwozia            |
| `body_type_wr_corrections`         | `samar_rv.py`                                        | —                                                                  | Korekty WR wg nadwozia            |
| `zabudowa_wr_corrections`          | `samar_rv.py`                                        | —                                                                  | Korekty WR wg zabudowy            |
| `paint_types`                      | `samar_rv.py`                                        | —                                                                  | Typy lakieru (metalik itp.)       |
| `koszty_opon`                      | `LTRSubCalculatorOpony.py`                           | `TabelaOponCrudPanel.tsx`                                          | Macierz cen opon                  |
| `tyre_configurations`              | `LTRSubCalculatorOpony.py`                           | `TabelaOponCrudPanel.tsx`                                          | Konfiguracje opon (klasy)         |
| `tabela_rabaty`                    | `pipeline_discounts.py`                              | `RabatyCrudPanel.tsx`                                              | Tabela rabatów dealerskich        |
| `control_center`                   | `samar_rv.py`, `LTRKalkulator.py` (pośrednio)        | —                                                                  | Parametry globalne systemu        |
| `ltr_admin_ubezpieczenia`          | `LTRKalkulator.py`                                   | —                                                                  | Stawki ubezpieczeniowe            |
| `ltr_admin_wspolczynniki_szkodowe` | `LTRKalkulator.py`                                   | —                                                                  | Współczynniki szkodowe            |
| `ltr_admin_korekta_wr_markas`      | `samar_rv.py`                                        | —                                                                  | Korekty WR wg marki               |
| `ltr_admin_korekta_wr_roczniks`    | `samar_rv.py`                                        | —                                                                  | Korekty WR wg rocznika            |
| `replacement_car_rates`            | `LTRKalkulator.py`                                   | —                                                                  | Stawki sam. zastępczego           |
| `LTRAdminParametry_czak`           | `LTRSubCalculatorOpony.py`                           | —                                                                  | Parametry admin (legacy)          |

## Tabele produkcyjne (schema: `reverse_search`)

| Tabela DB                      | Backend (`core/`)                                                            | Frontend | Opis                     |
| ------------------------------ | ---------------------------------------------------------------------------- | -------- | ------------------------ |
| `universal_features`           | `feature_importer.py`, `feature_enrichment.py`, `feature_cross_reference.py` | —        | Cechy uniwersalne        |
| `universal_feature_categories` | `feature_importer.py`                                                        | —        | Kategorie cech           |
| `universal_feature_aliases`    | `feature_importer.py`, `feature_enrichment.py`                               | —        | Aliasy nazw cech         |
| `vehicle_feature_evidence`     | `feature_resolver.py`, `feature_enrichment.py`, `feature_cross_reference.py` | —        | Dowody przypisania cech  |
| `vehicle_feature_state`        | `feature_resolver.py`, `feature_cross_reference.py`                          | —        | Stan cech pojazdu        |
| `vehicle_catalog_matches`      | `feature_cross_reference.py`                                                 | —        | Dopasowania katalogowe   |
| `model_document_sources`       | `feature_cross_reference.py`                                                 | —        | Źródła dokumentów modeli |
| `feature_import_runs`          | `feature_importer.py`                                                        | —        | Logi importów cech       |

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
