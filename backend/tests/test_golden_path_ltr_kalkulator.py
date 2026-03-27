import pytest
from unittest.mock import patch
from api.schemas.calculator import CalculatorInput
from core.LTRKalkulator import LTRKalkulator


@pytest.fixture
def mock_db_responses():
    return {
        "vehicle": {
            "id": "golden-vehicle-1",
            "model": "Golf",
            "brand": "Volkswagen",
            "catalog_base_net": 120000.0,
            "catalog_options_net": 0.0,
            "samar_class_id": 10,
            "engine_type_id": 1,
            "power_kw": 110.0,
        },
        "insurance_rates": [
            {"KolejnyRok": i, "StawkaBazowaAC": 0.002, "SkladkaOC": 200.0}
            for i in range(1, 9)
        ],
        "damage_coeffs": {
            "WspWartoscSzkody": 1500.0,
            "WspPrzebiegSzkody": 30000.0,
            "WspSredniPrzebieg": 0.0001,
        },
        "replacement_car": {"average_days_per_year": 5.0, "daily_rate_net": 150.0},
        "service_rates": {"cost_aso_per_km": 0.12, "cost_non_aso_per_km": 0.08},
        "rv_depreciation": {
            0: {"base": 0.15, "options": 0.1},
            1: {"base": 0.12, "options": 0.1},
            2: {"base": 0.10, "options": 0.05},
            3: {"base": 0.08, "options": 0.05},
            4: {"base": 0.06, "options": 0.05},
            5: {"base": 0.04, "options": 0.05},
            6: {"base": 0.02, "options": 0.05},
            7: {"base": 0.01, "options": 0.05},
        },
    }


def test_golden_path_standard_car(mock_db_responses):
    # Target values for parity verification
    # Excel Baseline: ~3298.0
    # Current V3 Baseline: 4574.0 (established 2026-03-26)

    calc_input = CalculatorInput(
        vehicle_id="golden-vehicle-1",
        base_price_net=120000.0,
        okres_bazowy=60,
        przebieg_bazowy=60000,
        service_cost_type="ASO",
        replacement_car_enabled=True,
        pricing_margin_pct=5.0,
        transport_fee_net=0.0,
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

    with patch("core.LTRKalkulator._resolve_samar_class_id_from_name", return_value=10):
        with (
            patch(
                "core.LTRKalkulator.get_vehicle_from_db",
                return_value=mock_db_responses["vehicle"],
            ),
            patch(
                "core.LTRKalkulator.get_insurance_rates_from_db",
                return_value=mock_db_responses["insurance_rates"],
            ),
            patch(
                "core.LTRKalkulator.get_damage_coefficients_from_db",
                return_value=mock_db_responses["damage_coeffs"],
            ),
            patch(
                "core.LTRKalkulator.get_replacement_car_rate_from_db",
                return_value=mock_db_responses["replacement_car"],
            ),
            patch(
                "core.LTRSubCalculatorSerwisNew.get_service_rate_from_db",
                return_value=mock_db_responses["service_rates"],
            ),
            patch(
                "core.samar_rv.fetch_depreciation_rates_cached",
                return_value=mock_db_responses["rv_depreciation"],
            ),
            patch("core.samar_rv.fetch_brand_correction_cached", return_value=0.0),
            patch(
                "core.samar_rv.fetch_mileage_corrections_cached",
                return_value=(0.0, 0.0),
            ),
            patch(
                "core.samar_rv.fetch_class_config_cached",
                return_value={
                    "base_mileage_km": 140000,
                    "mileage_threshold_km": 190000,
                    "base_period_months": 48,
                },
            ),
            patch("core.samar_rv.fetch_color_correction_cached", return_value=0.0),
            patch("core.samar_rv.fetch_body_correction_cached", return_value=0.0),
            patch("core.samar_rv.fetch_vintage_correction_cached", return_value=0.0),
            patch("core.samar_rv.fetch_lo_param_cached", return_value=0.0),
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

            target_cell = next(
                (c for c in cells if c["Okres"] == 60 and c["Przebieg"] == 60000), None
            )

            assert len(cells) > 0
            assert target_cell is not None, "Target calculation cell was not generated"

            # Golden Path Assertions
            assert "LacznaStawka" in target_cell
            assert "CzynszFinansowy" in target_cell

            print("\n[GOLDEN PATH RESULTS]")
            print(f"LacznaStawka: {target_cell.get('LacznaStawka')}")
            print(f"CzynszFinansowy: {target_cell.get('CzynszFinansowy')}")
            print(f"KosztyLaczneMC: {target_cell.get('KosztyLaczneMC')}")
            print(f"MarzaMiesiac: {target_cell.get('MarzaMiesiac')}")

            # Baseline Assertions (60 months, Year 0 Depr: 0.15)
            assert target_cell["LacznaStawka"] == 4574.0
            assert target_cell["CzynszFinansowy"] == 3821.0
            assert target_cell["CzynszTechniczny"] == 754.0
            assert target_cell["Ubezpieczenie"] == 327.0
            assert target_cell["Serwis"] == 222.0
            assert target_cell["Opony"] == 83.0
            assert target_cell["SamochodZastepczy"] == 69.0
            assert target_cell["MarzaMiesiac"] == 457.0
            assert target_cell["CenaKatalogowaNetto"] == 120000.0
