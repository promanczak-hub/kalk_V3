# 8. UBEZPIECZENIE (Insurance) 🛡️

> V1: [LTRSubCalculatorUbezpieczenie.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorUbezpieczenie.cs) (270 linii)
> V3: [LTRSubCalculatorUbezpieczenie.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorUbezpieczenie.py) (148 linii)

---

## Mapowanie pól

| V1 C#                                         | V3 Python                                  | Supabase                                    | Status    |
| --------------------------------------------- | ------------------------------------------ | ------------------------------------------- | --------- |
| `LICZBA_LAT = 7`                              | `LICZBA_LAT = 7`                           | —                                           | ✅        |
| `CenaZakupu` (netto)                          | `base_price`                               | input                                       | ✅        |
| `AmortyzacjaProcent`                          | `amortization_pct`                         | z calc #7                                   | ✅        |
| `LTRAdminUbezpieczenie[rok].StawkaBazowaAC`   | `insurance_rates[rok]["StawkaBazowaAC"]`   | `v1_admin_ubezpieczenie.stawka_bazowa_ac`   | ✅        |
| `LTRAdminUbezpieczenie[rok].SkladkaOC`        | `insurance_rates[rok]["SkladkaOC"]`        | `v1_admin_ubezpieczenie.skladka_oc_wartosc` | ✅        |
| `DoubezpieczenieKradziezy` (param)            | `ins_theft_doub_pct`                       | `control_center`                            | ✅ ale ⚠️ |
| `NaukaJazdy` (param)                          | `ins_driving_school_doub_pct`              | `control_center`                            | ✅ ale ⚠️ |
| `_kalkulacja.DoubezpieczenieKradziezy` (bool) | **HARDCODED `False`**                      | —                                           | 🔴        |
| `_kalkulacja.NaukaJazdy` (bool)               | **HARDCODED `False`**                      | —                                           | 🔴        |
| `SredniaWartoscSzkody` (param)                | `ins_avg_damage_value`                     | `control_center`                            | ✅        |
| `SredniPrzebiegDlaSzkody` (param)             | `ins_avg_damage_mileage`                   | `control_center`                            | ✅        |
| `WspolczynnikiSzkodowe.WspSredniPrzebieg`     | `damage_coefficients["WspSredniPrzebieg"]` | `ubezpieczenie_wspolczynniki_szkodowe`      | ✅        |
| `WspolczynnikiSzkodowe.WspWartoscSzkody`      | `damage_coefficients["WspWartoscSzkody"]`  | `ubezpieczenie_wspolczynniki_szkodowe`      | ✅        |
| `ExpressPlaciUbezpieczenie` (bool)            | **❌ BRAK** (zawsze liczy)                 | —                                           | ⚠️        |
| `KorektaKosztuUbezpieczenia` + kwota          | **❌ BRAK**                                | —                                           | 🔴        |
| `KlasaId` → filtr stawek                      | `klasa_samar` → filtr stawek               | `v1_admin_ubezpieczenie.klasa_samar`        | ✅        |

---

## Logika — PĘTLA 7 LAT

### V1 (L64-L107)

```
for rok = 1..7:
    podstawa = CenaZakupu × (1 - (rok-1)×12 × amortyzacja%)
    składkaAC = round(stawkaBazowaAC × podstawa)
    składkaOC = stała z tabeli
    doubezpKradziezy = składkaAC × %kradzież (jeśli zaznaczeno)
    doubezpNaukaJazdy = składkaAC × %naukaJazdy (jeśli zaznaczono)
    składkaRoczna = getSkladkaRoczna(suma, pro-rata za okres)
    szkodowość = getSredniaWartoscSzkodyRok(...)
    składkaŁącznie = roczna + szkodowość
    if (ExpressPłaci && rok obejmuje okr): sumaCałościowa += Σ
```

### V3 (L20-L147)

```
for year = 1..7:
    depreciation_factor = 1 - (year-1)×12 × amortyzacja%
    podstawa = base_price × depreciation_factor
    składkaAC = round(stawka × podstawa)
    doubezp_kradzież = 0 (HARDCODED False)  ← ⚠️
    doubezp_nauka = 0 (HARDCODED False)     ← ⚠️
    ... (pro-rata identyczna)
    if months > v2: total += składka_łączna
```

---

## Kluczowe różnice

| Kwestia                      | V1                       | V3                                    | Decyzja              |
| ---------------------------- | ------------------------ | ------------------------------------- | -------------------- |
| Doubezpieczenie kradzieży    | Warunkowo z UI           | HARDCODED `False`                     | ⏸ Trzeba podpiąć UI! |
| Doubezpieczenie nauka jazdy  | Warunkowo z UI           | HARDCODED `False`                     | ⏸ Trzeba podpiąć UI! |
| Korekta kosztu ubezpieczenia | ✅ dodaje korektę ręczną | ❌ BRAK                               | ⏸                    |
| ExpressPlaciUbezpieczenie    | ✅ warunkowo liczy       | ❌ zawsze liczy                       | ⏸                    |
| Fallback stawek              | `throw Exception`        | Miękkie lądowanie (ostatni znany rok) | ✅ (lepiej w V3)     |
| Tabele                       | `KlasaId` (int)          | `klasa_samar` (text)                  | ⚠️ Inny typ klucza   |

---

## ⏸ Twoje decyzje

1. **Doubezpieczenia** — Czy checkbox „kradzież" i „nauka jazdy" powinien być w UI?
2. **ExpressPlaciUbezpieczenie** — W V1 było warunkowe. V3 zawsze liczy. Czy poprawnie?
3. **Korekta ręczna ubezpieczenia** — Potrzebna?
4. **Pokaż tabelę** `v1_admin_ubezpieczenie` — czy dane są poprawne?

<!-- Wklej screenshoty tutaj ↓ -->
