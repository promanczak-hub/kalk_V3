import pytest
from unittest.mock import MagicMock
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew


def test_utrata_wartosci_bez_czynszu_brutto_to_netto():
    # Arrange
    vehicle_data = {"Paliwo": "Benzyna", "Segment": "C", "MinRokProd": 2024}

    # Mockujemy input_data - w uproszczeniu jako zwykły obiekt z atrybutami
    class MockInputData:
        class Settings:
            samar_rv_apply_color_correction = False
            samar_rv_apply_body_correction = False
            samar_rv_apply_options_depreciation = True
            samar_rv_base_mileage = 140000
            samar_rv_mileage_unit_km = 10000

        settings = Settings()

    calc = LTRSubCalculatorUtrataWartosciNew(
        vehicle_data=vehicle_data, calc_input=MockInputData()
    )

    # Podmieniamy wywołania bazy na mocki, by testować czystą matematykę
    calc.class_config = {"mileage_cutoff_threshold": 190000}
    calc.get_base_rv_48 = MagicMock(return_value=0.50)
    calc.get_brand_correction = MagicMock(return_value=0.0)
    calc.get_vintage_depreciation = MagicMock(return_value=0.08)
    calc.get_options_depreciation_percent = MagicMock(return_value=1.0)
    calc.get_color_correction = MagicMock(return_value=0.0)
    calc.get_body_correction = MagicMock(return_value=0.0)
    calc.get_mileage_correction = MagicMock(
        return_value={
            "lower_threshold_km": 140000.0,
            "upper_threshold_km": 190000.0,
            "penalty_below_upper_percent": 0.0,
            "penalty_above_upper_percent": 0.0,
            "step_km": 10000.0,
        }
    )

    # Mockujemy pobranie parametrów z bazy by zwróciło 1.23 na VAT oraz 0.05 na LO %
    calc._fetch_global_param = MagicMock(
        side_effect=lambda name, fallback: (
            1.23
            if "VAT" in name
            else (0.1 if "PrzewidywanaCenaSprzedazyLO" in name else fallback)
        )
    )

    # Act
    # Przyjmijmy:
    # months = 36 (3 years)
    # total_km = 60000
    # base_vehicle_capex (brutto po rabacie) = 123000 (czyli 100000 net)
    # options_capex (brutto po rabacie) = 24600 (czyli 20000 net)

    # Oczekiwane WR Brutoo: 123000 * 0.50 = 61500
    # Wiek 3 lata -> 61500 * 1.08 = 66420.0
    # Opcje = 24600 * 1.0 = 24600.0
    # suma = 91020.0
    # Utrata Wartości netto
    # Utrata brutto = 147600 - 91020 = 56580.0
    # Utrata netto = 56580 / 1.23 = 46000.0

    res = calc.calculate_values(
        months=36,
        total_km=60000,
        base_vehicle_capex_gross=123000.0,
        options_capex_gross=24600.0,
    )

    # Weryfikacja różnicy
    assert res["WR_Gross"] == pytest.approx(91020.0, 0.01)
    # Utrata Wartości netto
    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(46000.0, 0.01)


def test_utrata_wartosci_zero_cut():
    vehicle_data = {"Paliwo": "Benzyna", "Segment": "C", "MinRokProd": 2024}

    class MockInputData:
        class Settings:
            samar_rv_apply_color_correction = False
            samar_rv_apply_body_correction = False
            samar_rv_apply_options_depreciation = False
            samar_rv_base_mileage = 140000
            samar_rv_mileage_unit_km = 10000

        settings = Settings()

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, MockInputData())
    calc._fetch_global_param = MagicMock(return_value=1.23)  # VAT

    # Wymuszamy, żeby WR było wyższe niż cena
    # Cena: 1000, WR: 2000 => Utrata: 0.0
    calc._calculate_wr_gross = MagicMock(return_value=2000.0)

    res = calc.calculate_values(36, 60000, 1000.0, 0.0)

    assert res["UtrataWartosciBEZczynszu"] == 0.0


def test_wr_dla_lo():
    vehicle_data = {"Paliwo": "Benzyna", "Segment": "C", "MinRokProd": 2024}

    class MockInputData:
        class Settings:
            samar_rv_apply_color_correction = False
            samar_rv_apply_body_correction = False
            samar_rv_apply_options_depreciation = False
            samar_rv_base_mileage = 140000
            samar_rv_mileage_unit_km = 10000

        settings = Settings()

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, MockInputData())

    # Assign directly to bypass __init__ ordering issues for test
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.1
    calc._calculate_wr_gross = MagicMock(return_value=123000.0)

    res = calc.calculate_values(36, 60000, 200000.0, 0.0)

    # WRdlaLOBrutto = 123000.0 * 1.1 = 135300.0
    # WRdlaLONetto = 135300.0 / 1.23 = 110000.0
    assert res["WR_Gross"] == 123000.0
    assert res["WRdlaLO"] == pytest.approx(110000.0, 0.01)
