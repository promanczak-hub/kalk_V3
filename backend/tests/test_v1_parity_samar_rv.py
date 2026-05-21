from core.samar_rv import SamarRVCalculator, RVInput


def test_skoda_octavia_rs_v1_parity(monkeypatch):
    # ── Isolation: disable Redis cache entirely for this test ──────────────
    # Forcing `_get_client` to return None makes every @redis_cache decorator
    # fall through to a direct Supabase call, eliminating cross-test pollution.
    monkeypatch.setattr("core.redis_cache._get_client", lambda: None)
    """
    Weryfikacja WR (Wartości Rezydualnej) Skody Octavia RS przeciwko
    **2005 SOT** — arkusz `2005_wynik_SAMAR_PANCZAK.xlsx`, karta `Kalkulator_V3`
    wiersz 51 (decyzja usera 2026-05-21: 2005 Excel = SOT kalkulatora WR).

    Formuła Excela (BI51), liczona w BRUTTO:
        base_RV   = J(cena bazowa) × WR_klasa%(0,39)           = 70 707
        opcje_RV  = U(opcje) × stawka_opcji_rok4(0,24)         =  9 984
        BE        = base_RV + opcje_RV                          = 80 691
        przebieg  = AF(0,0143) × BE × (Δkm/10)  [BE, nie rv_total]
        BI        = BE − przebieg + (lakier% × J)               = 81 185,76
    gdzie dla 48mc/120k: Δkm = MIN(120,190)−140 = −20 → bonus +2 307,76;
    lakier niemetalik = −1% × 181 300 = −1 813.

    Konfiguracja:
        klasa SAMAR 10 (C niższa średnia), silnik 1 (Benzyna PB),
        cena bazowa brutto 181 300, opcje brutto 41 600,
        48 mc / 120 000 km, lakier niemetalik, rocznik bieżący (vintage 0).

    Wynik końcowy: WR net 66 004,69 → **81 185,76 PLN brutto** (36,42 %).

    Historia (przed 2005 SOT): legacy 81 185,76 → kalibracja V1 RMS
    (base 0,39→0,360555, opcje Path-B, przebieg 0,014642) zjechała do 63 076,20;
    2005 SOT przywraca Excel dla klasy 10 PB/mHEV.
    """

    # 1. Dane wejściowe (brutto → netto, jak robi to Wrapper)
    base_gross = 181300.00
    options_gross = 41600.00
    vat_rate = 1.23

    rv_input = RVInput(
        samar_class_id=10,
        engine_id=1,
        brand_name="Skoda",
        model_name="Octavia",
        months=48,
        total_km=120000,
        catalog_base_net=base_gross / vat_rate,
        catalog_options_net=options_gross / vat_rate,
        paint_type_id=1,  # Niemetalizowany → -1% kary na kolorze
        is_metalic=False,
        body_type_id=3,  # Sedan (utrata_wartosci=0 → Krok 4 aktywny)
        rocznik="current",  # bieżący → vintage 0 (Excel H51='bieżący')
        zabudowa_apr_wr=False,
        zabudowa_type_id=None,
        manual_wr_correction=0.0,
    )

    # 2. Kalkulacja
    result = SamarRVCalculator(rv_input).calculate()
    final_rv_gross = result.wr_net * vat_rate

    # 3. Wynik końcowy = 2005 SOT (Excel BI51)
    expected_rv_gross = 81185.76
    assert abs(final_rv_gross - expected_rv_gross) < 0.10, (
        f"Regresja vs 2005 SOT! Oczekiwano: {expected_rv_gross:.2f}, "
        f"otrzymano: {final_rv_gross:.2f}. Sprawdź samar_class_depreciation_rates "
        f"(benzyna_pb=0.39), samar_class_options_rv (Y4=0.24), "
        f"samar_class_mileage_corrections (PB=0.0143/0.03) dla klasy 10."
    )

    # 4. Asercje składowych (zabezpieczenie przed zbilansowaniem się dwóch błędów)
    # Base RV% = 0,39 (Excel TAB.WR KLASA, klasa C / PB)
    assert abs(result.debug.get("krok1_effective_pct", 0.0) - 0.39) < 1e-6, (
        f"Base RV% musi = 0,39 (2005 SOT), otrzymano {result.debug.get('krok1_effective_pct')}"
    )

    # Opcje amortyzowane WŁASNĄ stawką 0,24 (Path A — Excel TAB.DOPOSAŻENIA), nie base%
    assert abs(result.debug.get("krok3_options_rate_used", 0.0) - 0.24) < 1e-6, (
        f"Stawka opcji musi = 0,24 (rok 4), otrzymano {result.debug.get('krok3_options_rate_used')}"
    )

    # Lakier niemetalik = -1% ceny bazowej katalogowej (-1813 brutto)
    color_brutto = result.debug.get("krok5_color_netto", 0.0) * vat_rate
    assert abs(color_brutto - (-1813.0)) < 0.05, (
        f"Kara za lakier niemetalik musi = -1813 brutto, otrzymano {color_brutto:.2f}"
    )

    # Korekta przebiegu na BE, under_rate=0,0143: 2 paczki under → bonus ~-1876,23 netto
    mileage_netto = result.debug.get("krok4_korekta_przebieg_netto", 0.0)
    assert result.debug.get("krok4_active") is True, "Krok 4 powinien być AKTYWNY (Sedan)"
    assert abs(mileage_netto - (-1876.23)) < 0.5, (
        f"Krok 4 (48mc/120k, under 20k, 0,0143) ~-1876,23 netto, otrzymano {mileage_netto:.2f}"
    )

    # Rocznik bieżący → 0 (Excel ROCZNIK 'bieżący')
    assert abs(result.debug.get("krok6_vintage_pct", 0.0)) < 1e-9, (
        f"Vintage 'current' musi = 0, otrzymano {result.debug.get('krok6_vintage_pct')}"
    )
