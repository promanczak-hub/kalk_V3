import pytest
from unittest.mock import MagicMock
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew


class MockSettings:
    samar_rv_apply_color_correction = False
    samar_rv_apply_body_correction = False
    samar_rv_apply_options_depreciation = True
    samar_rv_base_mileage = 140000
    samar_rv_mileage_unit_km = 10000


class MockInputData:
    settings = MockSettings()


def test_utrata_wartosci_bez_czynszu_brutto_to_netto():
    """WR Brutto -> netto i UtrataWartosciBEZczynszu poprawna konwersja."""
    vehicle_data = {"Paliwo": "Benzyna", "Segment": "C", "MinRokProd": 2024}

    calc = LTRSubCalculatorUtrataWartosciNew(
        vehicle_data=vehicle_data, calc_input=MockInputData()
    )

    # Podmień VAT i LO na znane wartości
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.1

    # Mock rv_engine.calculate_rv -> zwraca znane WR brutto
    # Scenariusz:
    #   base_vehicle_capex_gross  = 123000 (100k netto)
    #   options_capex_gross       = 24600  (20k netto)
    #   RV brutto z SamarRV       = 91020
    #   Utrata brutto = 147600 - 91020 = 56580
    #   Utrata netto  = 56580 / 1.23 ≈ 46000
    calc.rv_engine.calculate_rv = MagicMock(return_value=91020.0)

    res = calc.calculate_values(
        months=36,
        total_km=60000,
        base_vehicle_capex_gross=123000.0,
        options_capex_gross=24600.0,
    )

    assert res["WR_Gross"] == pytest.approx(91020.0, 0.01)
    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(46000.0, 0.01)


def test_utrata_wartosci_zero_cut():
    """Utrata nie może być ujemna — max(0, ...)."""
    vehicle_data = {"Paliwo": "Benzyna", "Segment": "C", "MinRokProd": 2024}

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, MockInputData())
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.0

    # WR wyższe niż cena => utrata = 0
    # Ale clamp: 95% z 1000 = 950 → WR = 950
    calc.rv_engine.calculate_rv = MagicMock(return_value=2000.0)

    res = calc.calculate_values(36, 60000, 1000.0, 0.0)

    # Clamped to 95% of 1000 = 950, utrata = max(1000 - 950, 0) = 50
    # Netto = 50 / 1.23 ≈ 40.65
    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(50.0 / 1.23, 0.01)


def test_wr_dla_lo():
    """WRdlaLO = WR_brutto * (1 + przewidywana_cena_lo%) / VAT."""
    vehicle_data = {"Paliwo": "Benzyna", "Segment": "C", "MinRokProd": 2024}

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, MockInputData())
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.1

    # RV brutto = 123000, po clamp wewnątrz 5-95% z 200k = [10k, 190k] → OK
    calc.rv_engine.calculate_rv = MagicMock(return_value=123000.0)

    res = calc.calculate_values(36, 60000, 200000.0, 0.0)

    # WRdlaLOBrutto = 123000 * 1.1 = 135300
    # WRdlaLONetto  = 135300 / 1.23 = 110000.0
    assert res["WR_Gross"] == 123000.0
    assert res["WRdlaLO"] == pytest.approx(110000.0, 0.01)


def test_manual_wr_correction():
    """Korekta ręczna WR dodawana do WR brutto (×VAT)."""
    vehicle_data = {"Paliwo": "Benzyna", "Segment": "C", "MinRokProd": 2024}

    class InputWithCorrection:
        settings = MockSettings()
        manual_wr_correction = 1000.0  # 1000 netto korekty

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, InputWithCorrection())
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.0

    # RV brutto z engine = 50000
    calc.rv_engine.calculate_rv = MagicMock(return_value=50000.0)

    res = calc.calculate_values(36, 60000, 100000.0, 0.0)

    # WR brutto = 50000 + 1000 * 1.23 = 51230
    assert res["WR_Gross"] == pytest.approx(51230.0, 0.01)
