from unittest.mock import patch

from core.LTRKalkulator import LTRKalkulator
from api.schemas.calculator import CalculatorInput


def test_calculate_matrix_sanity():
    # Input settings
    calc_input = CalculatorInput(
        vehicle_id="mock-vehicle",
        base_price_net=100000.0,
        okres_bazowy=48,
        przebieg_bazowy=80000,  # 20k/year
        service_cost_type="ASO",
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
    )

    with (
        patch(
            "core.LTRKalkulator.get_vehicle_from_db",
            return_value={
                "id": "mock-vehicle",
                "samar_class_id": 1,
                "engine_type_id": 1,
                "power_kw": 110.0,
                "brand": "Toyota",
                "model": "Corolla",
            },
        ),
        patch("core.LTRKalkulator.get_samar_klasa_from_db", return_value={}),
        patch(
            "core.LTRKalkulator.get_insurance_rates_from_db",
            return_value=[
                {
                    "KolejnyRok": i,
                    "SkladkaOC": 100.0,
                    "StawkaBazowaAC": 0.05,
                    "StawkaNW": 50.0,
                }
                for i in range(1, 8)
            ],
        ),
        patch("core.LTRKalkulator.get_damage_coefficients_from_db", return_value={}),
        patch("core.LTRKalkulator.get_replacement_car_rate_from_db", return_value={}),
        patch(
            "core.LTRSubCalculatorSerwisNew.get_service_rate_from_db",
            return_value={"cost_aso_per_km": 0.15, "cost_non_aso_per_km": 0.10},
        ),
        patch(
            "core.samar_rv.SamarRVCalculator._fetch_depreciation_rates",
            return_value={
                0: {"base": 0.5, "options": 0.5},
                4: {"base": 0.0, "options": 0.0},
            },
        ),
        patch(
            "core.samar_rv.SamarRVCalculator._fetch_brand_correction", return_value=0.0
        ),
        patch(
            "core.samar_rv.SamarRVCalculator._fetch_mileage_corrections",
            return_value=(0.0, 0.0),
        ),
        patch(
            "core.samar_rv.SamarRVCalculator._fetch_class_config",
            return_value={"name": "mock"},
        ),
        patch(
            "core.samar_rv.SamarRVCalculator.fetch_color_correction", return_value=0.0
        ),
        patch(
            "core.samar_rv.SamarRVCalculator.fetch_body_correction",
            return_value=(0.0, 0.0),
        ),
        patch(
            "core.samar_rv.SamarRVCalculator.fetch_vintage_correction", return_value=0.0
        ),
        patch("core.samar_rv.SamarRVCalculator.fetch_lo_param", return_value=0.0),
        patch("core.LTRKalkulator.LTRSubCalculatorOpony") as mock_tires,
    ):
        # mock tires calculate_cost to return valid dict
        mock_tires.return_value.calculate_cost.return_value = {
            "capex_initial_set": 0,
            "monthly_hardware": 0,
            "monthly_storage": 0,
            "monthly_swaps": 0,
            "IloscOpon": 4,
        }

        calc = LTRKalkulator(input_data=calc_input, settings=mock_settings)
        calc.tires_calc = mock_tires.return_value
        cells = calc.build_matrix()

    assert isinstance(cells, list)
    assert len(cells) > 0

    # Ensure our specific 48m/20k pair was injected
    found_custom = False
    for cell in cells:
        assert "months" in cell
        assert "km_per_year" in cell
        assert "price_net" in cell
        if cell["months"] == 48 and cell["km_per_year"] == 20000:
            found_custom = True

    assert found_custom, (
        "Siatka nie zawiera wejściowych parametrów użytkownika (48mc / 20k km)."
    )
