import asyncio
import json
from types import SimpleNamespace
from api.schemas.calculator import CalculatorInput, VehicleOptions
from core.LTRKalkulator import LTRKalkulator


async def main():
    calc_input = CalculatorInput(
        vehicle_id="44d2cae6-7b6f-45d9-90e2-2532546eee5e",
        base_price_net=149975.0,
        discount_pct=26.7,
        factory_options=[
            VehicleOptions(
                name="Pakiet",
                price_net=3569.92,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
            VehicleOptions(
                name="Opt2",
                price_net=80.0,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
            VehicleOptions(
                name="Opt3",
                price_net=100.0,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
            VehicleOptions(
                name="Opt4",
                price_net=2000.0,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
            VehicleOptions(
                name="Opt5",
                price_net=625.0,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
            VehicleOptions(
                name="Opt6",
                price_net=450.0,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
            VehicleOptions(
                name="Opt7",
                price_net=900.0,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
            VehicleOptions(
                name="Opt8",
                price_net=450.0,
                price_gross=0,
                no_discount=False,
                include_in_wr=False,
            ),
        ],
        service_options=[],
        okres_bazowy=48,
        przebieg_bazowy=80000,
        pricing_margin_pct=15.0,
        z_oponami=True,
        klasa_opony_string="Medium",
        srednica_felgi=16,
        wibor_pct=5.85,
        margin_pct=2.0,
        replacement_car_enabled=True,
        add_gsm_subscription=True,
        add_hook_installation=False,
        add_registration=True,
        add_sales_prep=True,
        service_cost_type="ASO",
        vehicle_vintage="previous",
        is_metalic=False,
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
    capex_base, capex_opt = kalkulator._calculate_capex()
    print("CAPEX base:", capex_base)
    print("CAPEX options:", capex_opt)
    print("Total CAPEX:", capex_base + capex_opt)

    matrix = kalkulator.build_matrix()

    for cell in matrix:
        if cell["months"] == 48 and cell["km_per_year"] == 20000:
            print("CELL 48 / 20k:", json.dumps(cell, indent=2))
            # Access RV debug by running the UtrataWartosciNew calc directly
            from core.LTRSubCalculatorUtrataWartosciNew import (
                LTRSubCalculatorUtrataWartosciNew,
            )

            rv_calc = LTRSubCalculatorUtrataWartosciNew(kalkulator.vehicle, calc_input)
            tires_res = kalkulator.tires_calc.calculate_cost(48, 80000)
            base_wr_options = sum(opt.price_net for opt in calc_input.factory_options)
            rv_res = rv_calc.calculate_values(
                months=48,
                total_km=80000,
                base_vehicle_capex_gross=149975.0 * settings.vat_rate,
                options_capex_gross=(base_wr_options + tires_res["capex_initial_set"])
                * settings.vat_rate,
            )
            print("RV DEBUG:")
            print(json.dumps(rv_res.get("debug", {}), indent=2))
            break


if __name__ == "__main__":
    asyncio.run(main())
