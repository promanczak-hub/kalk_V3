# 6. UTRATA WARTOŚCI (Residual Value / Depreciation) 📉

> V1: [LTRSubCalculatorUtrataWartosci.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorUtrataWartosci.cs) (544 linii — **NAJKOMPLEKSOWSZY**)
> V3: [LTRSubCalculatorUtrataWartosciNew.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorUtrataWartosciNew.py) (110 linii) + [samar_rv.py](file:///d:/kalk_v3/backend/core/samar_rv.py)

---

## Kluczowa zmiana architektury

| Aspekt              | V1                                        | V3                                          |
| ------------------- | ----------------------------------------- | ------------------------------------------- |
| Źródło danych RV    | **TabelaEurotax** (WpisTabelaEuroTax)     | **SAMAR** (samar_base_rv + korekty)         |
| Korekta za przebieg | LTRKorektaEtax (4 ćwiartki)               | `samar_mileage_thresholds` (wielopoziomowe) |
| Korekta admin       | naukaJazdy + brakMetalika + kombi         | korekta koloru + nadwozia (SAMAR)           |
| Korekta RV dla LTR  | tabela WRLTR (klasa-paliwo)               | **❌ BRAK**                                 |
| WR dla wyposażenia  | formuła deprecjacji doposażenia           | `samar_options_depreciation`                |
| Interpolacja ET     | GetCenaUzywanego / GetCenaUzywanegoMinus1 | brak — SAMAR daje % wprost                  |

---

## Supabase tabele (V3)

| Tabela                       | Rola                                |
| ---------------------------- | ----------------------------------- |
| `samar_base_rv`              | Bazowe % RV wg klasy SAMAR i okresu |
| `samar_brand_corrections`    | Korekty wg marki                    |
| `samar_vintage_depreciation` | Korekta za rocznik                  |
| `samar_options_depreciation` | Deprecjacja opcji                   |
| `samar_mileage_thresholds`   | Progi przebiegowe                   |
| `samar_color_depreciation`   | Korekta za kolor                    |
| `samar_body_depreciation`    | Korekta za typ nadwozia             |

---

## Logika V1 (skrót)

```
1. cenaUzywanego = interpolacja(TabelaEurotax, okres) / interpolacja(...,0) × cenaCennikNetto
2. WR_wyposażenia = (opcjeFabr + opcjeSerw) / (1 + okres/12) × (1 + startMc/12)
3. przebiegNormatywny = TabelaPrzebieg[symbolEtax, miesiace] / miesiace
4. nadprzebieg = normatywny×okres - przebiegKoncowy
5. korekta_przebieg = cenaUzyw × mnożnik(4 ćwiartki) × (nadprzebieg/100k)
6. WR_poKorekciePrzebieg = cenaUzyw + WR_wyposaż + korekta_przebieg
7. korekta_admin = naukaJazdy% + brakMetalika% + kombi%
8. korekta_RV_LTR = WRLTR[klasa-paliwo].KorektaRVNetto
9. WR = WR_poKorekcje × (1 - admin%) + korektaRV_LTR [+ brakSerwisu mnożnik]
10. UtrataWartości = CAPEX + sumaOpcji - WR
```

## Logika V3 (uproszczona)

```
1. WR_brutto = SamarRVCalculator.calculate_rv(months, km, capex, options)
   → wewnętrznie: bazowe_rv% × korekcje (marka, rocznik, kolor, nadwozie, opcje, przebieg)
2. WR += korekta_ręczna × VAT
3. Clamp WR do 5-95% ceny zakupu
4. WR_netto = WR_brutto / VAT
5. WR_LO = WR × (1 + PrzewidywanaCenaSprzedazyLO)
6. Utrata = max(CAPEX - WR, 0) / VAT
```

---

## Kluczowe różnice

| Kwestia                       | V1                         | V3                                       | Decyzja             |
| ----------------------------- | -------------------------- | ---------------------------------------- | ------------------- |
| Model RV                      | Eurotax + korekty manualne | SAMAR + korekty tabelaryczne             | ⏸ **CELOWA zmiana** |
| Korekta naukaJazdy            | ✅                         | ❌                                       | ⏸                   |
| Korekta brakMetalika          | ✅ z DSU                   | ❌ (ale jest `samar_color_depreciation`) | ⏸                   |
| Korekta kombi                 | ✅ z DSU                   | ❌ (ale jest `samar_body_depreciation`)  | ⏸                   |
| Korekta RV LTR (klasa-paliwo) | ✅ tabela WRLTR            | ❌ BRAK                                  | 🔴                  |
| Clamp 5-95%                   | ❌                         | ✅ w V3                                  | 🆕                  |
| PrzewidywanaCenaSprzedazy LO  | ✅                         | ✅                                       | ✅                  |

---

## ⏸ Twoje decyzje

1. **SAMAR vs Eurotax** — Potwierdź że V3 celowo używa SAMAR zamiast Eurotax.
2. **Korekta RV dla LTR** — V1 miał tabelę `WRLTR` (klasa+paliwo → korektaRVNetto). Brak w V3. Potrzebna?
3. **Clamp 5-95%** — To nowe zabezpieczenie w V3, nie istnieje w V1. Akceptujesz?
4. **Pokaż tabele SAMAR w Supabase** — żebym mógł zweryfikować poprawność danych.

<!-- Wklej screenshoty tabel SAMAR tutaj ↓ -->
