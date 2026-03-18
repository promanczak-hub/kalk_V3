import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import json
from types import SimpleNamespace
from api.schemas.calculator import CalculatorInput, VehicleOptions
from core.LTRKalkulator import LTRKalkulator

async def main():
    vehicle_id = "2a016435-f3a5-4092-9b4f-a73ccce14a01"
    
    calc_input = CalculatorInput(
        vehicle_id=vehicle_id,
        base_price_net=162357.72,
        discount_pct=21.0,
        factory_options=[
            VehicleOptions(
                name="All Options",
                price_net=14985.36,
                price_gross=18432.0,
                no_discount=False,
                include_in_wr=True,
            )
        ],
        service_options=[],
        okres_bazowy=48,
        przebieg_bazowy=120000,
        pricing_margin_pct=0.0,
        wibor_pct=4.82,
        margin_pct=2.2,
        depreciation_pct=0.0,
        initial_deposit_pct=0.0,
        z_oponami=True,
        klasa_opony_string="Premium",
        srednica_felgi=19,
        replacement_car_enabled=True,
        add_gsm_subscription=True,
        add_hook_installation=False,
        add_registration=True,
        add_sales_prep=True,
        service_cost_type="ASO",
        vehicle_vintage="current",
        is_metalic=True,
        include_servicing=True,
    )

    settings = SimpleNamespace(
        vat_rate=1.23,
        budzet_marketingowy_ltr=0.0,
        normatywny_przebieg_mc=1667,
        cost_gsm_device=469.0,
        cost_gsm_installation=150.0,
        cost_gsm_subscription_monthly=2.5,
        cost_hook_installation=2000.0,
        cost_grid_dismantling=500.0,
        cost_registration=300.0,
        cost_sales_prep=1040.0,
        min_margin_amount=0.0,
        ubezpieczenie_doubezpieczenie_kradziez=False,
        ubezpieczenie_nauka_jazdy=False,
        insurance_base_rate=0.015,
        marza_ubezpieczenie_wskaznik_narzutu=0.1,
    )

    kalkulator = LTRKalkulator(input_data=calc_input, settings=settings)
    
    # Run pipeline for 48 / 30k (Commented out to focus on WR as per user request)
    # matrix = kalkulator.build_matrix()
    # cost_components = next((cell for cell in matrix if cell["months"] == 48 and cell["km_per_year"] == 30000), None)
    
    # print("--- 48 months / 30 000 km per year ---")
    # print(json.dumps(cost_components, indent=2))
    
    # Additionally dump the WR calculation
    from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew
    rv_calc = LTRSubCalculatorUtrataWartosciNew(kalkulator.vehicle, calc_input)
    base_wr_options = sum(opt.price_net for opt in calc_input.factory_options if opt.include_in_wr)
    
    rv_res = rv_calc.calculate_values(
        months=48,
        total_km=120000,
        base_vehicle_capex_gross=calc_input.base_price_net * settings.vat_rate,
        options_capex_gross=base_wr_options * settings.vat_rate,
    )
    print("\n--- RV TRACE ---")
    print(json.dumps(rv_res.get("debug", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
