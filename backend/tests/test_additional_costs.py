import os
import sys

# Dodajemy PYTHONPATH aby pytest widzial 'core':
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator
from core.models import ControlCenterSettings


@pytest.fixture
def mock_settings() -> ControlCenterSettings:
    return ControlCenterSettings(
        default_wibor=5.8,
        default_ltr_margin=2.0,
        vat_rate=0.23,
        bank_spread=0.01,
        samar_segment_b_adjustment=1,
        samar_segment_c_adjustment=1,
        samar_segment_d_adjustment=1,
        value_threshold_1=100000,
        value_threshold_2=200000,
        resale_time_days=60,
        inventory_financing_cost=0.05,
        samar_rv_apply_color_correction=False,
        samar_rv_apply_body_correction=False,
        samar_rv_apply_options_depreciation=False,
        samar_rv_base_mileage=15000,
        samar_rv_mileage_unit_km=10000,
        ins_theft_doub_pct=0.05,
        ins_driving_school_doub_pct=0.05,
        ins_avg_damage_value=5000,
        ins_avg_damage_mileage=20000,
        cost_gsm_subscription_monthly=0.0,
        cost_gsm_device=469.0,
        cost_gsm_installation=150.0,
        cost_hook_installation=80.0,
        cost_grid_dismantling=0.0,
        cost_registration=233.5,
        cost_sales_prep=800.0,
        ins_nnw_annual_rate=150.0,
        ins_ass_annual_rate=200.0,
        ins_green_card_annual_rate=50.0,
    )


def test_additional_costs_all_flags_on(mock_settings: ControlCenterSettings):
    from main import CalculatorInput

    input_data = CalculatorInput(
        vehicle_id="test",
        base_price_net=100000,
        discount_pct=10,
        wibor_pct=5.8,
        margin_pct=2.0,
        pricing_margin_pct=2.0,
        initial_deposit_pct=10.0,
        replacement_car_enabled=False,
        z_oponami=False,
        add_gsm_subscription=True,
        add_hook_installation=True,
        add_sales_prep=True,
    )
    # Registration (233.5) is always ON, Prep = 800, Hook = 80
    # GSM device = (469 / 6) * (24 / 12) = 78.16 * 2 = 156.33
    # GSM install = 150
    # Total for GSM: 156.33 + 150 = 306.33
    # Total overall expected: 233.5 + 800 + 80 + 306.33 = 1419.83

    calc = AdditionalCostsCalculator(mock_settings, input_data, months=24)
    res = calc.calculate_cost()

    assert res is not None
    assert "total_additional_costs" in res
    assert "monthly_additional_costs" in res

    # Tolerujemy drobne odchyłki w groszach przez podział
    assert abs(res["total_additional_costs"] - 1419.83) < 0.1
    assert abs(res["monthly_additional_costs"] - (1419.83 / 24)) < 0.1


def test_additional_costs_all_flags_off(mock_settings: ControlCenterSettings):
    from main import CalculatorInput

    input_data = CalculatorInput(
        vehicle_id="test",
        base_price_net=100000,
        discount_pct=10,
        wibor_pct=5.8,
        margin_pct=2.0,
        pricing_margin_pct=2.0,
        initial_deposit_pct=10.0,
        replacement_car_enabled=False,
        z_oponami=False,
        add_gsm_subscription=False,
        add_hook_installation=False,
        add_sales_prep=False,
    )

    calc = AdditionalCostsCalculator(mock_settings, input_data, months=36)
    res = calc.calculate_cost()

    # Registration is always ON! (233.5)
    assert res["total_additional_costs"] == 233.5
    assert res["monthly_additional_costs"] == round(233.5 / 36, 2)
