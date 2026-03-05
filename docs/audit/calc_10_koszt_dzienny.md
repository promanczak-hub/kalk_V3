# 10. KOSZT DZIENNY (Daily Cost) 📅

> V1: [LTRSubCalculatorKosztDzienny.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorKosztDzienny.cs) (91 linii)
> V3: [LTRSubCalculatorKosztDzienny.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorKosztDzienny.py) (99 linii)

---

## Mapowanie pól

| V1 C#                                 | V3 Python                     | Status |
| ------------------------------------- | ----------------------------- | ------ |
| `COEFF_KOSZT_DZIENNY = 30.4m`         | `COEFF_KOSZT_DZIENNY = 30.4`  | ✅     |
| `UtrataWartosciZczynszem`             | `utrata_wartosci_z_czynszem`  | ✅     |
| `UtrataWartosciBEZczynszu`            | `utrata_wartosci_bez_czynszu` | ✅     |
| `KosztFinansowy` (odsetki z czynszem) | `koszt_finansowy`             | ✅     |
| `SamochodZastepczyNetto`              | `samochod_zastepczy_netto`    | ✅     |
| `KosztyDodatkoweNetto`                | `koszty_dodatkowe_netto`      | ✅     |
| `UbezpieczenieNetto`                  | `ubezpieczenie_netto`         | ✅     |
| `OponyNetto`                          | `opony_netto`                 | ✅     |
| `SerwisNetto`                         | `serwis_netto`                | ✅     |
| `SumaOdsetekBezCzynszuInicjalnego`    | `suma_odsetek_bez_czynszu`    | ✅     |

---

## Logika (IDENTYCZNA ✅)

```
lacznyKosztFinansowy = KosztFinansowy + UtrataWartościZczynszem
lacznyKosztTechniczny = Zastępczy + Dodatkowe + Ubezpieczenie + Opony + Serwis
kosztyOgolem = fin + tech
kosztyMiesiac = kosztyOgolem / Okres
kosztDzienny = kosztyMiesiac / 30.4

// Symulacja BEZ czynszu:
SYM_fin = UtrataWartościBEZczynszu + SumaOdsetekBezCzynszu
SYM_ogolem = SYM_fin + tech
SYM_mc = SYM_ogolem / Okres
```

---

## Status: ✅ ZGODNY — ZERO RÓŻNIC

> ⚠️ Ale: V3 potrzebuje `suma_odsetek_bez_czynszu` z kalkulatora #9 (Finanse). Jeśli V3 liczy tylko jeden wariant PMT, to brakuje danych do symulacji. Patrz: → `calc_09_finanse.md`.

---

## ⏸ Brak decyzji — kalkulator identyczny. Ale zależy od poprawności wejść.
