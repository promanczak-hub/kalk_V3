import asyncio
import json
from pydantic import BaseModel
from typing import List

from core.LTRKalkulator import LTRKalkulator


class DummyOpt(BaseModel):
    price_net: float
    name: str = ""
    no_discount: bool = False
    include_in_wr: bool = True


class DummyInput(BaseModel):
    base_price_net: float
    discount_pct: float
    wibor_pct: float
    pricing_margin_pct: float
    factory_options: List[DummyOpt] = []
    service_options: List[DummyOpt] = []
    z_oponami: bool = True
    klasa_opony_string: str = "Premium"
    srednica_felgi: int = 19
    include_servicing: bool = True
    service_cost_type: str = "ASO"
    vehicle_id: str = ""
    engine_name: str = ""
    samar_category: str = ""
    rocznik: int = 2024
    replacement_car_enabled: bool = False
    okres_bazowy: int = 48
    przebieg_bazowy: int = 120000
    CzynszKwota: float = 0.0
    CzynszProcent: float = 0.0
    RodzajCzynszu: str = "Kwotowo"
    pakiet_serwisowy: float = 0.0
    add_gsm_subscription: bool = False
    add_hook_installation: bool = False
    add_grid_dismantling: bool = False
    add_registration: bool = False
    add_sales_prep: bool = False


class DummySettings(BaseModel):
    vat_rate: float = 1.23
    wibor_pct: float = 5.85
    default_wibor: float = 5.85
    default_ltr_margin: float = 15.0
    cost_gsm_device: float = 469.0
    cost_gsm_installation: float = 150.0
    budzet_marketingowy_ltr: float = 0.0
    normatywny_przebieg_mc: int = 1666
    ins_avg_damage_value: float = 8000.0
    ins_damage_frequency: float = 0.5
    ins_avg_damage_mileage: int = 15000
    cost_gsm_subscription_monthly: float = 0.0
    cost_hook_installation: float = 0.0
    cost_grid_dismantling: float = 0.0
    cost_registration: float = 0.0
    cost_sales_prep: float = 0.0


async def main():
    with open("stan_json.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct input
    base_price = (
        data.get("base_price_net") if data.get("base_price_net") is not None else 0
    )
    discount = data.get("discount_pct") if data.get("discount_pct") is not None else 0
    wibor = data.get("wibor_pct") if data.get("wibor_pct") is not None else 5.85
    margin = 0.0

    factory_opts = []
    for opt in data.get("factory_options", []):
        factory_opts.append(
            DummyOpt(
                price_net=opt.get("price_net", 0),
                name=opt.get("name", "Option"),
                no_discount=opt.get("no_discount", False),
                include_in_wr=opt.get("include_in_wr", True),
            )
        )

    srv_opts = []
    for opt in data.get("service_options", []):
        srv_opts.append(
            DummyOpt(
                price_net=opt.get("price_net", 0),
                name=opt.get("name", "Service"),
                no_discount=opt.get("no_discount", False),
                include_in_wr=opt.get("include_in_wr", False),
            )
        )

    vehicle_id = data.get("vehicle_id", "")
    samar_cat = data.get("samar_category", "")
    okres = data.get("okres_bazowy", 48)
    przebieg = data.get("przebieg_bazowy", 120000)
    czynsz_pct = data.get("czynsz_inicjalny_pct", 0.0)

    inp = DummyInput(
        base_price_net=base_price,
        discount_pct=discount,
        wibor_pct=wibor,
        pricing_margin_pct=margin,
        factory_options=factory_opts,
        service_options=srv_opts,
        vehicle_id=vehicle_id,
        samar_category=samar_cat,
        okres_bazowy=okres,
        przebieg_bazowy=przebieg,
        CzynszProcent=czynsz_pct,
        z_oponami=data.get("z_oponami", True),
        include_servicing=data.get("include_servicing", True),
        srednica_felgi=data.get("srednica_felgi", 19),
    )

    settings = DummySettings()

    kalkulator = LTRKalkulator(inp, settings)

    print(
        f"Vehicle: {kalkulator.vehicle.brand} {kalkulator.vehicle.model} (Klasa Samar = {kalkulator.samar_id})"
    )

    # Przeliczenie dla konfiguracji
    res = kalkulator.build_matrix()

    print("\n--- MATRIX DUMP (48 months) ---")
    for r in res:
        if r["Okres"] == 48 and r["PrzebiegKontrakt"] == 120000:
            print(
                f"Miesiące: {r['Okres']}, Przebieg Kontrakt: {r['PrzebiegKontrakt']}, Stawka: {r['LacznaStawka']}, WR: {r['WR']}"
            )
            print("Czynsz Finansowy:", r["CzynszFinansowy"])
            print("Czynsz Techniczny:", r["CzynszTechniczny"])
            print("Ubezpieczenie:", r["Ubezpieczenie"])
            print("Serwis:", r["Serwis"])
            print("Opony:", r["Opony"])


if __name__ == "__main__":
    asyncio.run(main())
