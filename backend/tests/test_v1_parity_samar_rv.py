from core.samar_rv import SamarRVCalculator, RVInput


def test_skoda_octavia_rs_v1_parity():
    """
    Test weryfikujący poprawność zrównania matematycznego (V1 Parity) z oryginalnym legacy Excelem
    (plik: 2503_wynik_JŁ.xlsx, Wiersz: 1682).

    Konfiguracja testu:
    - Pojazd: Skoda Octavia RS
    - Klasa SAMAR: 10
    - Model/Silnik ID: 1
    - Cena Podstawowa Katalogowa (Brutto): 181 300,00 PLN
    - Cena Opcji Katalogowa (Brutto): 41 600,00 PLN
    - Wiek/Okres: 48 miesięcy
    - Przebieg docelowy: 120 000 km

    Korekty testowane:
    - Lakier: Niemetalik (brak dopłaty lub zniżka - w tym przypadku kara -1% od Ceny Podstawowej) = -1813 PLN
    - Korekta Przebiegu: Ułamek 3/14 (poniżej progu), bazujący na wartości po amortyzacji z tabeli. Wymuszona kwota: +2307.76 PLN

    Wynik Końcowy BRUTTO z Excela (Wartość Końcowa RV): 81 185,76 PLN
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

    # 3. Weryfikacja
    # Zwrócone wartości są NETTO. Mnożymy przez VAT dla asercji BRUTTO z Excela.
    final_rv_gross = result.wr_net * vat_rate
    expected_rv_gross = 81185.76

    # Precyzja do dwóch miejsc po przecinku (2 grosze marginesu błędu)
    assert abs(final_rv_gross - expected_rv_gross) < 0.05, (
        f"Regresja V1 Parity! Oczekiwano: {expected_rv_gross:.2f}, otrzymano: {final_rv_gross:.2f}"
    )

    # Dodatkowa asercja składowych "trace" żeby zabezpieczyć się przed przypadkowym "zbilansowaniem" się dwóch błędów
    color_correction_netto = result.debug.get("krok5_color_netto", 0.0)
    color_correction_brutto = color_correction_netto * vat_rate
    assert abs(color_correction_brutto - (-1813.0)) < 0.05, (
        "Kara za lakier Niemetalik musi wynosić -1% ceny bazowej katalogowej (-1813 PLN)"
    )

    mileage_correction_netto = result.debug.get("krok4_korekta_przebieg_netto", 0.0)
    mileage_correction_brutto = mileage_correction_netto * vat_rate
    # Zgodnie ze wzorem: (stawka_under * RV_Total * ((przebieg-prog)/10000)) -> -2307.76
    assert abs(mileage_correction_brutto - (-2307.76)) < 0.05, (
        "Korekta przebiegu netto z matematycznego koszyka paczek musi opiewać na -2307.76 PLN"
    )
