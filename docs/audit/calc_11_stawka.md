# 11. STAWKA (Monthly Rate / Margin) 💵

> V1: [LTRSubCalculatorStawka.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorStawka.cs) (311 linii)
> V3: [LTRSubCalculatorStawka.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorStawka.py) (252 linie)

---

## Mapowanie pól

| V1 C#                            | V3 Python                           | Status |
| -------------------------------- | ----------------------------------- | ------ |
| `Marza` (decimal)                | `marza_pct`                         | ✅     |
| `KosztMC` / `KosztMcBEZcz`       | `koszt_mc` / `koszt_mc_bez_czynszu` | ✅     |
| `KosztyFinansoweNetto` (odsetki) | `koszty_finansowe_netto`            | ✅     |
| `UtrataWartosciNetto`            | `utrata_wartosci_netto`             | ✅     |
| `UbezpieczenieNetto`             | `ubezpieczenie_netto`               | ✅     |
| `SamochodZastepczyNetto`         | `samochod_zastepczy_netto`          | ✅     |
| `KosztyDodatkoweNetto`           | `koszty_dodatkowe_netto`            | ✅     |
| `OponyNetto`                     | `opony_netto`                       | ✅     |
| `SerwisNetto`                    | `serwis_netto`                      | ✅     |
| `Okres`                          | `okres`                             | ✅     |
| `CzynszInicjalny`                | — (logika: if czynsz=0 → KosztMC)   | ✅     |
| `MarzaKosztFinansowyProcent`     | `marza_koszt_finansowy_pct`         | ✅     |
| `MarzaUbezpieczenieProcent`      | `marza_ubezpieczenie_pct`           | ✅     |
| `MarzaSamochodZastepczyProcent`  | `marza_samochod_zastepczy_pct`      | ✅     |
| `MarzaSerwisProcent`             | `marza_serwis_pct`                  | ✅     |
| `MarzaOponyProcent`              | `marza_opony_pct`                   | ✅     |
| `MarzaKosztyDodatkoweProcent`    | `marza_koszty_dodatkowe_pct`        | ✅     |

---

## Logika V1 = V3 (ZGODNA)

```
1. podstawaMarzy = (czynsz=0) ? KosztMC : KosztMcBEZcz
2. marzaMC = podstawaMarzy × (1/(1-marza%)) - podstawaMarzy
3. Dla 6 kosztów (Fin, Ubezp, Zast, Serwis, Opony, Admin):
   - KosztMC = KosztyLaczne / Okres
   - RozkladMarzy = KosztMC / (sumaMC)
   - RozkladMarzyKorekta = override ?? RozkladMarzy
   - KwotaMarzy = marzaMC × RozkladMarzy
   - KwotaMarzyKorekta = marzaMC × RozkladMarzyKorekta
   - KosztPlusMarza = KosztMC + KwotaMarzy
   - KosztPlusMarzaKorekta = KosztMC + KwotaMarzyKorekta
4. czynszFinansowy = kosztFinansowy.KosztPlusMarzaKorekta
5. czynszTechniczny = Σ(tech.KosztPlusMarzaKorekta)
6. OferowanaStawka = czynszFinansowy + czynszTechniczny
```

---

## Status: ✅ ZGODNY

V3 jest pełnym portem V1 z rozkładem marży na 6 składników. Kluczowy punkt: wynik końcowy `OferowanaStawka` w `LTRKalkulator.cs` (L407) jest zaokrąglany w górę do pełnych PLN — sprawdzić czy V3 robi to samo.

---

## ⏸ Twoje decyzje

1. **Zaokrąglanie** — V1: `Math.Ceiling(oferowanaStawka)`. Czy V3 zaokrągla tak samo?
2. **Symulacja SYM** — V1 liczy symulowane stawki (BEZ czynszu). Czy V3 to robi?

<!-- Wklej screenshoty tutaj ↓ -->
