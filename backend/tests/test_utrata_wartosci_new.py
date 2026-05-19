import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew


class MockSettings:
    samar_rv_apply_color_correction = False
    samar_rv_apply_body_correction = False
    samar_rv_apply_options_depreciation = True
    samar_rv_base_mileage = 140000
    samar_rv_mileage_unit_km = 10000
    vat_rate = 1.23


class MockInputData:
    settings = MockSettings()


def test_utrata_wartosci_bez_czynszu_brutto_to_netto(mocker):
    """WR Brutto -> netto i UtrataWartosciBEZczynszu poprawna konwersja."""
    vehicle_data = {
        "Paliwo": "Benzyna",
        "Segment": "C",
        "MinRokProd": 2024,
        "samar_class_id": 1,
        "engine_type_id": 1,
        "fuel_name": "BENZYNA",
    }
    calc = LTRSubCalculatorUtrataWartosciNew(
        vehicle_data=vehicle_data, calc_input=MockInputData()
    )

    # Podmień VAT i LO na znane wartości
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.1

    # Mock SamarRVCalculator.calculate
    from core.samar_rv import RVOutput

    mock_rv_output = RVOutput(
        wr_net=91020.0 / 1.23,  # Result is netto in SamarRV
        wr_lo_net=0.0,
        utrata_wartosci_net=46000.0,
        wr_percent=0.0,
        debug={"krok1_wr_value_netto": 91020.0 / 1.23},
    )
    mocker.patch(
        "core.LTRSubCalculatorUtrataWartosciNew.SamarRVCalculator.calculate",
        return_value=mock_rv_output,
    )

    res = calc.calculate_values(
        months=36,
        total_km=60000,
        base_vehicle_catalog_gross=123000.0,
        options_catalog_gross=24600.0,
    )

    assert res["WR_Gross"] == pytest.approx(91020.0, 0.01)
    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(46000.0, 0.01)


def test_utrata_wartosci_zero_cut(mocker):
    """Utrata nie może być ujemna — max(0, ...)."""
    vehicle_data = {
        "Paliwo": "Benzyna",
        "Segment": "C",
        "MinRokProd": 2024,
        "samar_class_id": 1,
        "engine_type_id": 1,
        "fuel_name": "BENZYNA",
    }

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, MockInputData())
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.0

    from core.samar_rv import RVOutput

    mock_rv_output = RVOutput(
        wr_net=950.0, wr_lo_net=0.0, utrata_wartosci_net=50.0, wr_percent=0.0, debug={}
    )
    mocker.patch(
        "core.LTRSubCalculatorUtrataWartosciNew.SamarRVCalculator.calculate",
        return_value=mock_rv_output,
    )

    res = calc.calculate_values(36, 60000, 1000.0, 0.0)
    # Mock said utrata = 50.0 (netto), so we expect 50.0
    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(50.0, 0.01)


def test_wr_dla_lo(mocker):
    """WRdlaLO = WR_brutto * (1 + przewidywana_cena_lo%) / VAT."""
    vehicle_data = {
        "Paliwo": "Benzyna",
        "Segment": "C",
        "MinRokProd": 2024,
        "samar_class_id": 1,
        "engine_type_id": 1,
        "fuel_name": "BENZYNA",
    }

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, MockInputData())
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.1

    from core.samar_rv import RVOutput

    mock_rv_output = RVOutput(
        wr_net=100000.0,  # 123000 / 1.23
        wr_lo_net=110000.0,
        utrata_wartosci_net=0.0,
        wr_percent=0.0,
        debug={},
    )
    mocker.patch(
        "core.LTRSubCalculatorUtrataWartosciNew.SamarRVCalculator.calculate",
        return_value=mock_rv_output,
    )

    res = calc.calculate_values(36, 60000, 200000.0, 0.0)

    # WRdlaLOBrutto = 123000 * 1.1 = 135300
    # WRdlaLONetto  = 135300 / 1.23 = 110000.0
    assert res["WR_Gross"] == pytest.approx(123000.0, 0.01)
    assert res["WRdlaLO"] == pytest.approx(110000.0, 0.01)


