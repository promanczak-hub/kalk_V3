import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from core.PipelineDebugger import PipelineDebugger
from core.LTRKalkulator import LTRKalkulator
from main import CalculatorInput, VehicleOptions
from core.models import ControlCenterSettings


@pytest.fixture
def mock_settings():
    return ControlCenterSettings(
        default_wibor=5.85,
        default_ltr_margin=2.0,
        default_depreciation_pct=1.5,
        vat_rate=23.0,
        bank_spread=0.0,
        samar_segment_b_adjustment=0,
        samar_segment_c_adjustment=0,
        samar_segment_d_adjustment=0,
        value_threshold_1=0.0,
        value_threshold_2=0.0,
        resale_time_days=0,
        inventory_financing_cost=0.0,
        samar_rv_apply_color_correction=True,
        samar_rv_apply_body_correction=True,
        samar_rv_apply_options_depreciation=True,
        samar_rv_base_mileage=15000,
        samar_rv_mileage_unit_km=1000,
        ins_theft_doub_pct=0.0,
        ins_driving_school_doub_pct=0.0,
        ins_avg_damage_value=0.0,
        ins_avg_damage_mileage=0,
        ins_nnw_annual_rate=0.0,
        ins_ass_annual_rate=0.0,
        ins_green_card_annual_rate=0.0,
        cost_gsm_subscription_monthly=0.0,
        cost_gsm_device=500.0,
        cost_gsm_installation=100.0,
        cost_hook_installation=0.0,
        cost_grid_dismantling=0.0,
        cost_registration=0.0,
        cost_sales_prep=0.0,
        budzet_marketingowy_ltr=2000.0,
        normatywny_przebieg_mc=4000,
        samar_baza_url="http://mock",
        samar_token="mock_token",
        google_api_key="mock",
        search_engine_id="mock",
        openai_api_key="mock",
    )


@pytest.fixture
def mock_input_data():
    return CalculatorInput(
        vehicle_id="mock-123",
        base_price_net=100000.0,
        discount_pct=10.0,
        factory_options=[
            VehicleOptions(name="Paint", price_net=2000.0, price_gross=2460.0),
        ],
        service_options=[
            VehicleOptions(
                name="Service Pack",
                price_net=3000.0,
                price_gross=3690.0,
                include_in_wr=True,
            ),
        ],
        wibor_pct=5.85,
        margin_pct=2.0,
        pricing_margin_pct=15.0,
        depreciation_pct=1.5,
        initial_deposit_pct=10.0,
        z_oponami=True,
        klasa_opony_string="Premium",
        srednica_felgi=18,
        korekta_kosztu_opon=False,
        koszt_opon_korekta=0.0,
        service_cost_type="ASO",
        okres_bazowy=48,
        przebieg_bazowy=140000,
        replacement_car_enabled=True,
    )


def test_pipeline_debugger_no_overrides_matches_kalkulator(
    mock_input_data, mock_settings, monkeypatch
):
    monkeypatch.setattr(
        "core.LTRKalkulator.get_vehicle_from_db",
        lambda *a, **kw: {
            "id": "mock-123",
            "klasa_wr_id": "1",
            "engine_type_id": 1,
            "power_kw": 100,
        },
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_samar_klasa_from_db", lambda *a, **kw: {"id": "1"}
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_insurance_rates_from_db", lambda *a, **kw: []
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_replacement_car_rate_from_db",
        lambda *a, **kw: {"auto_zastepcze_baza": 100},
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_damage_coefficients_from_db", lambda *a, **kw: {}
    )

    # Bypass broken InsuranceCalculator completely
    class DummyInsuranceCalc:
        def __init__(self, *a, **kw):
            pass

        def calculate_cost(self, *a, **kw):
            return {"monthly_insurance": 100, "total_insurance": 1200}

    monkeypatch.setattr("core.LTRKalkulator.InsuranceCalculator", DummyInsuranceCalc)
    monkeypatch.setattr("core.PipelineDebugger.InsuranceCalculator", DummyInsuranceCalc)

    # Expected standard calculation
    standard_calc = LTRKalkulator(input_data=mock_input_data, settings=mock_settings)

    # Needs WR mock for new calculations
    monkeypatch.setattr(
        "core.LTRSubCalculatorUtrataWartosciNew.LTRSubCalculatorUtrataWartosciNew.calculate_values",
        lambda *a, **kw: {
            "WR": 40000.0,
            "WRdlaLO": 41000.0,
            "UtrataWartosciBEZczynszu": 50000.0,
            "UtrataWartosciZCzynszemInicjalnym": 55000.0,
        },
    )

    matrix = standard_calc.build_matrix()
    base_month = matrix[7]  # 48 months (6,12,18,24,30,36,42,48 -> index 7)

    # Debugger calculation
    debugger = PipelineDebugger(input_data=mock_input_data, settings=mock_settings)
    steps = debugger.calculate_steps(months=48, overrides={})

    assert len(steps) == 12
    # Verify Step 11 matches base_cost_net and Step 12 matches price_net
    # Note: Stawka is step 11, Budzet is step 12
    stawka_step = steps[10]

    print("\n--- MATRIX ---")
    import pprint

    pprint.pprint(base_month)
    print("\n--- STEPS ---")
    for s in steps:
        print(s["name"], s["outputs"])

    assert stawka_step["name"] == "Stawka"
    assert "outputs" in stawka_step
    assert (
        round(stawka_step["outputs"]["oferowana_stawka"], 2) == base_month["price_net"]
    )


def test_pipeline_debugger_with_override(mock_input_data, mock_settings, monkeypatch):
    monkeypatch.setattr(
        "core.LTRKalkulator.get_vehicle_from_db",
        lambda *a, **kw: {
            "id": "mock-123",
            "klasa_wr_id": "1",
            "engine_type_id": 1,
            "power_kw": 100,
        },
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_samar_klasa_from_db", lambda *a, **kw: {"id": "1"}
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_insurance_rates_from_db", lambda *a, **kw: []
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_replacement_car_rate_from_db",
        lambda *a, **kw: {"auto_zastepcze_baza": 100},
    )
    monkeypatch.setattr(
        "core.LTRKalkulator.get_damage_coefficients_from_db", lambda *a, **kw: {}
    )

    class DummyInsuranceCalc:
        def __init__(self, *a, **kw):
            pass

        def calculate_cost(self, *a, **kw):
            return {"monthly_insurance": 100, "total_insurance": 1200}

    monkeypatch.setattr("core.LTRKalkulator.InsuranceCalculator", DummyInsuranceCalc)
    monkeypatch.setattr("core.PipelineDebugger.InsuranceCalculator", DummyInsuranceCalc)

    monkeypatch.setattr(
        "core.LTRSubCalculatorUtrataWartosciNew.LTRSubCalculatorUtrataWartosciNew.calculate_values",
        lambda *a, **kw: {
            "WR": 40000.0,
            "WRdlaLO": 41000.0,
            "UtrataWartosciBEZczynszu": 50000.0,
            "UtrataWartosciZCzynszemInicjalnym": 55000.0,
        },
    )

    debugger = PipelineDebugger(input_data=mock_input_data, settings=mock_settings)

    # Calculate without override
    steps_normal = debugger.calculate_steps(months=48, overrides={})
    normal_price = steps_normal[10]["outputs"]["oferowana_stawka"]

    # Calculate with override on WR
    steps_override = debugger.calculate_steps(
        months=48, overrides={"step_6_wr": 60000.0}
    )  # Increased WR should lower the installment
    override_price = steps_override[10]["outputs"]["oferowana_stawka"]

    assert override_price < normal_price
