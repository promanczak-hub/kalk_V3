# 9. FINANSE / PMT (Financial Costs) 🏦

> V1: [LTRSubCalculatorFinanse.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorFinanse.cs) (194 linie) + [PMT.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/PMT.cs) (51 linii)
> V3: [LTRSubCalculatorFinanse.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorFinanse.py) (75 linii)

---

## Mapowanie pól

| V1 C#                         | V3 Python                         | Status              |
| ----------------------------- | --------------------------------- | ------------------- |
| `WartoscPoczatkowaNetto`      | `total_capex`                     | ✅                  |
| `CzynszInicjalny / VAT`       | `upfront_pct / 100 × total_capex` | ⚠️ V1: kwota; V3: % |
| `WrPrzewidywanaCenaSprzedazy` | `rv_net`                          | ✅                  |
| `Okres`                       | `months`                          | ✅                  |
| `WIBORProcent`                | `wibor_pct`                       | ✅                  |
| `MarzaFinansowaProcent`       | `margin_pct`                      | ✅                  |

---

## Logika V1

### Formuła PMT (PMT.cs L15-L38)

```
kapital = -1 × kapitalDoSplaty
im = oprocentowanie / 12
imN = (1 + im)^pozostaloRat  // custom Pow function
pmt = ((kapital × imN + wykup) × im) / (1 - imN)
```

### Harmonogram (L138-L188)

```
wartoscKredytu = WP - (CzynszInicjalny / VAT)
wykupKwota = min(wartoscKredytu, WR)
oprocentowanie = WIBOR + MarzaFinansowa
→ DWA WARIANTY:
  1. zCzynszem: kredyt = WP - czynsz, wykup = min(kredyt, WR)
  2. bezCzynszu: kredyt = WP,           wykup = min(WP, WR)
→ Rozbicie na raty (kapitalowa + odsetkowa) per miesiąc
→ SumaOdsetek = Σ(rata odsetkowa)
```

### Logika V3

```
rate = (wibor + margin) / 100 / 12
pv = total_capex - upfront_value
fv = min(rv_net, pv)
pmt = (rate × (pv - fv / (1+rate)^n)) / (1 - (1+rate)^(-n))
total_interest = pmt × n - (pv - fv)
```

---

## Kluczowe różnice

| Kwestia          | V1                                               | V3                                                   | Decyzja                       |
| ---------------- | ------------------------------------------------ | ---------------------------------------------------- | ----------------------------- |
| Formuła PMT      | Customowa `((K×(1+im)^n + W)×im) / (1-(1+im)^n)` | Annuitetowa `(r×(PV - FV/(1+r)^n)) / (1-(1+r)^(-n))` | ⏸ **MOGĄ DAWAĆ INNE WYNIKI!** |
| Dwa warianty     | ✅ z czynszem + bez czynszu                      | ❌ tylko jeden wariant                               | 🔴                            |
| Harmonogram rat  | ✅ pełne rozbicie na raty                        | ❌ tylko agregat                                     | ⚠️                            |
| Czynsz inicjalny | kwota brutto → / VAT                             | `upfront_pct` (%) × capex                            | ⚠️ Inny model                 |
| Wykup            | `min(wartoscKredytu, WR)`                        | `min(rv_net, pv)`                                    | ✅                            |

---

## ⏸ Twoje decyzje

1. **Formuła PMT** — V1 i V3 używają **różnych wariantów** wzoru annuitetowego. Trzeba przetestować numerycznie czy dają te same wyniki!
2. **Dwa warianty** — V1 liczy z czynszem i bez. V3 tylko jeden. `SumaOdsetekBEZczynszu` jest potrzebna do `KosztDzienny.SYM`. Dodać?
3. **Czynsz: kwota vs %** — V1 przyjmuje kwotę brutto czynszu. V3 przyjmuje %. Czy to zamierzone?

<!-- Wklej screenshoty tutaj ↓ -->