def test_manual_wr_correction(mocker):
    """Korekta ręczna WR dodawana do WR brutto (×VAT)."""
    vehicle_data = {
        "Paliwo": "Benzyna",
        "Segment": "C",
        "MinRokProd": 2024,
        "samar_class_id": 1,
        "engine_type_id": 1,
        "fuel_name": "BENZYNA",
    }

    class InputWithCorrection:
        settings = MockSettings()
        manual_wr_correction = 1000.0  # 1000 netto korekty

    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, InputWithCorrection())
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.0

    from core.samar_rv import RVOutput

    mock_rv_output = RVOutput(
        wr_net=41650.41,  # 51230 / 1.23
        wr_lo_net=0.0,
        utrata_wartosci_net=0.0,
        wr_percent=0.0,
        debug={},
    )
    mocker.patch(
        "core.LTRSubCalculatorUtrataWartosciNew.SamarRVCalculator.calculate",
        return_value=mock_rv_output,
    )

    res = calc.calculate_values(36, 60000, 100000.0, 0.0)

    # WR brutto = 50000 + 1000 * 1.23 = 51230
    assert res["WR_Gross"] == pytest.approx(51230.0, 0.01)


def _mock_samar_rv(mocker, utrata_net: float) -> None:
    """Helper: mockuje SamarRVCalculator.calculate na zadanym utrata_net."""
    from core.samar_rv import RVOutput

    mocker.patch(
        "core.LTRSubCalculatorUtrataWartosciNew.SamarRVCalculator.calculate",
        return_value=RVOutput(
            wr_net=50000.0,
            wr_lo_net=0.0,
            utrata_wartosci_net=utrata_net,
            wr_percent=0.0,
            debug={},
        ),
    )


def _make_calc() -> LTRSubCalculatorUtrataWartosciNew:
    """Helper: tworzy WR calculator z minimalnym pojazdem."""
    vehicle_data = {
        "Paliwo": "Benzyna",
        "Segment": "C",
        "MinRokProd": 2024,
        "samar_class_id": 1,
        "engine_type_id": 1,
        "fuel_name": "BENZYNA",
    }
    calc = LTRSubCalculatorUtrataWartosciNew(vehicle_data, MockInputData())
    calc.vat_rate = 1.23
    calc.przewidywana_cena_lo = 0.0
    return calc


def test_utrata_z_czynszem_default_zero(mocker):
    """Domyślny czynsz=0 ⇒ UtrataZCzynszem == UtrataBezCzynszu."""
    _mock_samar_rv(mocker, utrata_net=46000.0)
    calc = _make_calc()

    res = calc.calculate_values(36, 60000, 123000.0, 24600.0)

    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(46000.0, 0.01)
    assert res["UtrataWartosciZCzynszemInicjalnym"] == pytest.approx(46000.0, 0.01)


def test_utrata_z_czynszem_reduces_pool(mocker):
    """Czynsz inicjalny netto redukuje pulę amortyzacji (V1 cs:54-55)."""
    _mock_samar_rv(mocker, utrata_net=46000.0)
    calc = _make_calc()

    res = calc.calculate_values(
        36, 60000, 123000.0, 24600.0, czynsz_inicjalny_netto=10000.0
    )

    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(46000.0, 0.01)
    assert res["UtrataWartosciZCzynszemInicjalnym"] == pytest.approx(36000.0, 0.01)


def test_utrata_z_czynszem_floor_zero(mocker):
    """Gdy czynsz > utrata, wynik nie schodzi poniżej 0."""
    _mock_samar_rv(mocker, utrata_net=5000.0)
    calc = _make_calc()

    res = calc.calculate_values(
        36, 60000, 123000.0, 24600.0, czynsz_inicjalny_netto=20000.0
    )

    assert res["UtrataWartosciBEZczynszu"] == pytest.approx(5000.0, 0.01)
    assert res["UtrataWartosciZCzynszemInicjalnym"] == pytest.approx(0.0, abs=1e-9)
