# 2. KOSZTY DODATKOWE (Additional Costs) 📋

> V1: [LTRSubCalculatorKosztyDodatkowe.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorKosztyDodatkowe.cs) (180 linii)
> V3: [LTRSubCalculatorKosztyDodatkowe.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorKosztyDodatkowe.py) (42 linie)

---

## Mapowanie pól V1 C# → V3 Python → Supabase

| V1 C#                                    | V3 Python                                | Supabase / ControlCenter                       | Status                                     |
| ---------------------------------------- | ---------------------------------------- | ---------------------------------------------- | ------------------------------------------ |
| `CzyGPS` (bool)                          | `input_data.add_gsm_subscription`        | UI input                                       | ✅                                         |
| `AbonamentGPS` (Kwota/mc)                | `settings.cost_gsm_subscription_monthly` | `control_center.cost_gsm_subscription_monthly` | ✅                                         |
| `CenaUrzadzeniaGSM`                      | `settings.cost_gsm_device`               | `control_center.cost_gsm_device`               | ✅                                         |
| `MontazUrzadzeniaGSM`                    | `settings.cost_gsm_installation`         | `control_center.cost_gsm_installation`         | ✅                                         |
| `Hak` (bool)                             | `input_data.add_hook_installation`       | UI input                                       | ✅                                         |
| `HakHolowniczy` (Kwota)                  | `settings.cost_hook_installation`        | `control_center.cost_hook_installation`        | ✅                                         |
| `ZarejestrowanieKartaPojazdu`            | `settings.cost_registration`             | `control_center.cost_registration`             | ✅                                         |
| `PrzygotowanieDoSprzedazyLtr`            | `settings.cost_sales_prep`               | `control_center.cost_sales_prep`               | ⚠️ V1 = korekta×klasa×przebieg; V3 = flat. |
| `KosztWymontowaniaKraty`                 | `settings.cost_grid_dismantling`         | `control_center.cost_grid_dismantling`         | ✅                                         |
| `ElementyRyczaltowe` (tabela)            | **❌ BRAK w V3**                         | —                                              | 🔴                                         |
| `KosztZabudowy` (tabela)                 | **❌ BRAK w V3**                         | —                                              | 🔴                                         |
| Korekta przygotowania (klasa × przebieg) | **❌ Uproszczono**                       | —                                              | ⚠️                                         |

---

## Logika V1

### GSM (L70-L88)

```
if (CzyGPS):
    abonament = AbonamentGPS × okres
    urzadzenie = CenaUrządzenia / 6 × (okres / 12)
    montaz = MontazUrządzenia
    suma += abonament + urzadzenie + montaz
```

### Przygotowanie do sprzedaży (L129-L152)

```
if (LTR):
    wartoscPrzygotowania = korektaKlasa × korektaPrzebieg × PrzygotowanieDoSprzedazyLtr
else:
    wartoscPrzygotowania = PrzygotowanieDoSprzedazyRacMtr
```

> ⚠️ **V3 uproszczono**: `settings.cost_sales_prep` — bez korekty klasa/przebieg!

### Elementy ryczałtowe (L91-L106) ← **BRAK W V3**

```
for each element:
    if (typOpłaty == PerMc): suma += stawkaMc × okres
    if (typOpłaty == PadXXkm): suma += stawka × (przebieg / 10000)
```

### Koszty zabudowy (L108-L127) ← **BRAK W V3**

```
if (hasZabudowa):
    suma += (okres / 12) × KosztZabudowyNettoRok
```

---

## V3 — co jest inaczej / brakuje

| Kwestia                    | V1                         | V3                     | Decyzja |
| -------------------------- | -------------------------- | ---------------------- | ------- |
| Elementy ryczałtowe        | ✅ tabela dynamiczna       | ❌ BRAK                | ⏸       |
| Koszty zabudowy            | ✅ wg klasy budowy         | ❌ BRAK                | ⏸       |
| Przygotowanie do sprzedaży | korekta × klasa × przebieg | flat `cost_sales_prep` | ⏸       |
| Demontaż kraty             | stała z parametrów         | stała z ControlCenter  | ✅      |

---

## ⏸ Twoje decyzje

1. **Elementy ryczałtowe** — Czy potrzebne w V3? Jeśli tak, potrzebuję zdefiniować tabelę.
2. **Koszty zabudowy** — Czy V3 obsługuje zabudowy (np. chłodnie, boksy)?
3. **Przygotowanie do sprzedaży** — Czy flat value wystarczy, czy potrzebujemy korekty wg klasy i przebiegu?

<!-- Wklej screenshoty tutaj ↓ -->
