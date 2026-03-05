# 3. SAMOCHÓD ZASTĘPCZY (Replacement Car) 🚗

> V1: [LTRSubCalculatorSamochodZastepczy.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorSamochodZastepczy.cs) (104 linie)
> V3: [LTRSubCalculatorSamochodZastepczy.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorSamochodZastepczy.py) (42 linie)

---

## Mapowanie pól

| V1 C#                                          | V3 Python                            | Supabase                                      | Status |
| ---------------------------------------------- | ------------------------------------ | --------------------------------------------- | ------ |
| `SamochodZastepczy` (bool)                     | `enabled`                            | UI input                                      | ✅     |
| `KlasaId` (z Modelu)                           | `samar_class_id`                     | `replacement_car_rates.samar_class_id`        | ✅     |
| `LTRAdminStawkaZastepczy.SredniaIloscDobWRoku` | `rate_data["average_days_per_year"]` | `replacement_car_rates.average_days_per_year` | ✅     |
| `LTRAdminStawkaZastepczy.DobaNetto`            | `rate_data["daily_rate_net"]`        | `replacement_car_rates.daily_rate_net`        | ✅     |
| `Okres`                                        | `months`                             | input                                         | ✅     |

---

## Logika V1 (L64)

```
stawka = SredniaIloscDobWRoku × DobaNetto × okres / 12
```

## Logika V3

```
years = months / 12.0
total_days = average_days_per_year × years
total_cost = total_days × daily_rate_net
```

> ✅ **IDENTYCZNA** — V1: `dni × stawka × lata` = V3: `dni × stawka × lata`

---

## Status: ✅ ZGODNY

Jedyna różnica — V1 ma fallback do parametrów (`StawkaZaZastepczy`), V3 pobiera z dedykowanej tabeli `replacement_car_rates` per klasa SAMAR.

---

## ⏸ Twoje decyzje

1. **Tabela stawek** — czy `replacement_car_rates` ma poprawne dane? Pokaż screenshot.
2. **Fallback** — V1 miał `_tabele.Parametry.StawkaZaZastepczy` jako zapasowy. V3 nie ma fallbacku. Potrzebny?

<!-- Wklej screenshoty tutaj ↓ -->
