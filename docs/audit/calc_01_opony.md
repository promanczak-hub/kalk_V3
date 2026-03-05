# 1. OPONY (Tires) 🛞

> V1: [LTRSubCalculatorOpony.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorOpony.cs) (223 linii)
> V3: [LTRSubCalculatorOpony.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorOpony.py) (254 linii)

---

## Mapowanie pól V1 C# → V3 Python → Supabase

| V1 C#                            | V3 Python                                         | Supabase tabela.kolumna                                           | Status                                                   |
| -------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------- |
| `ZOponami` (bool)                | `z_oponami`                                       | input z UI                                                        | ✅                                                       |
| `KlasaOpon` (string)             | `klasa_opony_string` → `tire_column_name`         | input z UI dropdown                                               | ✅                                                       |
| `RozmiarOpon.Srednica`           | `srednica_felgi` (int)                            | input z UI                                                        | ✅                                                       |
| `PozycjaCennikaOpon` (cennik)    | `_fetch_tire_cost()`                              | `koszty_opon.{kolumna_klasy}` WHERE `srednica=?`                  | ⚠️ V1 szuka wg "Budżet" marki, V3 szuka wg kolumny klasy |
| `OponyPrzekladki` (param)        | `swap_cost`                                       | `LTRAdminParametry_czak.col_2` WHERE `col_1='OponyPrzekladki'`    | ✅                                                       |
| `OponyPrzechowywane` (param)     | `storage_cost_per_year`                           | `LTRAdminParametry_czak.col_2` WHERE `col_1='OponyPrzechowywane'` | ✅                                                       |
| `StawkaVAT` (param)              | `vat_rate`                                        | `LTRAdminParametry_czak.col_2` WHERE `col_1='VAT'`                | ✅                                                       |
| `KosztOponKorekta` / VAT         | `koszt_opon_korekta / vat_rate`                   | input z UI                                                        | ✅                                                       |
| `LiczbaKompletowOpon` (override) | `sets_needed_override`                            | input z UI                                                        | ✅                                                       |
| progi schodkowe (hardcoded w V1) | `_fetch_tire_configurations()`                    | `tyre_configurations.config_key/value`                            | ✅ Lepiej w V3 (z bazy)                                  |
| `OdkupOpon` (cennik)             | **❌ BRAK w V3**                                  | (brak tabeli)                                                     | 🔴 NIE ZAIMPLEMENTOWANO                                  |
| `AutoLiczbaOpon` (bool)          | domyślnie auto, override = `sets_needed_override` | —                                                                 | ✅                                                       |

---

## Logika V1 (z linią kodu C#)

### Krok 1: Koszt 1 kompletu (L117-L141)

```
koszt1kompletu = PozycjaCennikaOpon[Srednica, KlasaOpon, marka="Budżet"].CenaCennikowa
if (KorektaKosztuOpon):
    koszt1kompletu += KosztOponKorekta / VAT
```

### Krok 2: Ilość kompletów (L143-L183)

**Wielosezonowe:**
| Przebieg | Ilość |
|----------|-------|
| ≤ 60 000 | 1 |
| ≤ 120 000 | 2 |
| ≤ 180 000 | 3 |
| ≤ 240 000 | 4 |
| ≤ 300 000 | 5 |
| > 300 000 | 6 |

**Sezonowe:**
| Przebieg | Ilość |
|----------|-------|
| ≤ 120 000 | 1 |
| ≤ 180 000 | 2 |
| ≤ 240 000 | 3 |
| ≤ 300 000 | 4 |
| > 300 000 | 5 |

### Krok 3: Łączny koszt hardware (L185-L220)

```
if (autoLiczbaOpon):
    wielosezon: koszt + ((przebieg - 60k) / 60k) × koszt
    sezonowe:   koszt + ((przebieg - 120k) / 60k) × koszt
else:
    ilość_override × koszt
```

### Krok 4: Przekładki (L80-L88)

```
wielosezon: ceil(przebieg / 60k) × costPrzekladki
sezonowe:   costPrzekladki × lata × 2
```

### Krok 5: Przechowywanie (L90-L96)

```
wielosezon: 0
sezonowe:   costPrzechowywanie × lata × 2
```

### Krok 6: Odkup opon (L98-L115) ← **BRAK W V3**

```
if (OdkupOpon):
    odkup = PozycjaCennikaOpon[marka="Odkup opon"].CenaCennikowa
```

### Wynik końcowy

```
OponyNetto = łącznyKosztOpon + przekładki + przechowywanie - odkup
Koszt1KplOpon = koszt1kompletu  → CAPEX (via CenaZakupu)
```

---

## V3 — co jest inaczej / brakuje

| Kwestia           | V1                                                     | V3                                           | Decyzja                     |
| ----------------- | ------------------------------------------------------ | -------------------------------------------- | --------------------------- |
| Źródło cen opon   | `PozycjaCennikaOpon` (cennik zewnętrzny)               | `koszty_opon` (tabela z kolumnami per klasa) | ⏸                           |
| Odkup opon        | ✅ (z cennika)                                         | ❌ BRAK                                      | ⏸                           |
| Progi schodkowe   | hardcoded w CS                                         | z bazy `tyre_configurations`                 | ✅ (lepiej)                 |
| Mnożnik ceny (×4) | cena za 1 komplet (4 szt. razem)                       | `unit_price × 4` (cena za 1 sztukę × 4)      | ⏸ Uwaga: inny model cenowy! |
| CAPEX split       | V1: `Koszt1KplOpon` trafia do `CenaZakupu` jako brutto | V3: `capex_initial_set`                      | ✅                          |

---

## ⏸ Twoje decyzje (wklej screenshot / odpowiedz)

1. **Odkup opon** — Potrzebny w V3? Jeśli tak, potrzebuję tabelę w Supabase.
2. **Model cenowy** — V1 pobiera cenę za komplet. V3 pobiera cenę za 1 sztukę i mnoży ×4. Pokaż mi jak wygląda tabela `koszty_opon` w Supabase — czy to cena za 1 szt. czy za komplet?
3. **Marka "Budżet"** — W V1 cennik filtrował po `marka="Budżet"`. W V3 filtrujemy po kolumnie klasy. Czy to zamierzone uproszczenie?

<!-- Wklej screenshoty tutaj ↓ -->
