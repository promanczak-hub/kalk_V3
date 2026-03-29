import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.samar_rv import SamarRVCalculator, RVInput, RVOutput


@pytest.fixture
def mock_rv_input():
    return RVInput(
        samar_class_id=1,
        engine_id=1,
        fuel_name="BENZYNA",
        brand_name="TEST_BRAND",
        model_name="TEST_MODEL",
        months=48,
        total_km=140000,
        catalog_base_net=100000.0,
        catalog_options_net=20000.0,
        paint_type_id=1,
        is_metalic=True,
        body_type_id=1,
        rocznik="current",
        zabudowa_apr_wr=True,
        zabudowa_type_id=2,
        manual_wr_correction=0.0,
    )


def test_samar_rv_calculate_base(mocker, mock_rv_input):
    """Testuje czy kalkulator wyliczy poprawnie RV wg uproszczonego V1 algorytmu na mockach"""
    # Base WR = 50% dla 4 roku
    mocker.patch.object(
        SamarRVCalculator,
        "_fetch_depreciation_rates",
        return_value={"km_140000": 0.50},
    )
    mocker.patch.object(SamarRVCalculator, "_fetch_brand_correction", return_value=0.0)
    mocker.patch.object(
        SamarRVCalculator, "_fetch_mileage_corrections", return_value=(0.0, 0.0, 140000)
    )
    mocker.patch.object(SamarRVCalculator, "_fetch_base_rv_percent", return_value=0.50)
    mocker.patch("core.samar_rv.fetch_base_options_rate_cached", return_value=0.80)
    mocker.patch.object(SamarRVCalculator, "fetch_color_correction", return_value=0.01)
    mocker.patch.object(SamarRVCalculator, "fetch_body_correction", return_value=0.02)
    mocker.patch.object(
        SamarRVCalculator, "fetch_zabudowa_correction", return_value=0.0
    )
    mocker.patch.object(SamarRVCalculator, "fetch_vintage_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_lo_param", return_value=0.0)

    calc = SamarRVCalculator(mock_rv_input)

    # Base: 50%
    # Options: 80% (0.8)
    # Wartość 48 miesięcy = 50% * 100k = 50k
    # Brak deprecjacji przebiegu (0.0 multiplier na under/over)
    # Opcje = 20k * 0.8 = 16k
    # Kolor = 100k * 0.01 = 1k
    # Zabudowa/Body = (100k + 20k) * 0.02 = 2.4k
    # RV = 50k + 16k + 1k + 2.4k = 69.4k

    output: RVOutput = calc.calculate()
    assert output.wr_net == pytest.approx(69400.0)


def test_samar_rv_sanity_bounds(mocker, mock_rv_input):
    """Sprawdzenie czy parametry zwracaja sie poprawnie przy 0% (edge case)"""
    mocker.patch.object(
        SamarRVCalculator,
        "_fetch_depreciation_rates",
        return_value={"km_140000": 0.0},
    )
    mocker.patch.object(SamarRVCalculator, "_fetch_brand_correction", return_value=0.0)
    mocker.patch.object(
        SamarRVCalculator, "_fetch_mileage_corrections", return_value=(0.0, 0.0, 140000)
    )
    mocker.patch.object(SamarRVCalculator, "_fetch_base_rv_percent", return_value=0.00)
    mocker.patch("core.samar_rv.fetch_base_options_rate_cached", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_color_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_body_correction", return_value=0.0)
    mocker.patch.object(
        SamarRVCalculator, "fetch_zabudowa_correction", return_value=0.0
    )
    mocker.patch.object(SamarRVCalculator, "fetch_vintage_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_lo_param", return_value=0.0)

    calc = SamarRVCalculator(mock_rv_input)

    # Suma to 0%, wiec final_rv_netto wynika tylko z opcji przez ułamek V1: 20000 / (1 + 4) = 4000
    rv_output = calc.calculate()
    assert rv_output.wr_net == pytest.approx(4000.0)
