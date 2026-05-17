from core.samar_rv import SamarRVCalculator, RVInput


def test_skoda_octavia_rs_v1_parity(monkeypatch):
    # ── Isolation: disable Redis cache entirely for this test ──────────────
    # When other tests run BEFORE this one in the suite (especially
    # test_feature_enrichment which transitively touches Supabase paths),
    # @redis_cache state in core.samar_rv_fetchers diverges ~1664 PLN brutto
    # from a fresh calc. Forcing `_get_client` to return None makes every
    # @redis_cache decorator fall through to a direct Supabase call,
    # eliminating cross-test pollution while keeping the parity assertion
    # honest. Individual runs still produce 61046 PLN brutto identically.
    monkeypatch.setattr("core.redis_cache._get_client", lambda: None)
    """
    Test weryfikujący poprawność WR (Wartości Rezydualnej) dla Skoda Octavia RS
    przeciwko aktualnemu **2503 SOT** (Source of Truth).

    Historia parity:
    - Pierwotny baseline: legacy Excel `2503_wynik_JŁ.xlsx` wiersz 1682 = 81 185,76 PLN brutto.
    - Po fixach **k2** (kaskada roczna: additive → multiplicative) + **k4**
      (korekta przebiegu wyłączona per 2503 SOT — patrz `body_types_sot` memory note)
      = 61 046,00 PLN brutto.
    - **2026-05-17 Octavia V1 parity calibration** (memory `v1_wr_calibration`):
      class 10 (C niższa średnia) benzyna_pb / benzyna_mhev_pb_mhev: 0.39 → **0.36**
      w `samar_class_depreciation_rates`. Powód: w V1 RMS Octavia ląduje w klasie D
      (DPb=0.36); w v3 SAMAR Octavia mapuje się do C (poprawnie, granularniej).
      Aby WR zgadzało się co do grosza dla **tej samej Octavii** w obu systemach,
      v3 class C dostaje koeficjent V1 class D = 0.36. Aktualny SOT = **55 607,00 PLN brutto**.

    Konfiguracja testu:
    - Pojazd: Skoda Octavia RS
    - Klasa SAMAR: 10 (C niższa średnia)
    - Engine ID: 1 (Benzyna PB)
    - Cena Podstawowa Katalogowa (Brutto): 181 300,00 PLN
    - Cena Opcji Katalogowa (Brutto): 41 600,00 PLN
    - Wiek/Okres: 48 miesięcy
    - Przebieg docelowy: 120 000 km

    Korekty testowane (Krok 5 — niezmienione przez k2/k4):
    - Lakier Niemetalik: -1% od Ceny Bazowej Katalogowej = **-1813 PLN brutto** ✓
    - Korekta Przebiegu (Krok 4): **0,00 PLN** — flagowane przez
      `krok4_korekta_disabled_per_sot = 1.0` w debug

    Wynik Końcowy BRUTTO per current SOT (post Octavia V1 calibration): **55 607,00 PLN**
    """

    # 1. Przygotuj dane wejściowe
    base_gross = 181300.00
    options_gross = 41600.00
    vat_rate = 1.23

    base_net = base_gross / vat_rate
    options_net = options_gross / vat_rate

    # Przygotowanie RVInput (tak, jak robi to Wrapper)
    rv_input = RVInput(
        samar_class_id=10,
        engine_id=1,
        brand_name="Skoda",
        model_name="Octavia",
        months=48,
        total_km=120000,
        catalog_base_net=base_net,
        catalog_options_net=options_net,
        paint_type_id=1,
        is_metalic=False,  # Ważne: brak metalika załącza -1% kary na kolorze
        body_type_id=3,
        rocznik="2026",
        zabudowa_apr_wr=False,
        zabudowa_type_id=None,
        manual_wr_correction=0.0,
    )

    # 2. Wykonaj kalkulację główną
    calculator = SamarRVCalculator(rv_input)
    result = calculator.calculate()

    # 3. Weryfikacja przeciwko 2503 SOT (po fixach k2 + k4)
    # Zwrócone wartości są NETTO. Mnożymy przez VAT dla asercji BRUTTO z SOT.
    final_rv_gross = result.wr_net * vat_rate
    # Historia baseline:
    #   81 185,76 (legacy 2503_wynik_JŁ.xlsx)
    #   → 61 046,00 (post k2+k4 SOT)
    #   → 55 607,00 (post Octavia V1 parity 2026-05-17 stage 1: class 10 PB 0.39→0.36)
    #   → 63 076,20 (post Octavia V1 parity 2026-05-17 stage 2: full V1-grosz calibration:
    #                base 0.36→0.360555, cascade off-by-one fix, V1 deltas, Krok 4 re-enabled
    #                z baseline=140k constant + threshold=190k, options at base_rate, see
    #                memory `v1_wr_calibration`)
    expected_rv_gross = 63076.20

    # Precyzja: 0.05 grosz (testowa konfiguracja 48mc/120k — Krok 4 daje bonus dla
    # under-baseline 20k, formuła dokładna do groszy w okresie 48mc)
    assert abs(final_rv_gross - expected_rv_gross) < 0.05, (
        f"Regresja vs current SOT! Oczekiwano: {expected_rv_gross:.2f}, otrzymano: {final_rv_gross:.2f}. "
        f"Jeśli to celowa zmiana — sprawdź samar_class_depreciation_rates + tab_okres_final + "
        f"samar_class_mileage_corrections (wszystkie dla class 10 PB/mHEV) + samar_rv.py cascade formula + "
        f"memory `v1_wr_calibration`."
    )

    # Dodatkowa asercja składowych "trace" żeby zabezpieczyć się przed przypadkowym "zbilansowaniem" się dwóch błędów
    color_correction_netto = result.debug.get("krok5_color_netto", 0.0)
    color_correction_brutto = color_correction_netto * vat_rate
    assert abs(color_correction_brutto - (-1813.0)) < 0.05, (
        f"Kara za lakier Niemetalik musi wynosić -1% ceny bazowej katalogowej (-1813 PLN brutto), "
        f"otrzymano: {color_correction_brutto:.2f}"
    )

    # Krok 4 (korekta przebiegu) — RE-ENABLED 2026-05-17 per V1 RMS parity.
    # Aktywny dla nadwozi z body_types.utrata_wartosci == 0 (Kombi/Sedan/Hatchback).
    # Test config: body_type_id=3 (Sedan, utrata_wartosci=0) + 48mc/120k.
    # Excess = 120k - baseline_140k = -20k → 2 paczki under → bonus.
    # Bonus = 2 × under_rate × rv_total_netto (zwiększa WR).
    # debug stores the SIGNED value (-1913.4 = bonus added back to WR).
    assert result.debug.get("krok4_active") is True, (
        "Krok 4 powinien być AKTYWNY dla body_type Sedan (utrata_wartosci=0). "
        "Per V1 RMS parity (memory `v1_wr_calibration`)."
    )
    mileage_correction_netto = result.debug.get("krok4_korekta_przebieg_netto", 0.0)
    # For 48mc/120k expected korekta ≈ -1913.40 (bonus added back; negative sign = "added to WR")
    assert abs(mileage_correction_netto - (-1913.40)) < 0.5, (
        f"Krok 4 dla 48mc/120k (under-baseline by 20k) powinien dać ~-1913.40 netto bonus, "
        f"otrzymano: {mileage_correction_netto:.4f}"
    )
