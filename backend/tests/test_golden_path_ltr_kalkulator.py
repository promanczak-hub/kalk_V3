from unittest.mock import patch
import pytest
from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput

@pytest.fixture
def mock_db_responses():
    return {
        "vehicle": {
            "id": "golden-vehicle-1",
            "samar_class_id": 16, # Compact
            "engine_type_id": 1,
            "power_kw": 110.0,
            "brand": "Skoda",
            "model": "Octavia",
        },
        "samar_klasa": {
            "rv_base_period_months": 48,
            "rv_base_mileage_km": 140000,
            "rv_mileage_threshold_km": 190000,
        },
        "insurance_rates": [
            {
                "KolejnyRok": i,
                "SkladkaOC": 800.0,
                "StawkaBazowaAC": 0.02,
                "StawkaNW": 50.0,
            }
            for i in range(1, 8)
        ],
        "damage_coeffs": {"WspSredniPrzebieg": 1.0, "WspWartoscSzkody": 1.0},
        "replacement_car": {"average_days_per_year": 5.0, "daily_rate_net": 150.0},
        "service_rates": {"cost_aso_per_km": 0.12, "cost_non_aso_per_km": 0.08},
        "rv_depreciation": {
            0: {"base": 0.5, "options": 0.5},
            4: {"base": 0.0, "options": 0.0},
        },
    }

def test_golden_path_standard_car(mock_db_responses):
    # Set up realistic inputs for a standard car
    calc_input = CalculatorInput(
        vehicle_id="golden-vehicle-1",
        base_price_net=120000.0,
        okres_bazowy=36,
        przebieg_bazowy=60000,  # 20k/year
        service_cost_type="ASO",
        replacement_car_enabled=True,
        pricing_margin_pct=10.0, # 10% margin
        transport_fee_net=500.0,
    )
    
    from types import SimpleNamespace
    mock_settings = SimpleNamespace(
        cost_gsm_subscription_monthly=2.5,
        cost_gsm_device=200.0,
        cost_gsm_installation=100.0,
        cost_hook_installation=2500.0,
        cost_grid_dismantling=300.0,
        cost_registration=350.0,
        cost_sales_prep=1040.0,
        ins_avg_damage_value=1500.0,
        ins_avg_damage_mileage=30000.0,
        car_daily_cost=30.4,
        cost_marketing_monthly=100.0,
        normatywny_przebieg_mc=1667,
    )

    with (
        patch("core.LTRKalkulator.get_vehicle_from_db", return_value=mock_db_responses["vehicle"]),
        patch("core.LTRKalkulator.get_samar_klasa_from_db", return_value=mock_db_responses["samar_klasa"]),
        patch("core.LTRKalkulator.get_insurance_rates_from_db", return_value=mock_db_responses["insurance_rates"]),
        patch("core.LTRKalkulator.get_damage_coefficients_from_db", return_value=mock_db_responses["damage_coeffs"]),
        patch("core.LTRKalkulator.get_replacement_car_rate_from_db", return_value=mock_db_responses["replacement_car"]),
        patch("core.LTRSubCalculatorSerwisNew.get_service_rate_from_db", return_value=mock_db_responses["service_rates"]),
        patch("core.samar_rv.SamarRVCalculator._fetch_depreciation_rates", return_value=mock_db_responses["rv_depreciation"]),
        patch("core.samar_rv.SamarRVCalculator._fetch_brand_correction", return_value=0.0),
        patch("core.samar_rv.SamarRVCalculator._fetch_mileage_corrections", return_value=(0.0, 0.0)),
        patch("core.samar_rv.SamarRVCalculator._fetch_class_config", return_value={"base_mileage_km": 140000, "mileage_threshold_km": 190000, "base_period_months": 48}),
        patch("core.samar_rv.SamarRVCalculator.fetch_color_correction", return_value=0.0),
        patch("core.samar_rv.SamarRVCalculator.fetch_body_correction", return_value=0.0),
        patch("core.samar_rv.SamarRVCalculator.fetch_vintage_correction", return_value=0.0),
        patch("core.samar_rv.SamarRVCalculator.fetch_lo_param", return_value=0.0),
        patch("core.LTRKalkulator.LTRSubCalculatorOpony") as mock_tires,
    ):
        mock_tires.return_value.tire_set_price = 2000.0
        mock_tires.return_value.z_oponami = True
        mock_tires.return_value.calculate_cost.return_value = {
            "capex_initial_set": 2000.0,
            "monthly_hardware": 50.0,
            "monthly_storage": 10.0,
            "monthly_swaps": 15.0,
            "IloscOpon": 4,
        }

        calc = LTRKalkulator(input_data=calc_input, settings=mock_settings)
        calc.tires_calc = mock_tires.return_value
        cells = calc.build_matrix()

    assert len(cells) > 0

    # Find specific cell for 36 months and 60,000 km
    target_cell = next((c for c in cells if c["Okres"] == 36 and c["Przebieg"] == 20000), None)
    assert target_cell is not None, "Target calculation cell was not generated"

    # Golden Path Assertions: these lock the exact expected math down to the decimal
    # A single component breaking its math will fail one of these assertions
    assert "LacznaStawka" in target_cell
    assert "CzynszFinansowy" in target_cell
    assert "Ubezpieczenie" in target_cell
    assert "Serwis" in target_cell
    assert "Opony" in target_cell
    assert "SamochodZastepczy" in target_cell
    
    print("\\n[GOLDEN PATH RESULTS]")
    print(f"LacznaStawka: {target_cell.get('LacznaStawka')}")
    print(f"CzynszFinansowy: {target_cell.get('CzynszFinansowy')}")
    print(f"KosztyLaczneMC: {target_cell.get('KosztyLaczneMC')}")
    print(f"MarzaMiesiac: {target_cell.get('MarzaMiesiac')}")
    
    # GOLDEN PATH ASSERTIONS - These values MUST NOT CHANGE during refactoring
    assert target_cell["LacznaStawka"] == 3298.0
    assert target_cell["CzynszFinansowy"] == 2516.0
    assert target_cell["CzynszTechniczny"] == 782.0
    assert target_cell["Ubezpieczenie"] == 356.0
    assert target_cell["Serwis"] == 222.0
    assert target_cell["Opony"] == 83.0
    assert target_cell["SamochodZastepczy"] == 69.0
    assert target_cell["Admin"] == 52.0
    assert target_cell["MarzaMiesiac"] == 330.0
    assert target_cell["KosztFinansowyLacznie"] == 81518.0
    assert target_cell["CenaKatalogowaNetto"] == 120000.0
