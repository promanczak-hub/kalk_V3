# 12. BUDŻET MARKETINGOWY (Marketing Budget) 📢

> V1: [LTRSubCalculatorBudzetMarketingowy.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorBudzetMarketingowy.cs) (46 linii)
> V3: [LTRSubCalculatorBudzetMarketingowy.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorBudzetMarketingowy.py) (46 linii)

---

## Mapowanie pól

| V1 C#                                 | V3 Python                        | Supabase                  | Status |
| ------------------------------------- | -------------------------------- | ------------------------- | ------ |
| `WRPrzewidywanaCenaSprzedazy` (netto) | `wr_przewidywana_cena_sprzedazy` | z calc #6                 | ✅     |
| `StawkaVAT`                           | `stawka_vat`                     | `control_center.vat_rate` | ✅     |
| `BudzetMarketingowyLtr`               | `budzet_marketingowy_ltr`        | `LTRAdminParametry_czak`  | ✅     |

---

## Logika (IDENTYCZNA ✅)

```
korektaWRMaksBrutto = WR × StawkaVAT × BudzetMarketingowyLtr
```

---

## Status: ✅ ZGODNY — ZERO RÓŻNIC

Najprostszy kalkulator. Jedna mnożenie.

---

## ⏸ Brak decyzji — kalkulator identyczny.
