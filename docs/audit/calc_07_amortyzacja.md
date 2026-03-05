# 7. AMORTYZACJA (Depreciation %) 📐

> V1: [LTRSubCalculatorAmortyzacja.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorAmortyzacja.cs) (53 linie)
> V3: [LTRSubCalculatorAmortyzacja.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorAmortyzacja.py) (63 linie)

---

## Mapowanie pól

| V1 C#                   | V3 Python     | Status |
| ----------------------- | ------------- | ------ |
| `WP` (CenaZakupu netto) | `wp` (float)  | ✅     |
| `WR` (WR netto)         | `wr` (float)  | ✅     |
| `Okres`                 | `okres` (int) | ✅     |

---

## Logika (IDENTYCZNA ✅)

```
utrataWartosci = WP - WR
kwotaAmortyzacji1Miesiac = utrataWartosci / Okres
procentAmortyzacji = kwotaAmortyzacji1Miesiac / WP
```

## Wynik

| `AmortyzacjaProcent` | → **(Ub)** do naliczania % deprecjacji podstawy AC |

---

## Status: ✅ ZGODNY — ZERO RÓŻNIC

V3 dodaje jedynie guard `if okres <= 0 or wp <= 0: return 0` (brak w V1).

---

## ⏸ Brak decyzji — kalkulator identyczny.
