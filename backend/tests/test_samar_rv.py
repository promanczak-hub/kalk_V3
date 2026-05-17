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
    """Testuje czy kalkulator wyliczy poprawnie RV wg V1-aligned algorytmu.

    Post 2026-05-17 (V1 RMS parity calibration):
    - Path B: opcje × base_rate (= 0.50) zamiast osobnego options_rate
    - Krok 4 (przebieg) aktywny tylko gdy body_correction == 0 (Kombi/Sedan); tu body=0.02 → DISABLED
    - Krok 5 (kolor/body) ADDITIVE
    """
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
    mocker.patch.object(SamarRVCalculator, "fetch_color_correction", return_value=0.01)
    mocker.patch.object(SamarRVCalculator, "fetch_body_correction", return_value=0.02)
    mocker.patch.object(SamarRVCalculator, "fetch_vintage_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_lo_param", return_value=0.0)

    calc = SamarRVCalculator(mock_rv_input)

    # Path B kalkulacja:
    # Base × base_pct = 100k × 0.50 = 50k
    # Opcje × base_pct = 20k × 0.50 = 10k (Path B: same rate as base)
    # rv_total = 60k
    # Krok 4: body_correction=0.02 ≠ 0 → DISABLED (mileage neutral)
    # Krok 5: kolor = 100k × 0.01 = 1k, body = 100k × 0.02 = 2k → sum = 3k
    # rv_pre_manual = 60k + 3k = 63k
    # Vintage = 0, Manual = 0 → final = 63k

    output: RVOutput = calc.calculate()
    assert output.wr_net == pytest.approx(63000.0)


def test_samar_rv_sanity_bounds(mocker, mock_rv_input):
    """Edge case: wszystkie rates = 0 → WR = 0 (post Path B: brak fallbacku opcje/(1+years))."""
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
    mocker.patch.object(SamarRVCalculator, "fetch_color_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_body_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_vintage_correction", return_value=0.0)
    mocker.patch.object(SamarRVCalculator, "fetch_lo_param", return_value=0.0)

    calc = SamarRVCalculator(mock_rv_input)

    # Path B: opcje × base_pct (0) = 0. Brak fallbacku.
    # Krok 4: body=0 → aktywny ALE under_rate=over_rate=0 → korekta=0
    # WR = 0
    rv_output = calc.calculate()
    assert rv_output.wr_net == pytest.approx(0.0)
