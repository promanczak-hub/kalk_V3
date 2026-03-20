from unittest.mock import patch
import traceback

def run():
    try:
        from core.LTRKalkulator import LTRKalkulator
        from api.schemas.calculator import CalculatorInput
        from types import SimpleNamespace
        
        calc_input = CalculatorInput(
            vehicle_id="golden-vehicle-1",
            base_price_net=120000.0,
            okres_bazowy=36,
            przebieg_bazowy=60000,
            service_cost_type="ASO",
            replacement_car_enabled=True,
            pricing_margin_pct=10.0,
        )
        
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
        
        mock_db_responses = {
            "vehicle": {
                "id": "golden-vehicle-1",
                "samar_class_id": 16,
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
            "replacement_car": {"base_rate": 100.0, "markup_pct": 10.0},
            "service_rates": {"cost_aso_per_km": 0.12, "cost_non_aso_per_km": 0.08},
            "rv_depreciation": {
                0: {"base": 0.5, "options": 0.5},
                4: {"base": 0.0, "options": 0.0},
            },
        }

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
            print("Successfully built cells:", len(cells))
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    run()
