# 5. CENA ZAKUPU (Purchase Price / CAPEX) 💰

> V1: [LTRSubCalculatorCenaZakupu.cs](file:///C:/Users/proma/Downloads/kalkulator_V1_extracted/kalkulator_V1/LTRSubCalculatorCenaZakupu.cs) (166 linii)
> V3: [LTRSubCalculatorCenaZakupu.py](file:///d:/kalk_v3/backend/core/LTRSubCalculatorCenaZakupu.py) (94 linie)

---

## Mapowanie pól

| V1 C#                            | V3 Python                              | Status             |
| -------------------------------- | -------------------------------------- | ------------------ |
| `CenaCennikowa` (brutto)         | `base_price_net` (netto)               | ⚠️ Inne jednostki! |
| `OpcjeFabryczne` (lista brutto)  | `options[is_service=False]` (netto)    | ⚠️                 |
| `RabatProcent`                   | `discount_pct`                         | ✅                 |
| `OplataTransportowa` (brutto)    | **❌ BRAK**                            | 🔴                 |
| `OpcjeKatalogoweNierabatowane`   | `options[is_discountable=False]`       | ✅                 |
| `OpcjaSerwisowas` (brutto)       | `options[is_service=True]`             | ✅                 |
| `CzyGPS` → `CenaGSM + MontazGSM` | `add_gsm_device` + `gsm_hardware_cost` | ✅                 |
| `Koszt1KplOpon × VAT`            | **❌ BRAK** (opony osobno)             | ⚠️                 |
| `PakietSerwisowyNetto × VAT`     | `pakiet_serwisowy_net`                 | ✅                 |

---

## Logika V1 (L47-L107, BRUTTO)

```
1. opcjeFabr = Σ(OpcjeFabryczne.CenaCennikowa)
2. cenaCatalogue = CenaCennikowa + opcjeFabr
3. poRabacie = (cenaCatalogue - transport - nierabatowane) × (1 - rabat%) + transport + nierabatowane
4. opcjeSerwisowe = Σ(OpcjaSerwisowas) + [GSM brutto]
5. CAPEX = poRabacie + opcjeSerwisowe + oponyBrutto + pakietSerwisowyBrutto
6. Wynik NETTO = CAPEX / VAT
```

## Logika V3 (netto-based)

```
1. discounted_base = base_price_net × (1 - discount%)
2. discountable_opts = Σ(opts where discountable and not service) × (1 - discount%)
3. non_discountable_opts = Σ(opts where not discountable)
4. service_opts = Σ(opts where is_service)
5. CAPEX = discounted_base + discountable_opts_discounted + non_discountable + service + pakiet_serwisowy + [GSM]
```

---

## Kluczowe różnice

| Kwestia        | V1                                                          | V3                                              | Decyzja          |
| -------------- | ----------------------------------------------------------- | ----------------------------------------------- | ---------------- |
| Jednostki      | BRUTTO → wynik / VAT = netto                                | NETTO od początku                               | ⏸ Zmiana modelu! |
| Transport      | ✅ `OplataTransportowa` (nie podlega rabatowi)              | ❌ BRAK                                         | ⏸                |
| Opony w CAPEX  | ✅ `Koszt1KplOpon × VAT` dodany do CAPEX                    | ❌ BRAK (opony wchodzą inaczej?)                | ⏸                |
| Rabat          | `(cena - transport - nierab) × (1-r%) + transport + nierab` | `base × (1-r%) + disc_opts × (1-r%) + non_disc` | ⚠️ Inna formuła! |
| Wynik pośredni | `CenaBezOpon_OpcjiSerw_iPakietu` → do UtW                   | BRAK odpowiednika                               | ⏸                |

---

## ⏸ Twoje decyzje

1. **Brutto vs Netto** — V1 liczy w brutto i konwertuje. V3 od razu w netto. Czy to OK?
2. **Transport** — Czy potrzebna opłata transportowa?
3. **Opony w CAPEX** — V1 dodaje `Koszt1KplOpon` do CAPEX. Czy V3 robi to samo (via `capex_initial_set`)?
4. **Pokaż jak wprowadzasz opcje fabryczne i serwisowe w UI** — żebym mógł zweryfikować mapowanie.

<!-- Wklej screenshoty tutaj ↓ -->
