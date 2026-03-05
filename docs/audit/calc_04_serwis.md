# 4. SERWIS (Service) 🔧

> V1: [LTRSubCalculatorSerwis.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorSerwis.cs) (279 linii)
> V3: [LTRSubCalculatorSerwisNew.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorSerwisNew.py) (179 linii) — **NOWY algorytm**

---

## Mapowanie pól

| V1 C#                              | V3 Python                                      | Supabase                                | Status                |
| ---------------------------------- | ---------------------------------------------- | --------------------------------------- | --------------------- |
| `CzyUwzgledniaSerwisowanie` (bool) | `z_serwisem`                                   | UI                                      | ✅                    |
| `TabelaSerwisowa` (cennik)         | **❌ usunięto** — zastąpiono stawką za km      | `samar_service_costs`                   | 🟡 ZMIENIONY ALGORYTM |
| `PakietSerwisowyNetto`             | `pakiet_serwisowy`                             | input                                   | ✅                    |
| `InneKosztySerwisowania`           | `inne_koszty_serwisowania_netto`               | input                                   | ✅                    |
| `KorektaSerwisProcent` (param)     | **❌ BRAK**                                    | —                                       | 🔴                    |
| `KosztPrzegladuPodstawowego`       | **❌ BRAK**                                    | —                                       | 🔴                    |
| —                                  | `samar_class_id`, `engine_type_id`, `power_kw` | `samar_service_costs`                   | 🆕 Nowe w V3          |
| —                                  | `normatywny_przebieg_mc` (floor)               | `control_center.normatywny_przebieg_mc` | 🆕                    |

---

## Logika V1 (L161-L273)

```
1. Pobierz TabelaSerwisowa (cennik wg przebiegów)
2. Oblicz koszty z overlap przebiegu (sumaZKosztowPrzebiegu)
3. Doliczy brakujące przeglądy podstawowe
4. Korekta admin % (KorektaSerwisProcent)
5. Jeśli PakietSerwisowy > 0 → wynik = pakiet + inneKoszty
6. Inaczej → kosztyZPrzebiegu + inneKoszty - korektaAdmin
```

## Logika V3 (nowa)

```
1. Jeśli pakiet_serwisowy > 0 → koszt = pakiet / okres
2. Inaczej:
   effective_km = max(przebieg, normatywny_przebieg_mc × okres)
   stawka = samar_service_costs[samar_class, engine_type, power_band]
   koszt = effective_km × stawka / okres
3. Zawsze: + inne_koszty_serwisowania_netto
```

---

## Kluczowe różnice

| Kwestia              | V1                                   | V3                               | Decyzja             |
| -------------------- | ------------------------------------ | -------------------------------- | ------------------- |
| Algorytm             | Tabela serwisowa z overlap przebiegu | Stawka za km z SAMAR             | ⏸ **CELOWA zmiana** |
| Floor przebiegu      | brak                                 | `normatywny_przebieg_mc × okres` | 🆕                  |
| Korekta admin %      | ✅ z parametrów                      | ❌ brak                          | ⏸                   |
| Przeglądy podstawowe | ✅ dolicza brakujące                 | ❌ nie istnieje                  | ⏸                   |
| Power band           | nie istnieje                         | LOW/MID/HIGH wg kW               | 🆕                  |

---

## ⏸ Twoje decyzje

1. **Algorytm** — Czy zmiana z "tabeli serwisowej" na "stawka za km z SAMAR" jest celowa i zaakceptowana?
2. **Korekta admin %** — Potrzebna w V3?
3. **Przeglądy podstawowe** (brakujące przeglądy) — Potrzebne w V3?

<!-- Wklej screenshoty tabeli samar_service_costs ↓ -->
