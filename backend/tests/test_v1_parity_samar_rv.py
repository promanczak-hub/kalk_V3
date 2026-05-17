from core.samar_rv import SamarRVCalculator, RVInput


def test_skoda_octavia_rs_v1_parity():
    # ── Isolation: bust Redis cache for samar_rv:* keys ────────────────────
    # When other tests run BEFORE this one in the suite (e.g. test_feature_enrichment
    # transitively triggers Supabase calls via different paths), the @redis_cache
    # state in core.samar_rv_fetchers gets populated with values that diverge
    # ~1664 PLN brutto from a fresh calc. Forcing a cache flush at test start
    # makes the test deterministic regardless of suite ordering. Individual
    # runs still produce 61046 PLN brutto identically.
    try:
        from core.redis_cache import cache_invalidate_pattern
        cache_invalidate_pattern("samar_rv:*")
    except Exception:
        # Redis unavailable in test env → @redis_cache falls through to direct
        # function call anyway, so no-op is safe.
        pass
    """
    Test weryfikujący poprawność WR (Wartości Rezydualnej) dla Skoda Octavia RS
    przeciwko aktualnemu **2503 SOT** (Source of Truth).

    Historia parity:
    - Pierwotny baseline: legacy Excel `2503_wynik_JŁ.xlsx` wiersz 1682 = 81 185,76 PLN brutto.
    - Po fixach **k2** (kaskada roczna: additive → multiplicative) + **k4**
      (korekta przebiegu wyłączona per 2503 SOT — patrz `body_types_sot` memory note)
      aktualny SOT = **61 046,00 PLN brutto**.
    - Tabela `body_types.utrata_wartosci` (Supabase) jest single source of truth dla
      korekt nadwozia + przebiegu zamiast wcześniejszego rozproszenia w samar_rv.py.

    Konfiguracja testu:
    - Pojazd: Skoda Octavia RS
    - Klasa SAMAR: 10
    - Model/Silnik ID: 1
    - Cena Podstawowa Katalogowa (Brutto): 181 300,00 PLN
    - Cena Opcji Katalogowa (Brutto): 41 600,00 PLN
    - Wiek/Okres: 48 miesięcy
    - Przebieg docelowy: 120 000 km

    Korekty testowane (Krok 5 — niezmienione przez k2/k4):
    - Lakier Niemetalik: -1% od Ceny Bazowej Katalogowej = **-1813 PLN brutto** ✓
    - Korekta Przebiegu (Krok 4): **0,00 PLN** — flagowane przez
      `krok4_korekta_disabled_per_sot = 1.0` w debug

    Wynik Końcowy BRUTTO (Wartość Końcowa RV) per 2503 SOT: **61 046,00 PLN**
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
    expected_rv_gross = 61046.00  # 2503 SOT (post k2+k4); poprzednio 81185.76 (legacy 2503_wynik_JŁ.xlsx)

    # Precyzja do dwóch miejsc po przecinku (2 grosze marginesu błędu)
    assert abs(final_rv_gross - expected_rv_gross) < 0.05, (
        f"Regresja vs 2503 SOT! Oczekiwano: {expected_rv_gross:.2f}, otrzymano: {final_rv_gross:.2f}. "
        f"Jeśli to celowa zmiana — sprawdź k2/k4 logic + zaktualizuj test + Golden Rule + body_types_sot memory note."
    )

    # Dodatkowa asercja składowych "trace" żeby zabezpieczyć się przed przypadkowym "zbilansowaniem" się dwóch błędów
    color_correction_netto = result.debug.get("krok5_color_netto", 0.0)
    color_correction_brutto = color_correction_netto * vat_rate
    assert abs(color_correction_brutto - (-1813.0)) < 0.05, (
        f"Kara za lakier Niemetalik musi wynosić -1% ceny bazowej katalogowej (-1813 PLN brutto), "
        f"otrzymano: {color_correction_brutto:.2f}"
    )

    # Korekta przebiegu (Krok 4) jest WYŁĄCZONA per 2503 SOT.
    # Po konsolidacji korekt do body_types.utrata_wartosci (memory `body_types_sot`)
    # samar_rv.py nie liczy już mileage correction tutaj.
    mileage_correction_netto = result.debug.get("krok4_korekta_przebieg_netto", 0.0)
    assert abs(mileage_correction_netto) < 0.01, (
        f"Krok 4 (korekta przebiegu) musi być wyłączony per 2503 SOT (0.0 netto), "
        f"otrzymano: {mileage_correction_netto:.4f}. "
        f"Sprawdź flagę `krok4_korekta_disabled_per_sot` w debug — powinna być True."
    )

    # Verify the explicit SOT-disable flag is set (defense in depth — catches
    # an accidental re-enabling of Krok 4 even if value happens to be 0.0 by coincidence)
    assert result.debug.get("krok4_korekta_disabled_per_sot") == 1.0, (
        "Flaga `krok4_korekta_disabled_per_sot` musi być ustawiona na 1.0 — "
        "Krok 4 jest celowo wyłączony per 2503 SOT, korekty przebiegu w body_types.utrata_wartosci"
    )
