import json
import asyncio
from core.LTRKalkulator import LTRKalkulator

async def main():
    print("Loading stan_json.json...")
    with open("stan_json.json", "r", encoding="utf-8") as f:
        stan = json.load(f)

    discount_dict = stan.get("discount", {})
    fin_params = stan.get("financial_params", {})
    toggles = stan.get("toggles", {})
    mapped_ai = stan.get("mapped_ai_data", {})
    tire_params = stan.get("tire_params", {})
    
    # Base Price calculation exactly as useVehicleCalculations.ts
    c = stan.get("card_summary", {})
    raw_base = str(c.get("base_price") or c.get("total_price") or "0")
    import re
    clean_base = float(re.sub(r"[^\d.,]", "", raw_base.replace(",", ".")))
    
    # This vehicle happens to have a "brutto" price domain
    price_domain = c.get("_price_domain", "unknown")
    is_brutto = "brutto" in raw_base.lower() or price_domain == "brutto"
    base_price_net = round(clean_base / 1.23, 2) if is_brutto else clean_base
    
    # Options (Factory)
    persisted_factory = []
    from types import SimpleNamespace
    for o in stan.get("factory_options", []):
        persisted_factory.append(SimpleNamespace(
            name=o.get("name", "Opcja"),
            price_net=o.get("price_net", 0.0),
            price_gross=o.get("price_gross", round(o.get("price_net", 0.0) * 1.23, 2)),
            no_discount=bool(o.get("no_discount", False)),
            include_in_wr=False
        ))
    
    payload = {
        "calculation_id": "ab33d7b6-2310-474b-a87a-a5979e40da98",
        "vehicle_id": stan.get("vehicle_id") or "ab33d7b6-2310-474b-a87a-a5979e40da98",
        "base_price_net": base_price_net,
        "discount_pct": discount_dict.get("active_discount_pct", 0),
        "factory_options": persisted_factory,
        "service_options": [],
        "okres_bazowy": mapped_ai.get("usage_months", 48),
        "przebieg_bazowy": mapped_ai.get("total_km", 140000),
        "wibor_pct": fin_params.get("wibor_pct") or 5.0,
        "margin_pct": fin_params.get("margin_pct") or 2.0,
        "pricing_margin_pct": 15.0,
        "depreciation_pct": fin_params.get("depreciation_pct"),
        "initial_deposit_pct": fin_params.get("initial_deposit_pct") or 0.0,
        "replacement_car_enabled": toggles.get("replacement_car", True),
        "add_gsm_subscription": toggles.get("gps_required", True),
        "add_hook_installation": toggles.get("hook_installation", False),
        "add_grid_dismantling": toggles.get("grid_dismantling", False),
        "add_registration": toggles.get("add_registration", True),
        "add_sales_prep": toggles.get("add_sales_prep", True),
        "korekta_kosztu_przygotowania": float(stan.get("korekta_kosztu_przygotowania") or 0.0),
        "z_oponami": toggles.get("z_oponami", True),
        "klasa_opony_string": tire_params.get("tire_class", "Medium") or "Medium",
        "srednica_felgi": int(tire_params.get("rim_diameter") or 16),
        "liczba_kompletow_opon": None,
        "korekta_kosztu_opon": tire_params.get("tire_cost_correction_enabled", True),
        "koszt_opon_korekta": tire_params.get("tire_cost_correction", 0.0),
        "service_cost_type": stan.get("service_cost_type", "ASO"),
        "include_servicing": toggles.get("include_servicing", True),
        "vehicle_vintage": stan.get("vehicle_vintage", "current"),
        "is_metalic": stan.get("is_metalic", False),
        "manual_wr_correction": 0.0,
        "pakiet_serwisowy": float(stan.get("pakiet_serwisowy", 0.0)),
        "inne_koszty_serwisowania_netto": float(fin_params.get("other_service_costs") or 0.0),
        "CzynszProcent": 0.0,
        "ubezpieczenie_is_pakiet": True,
        "opcja_serwisowa": "Aso",
        "doplata_inne": 0.0,
        "typ_pojazdu": "Osobowy",
        "wersja_wyposazenia": stan.get("wersja_wyposazenia"),
        "matrix_km_mode": "contract",
        "matrix_contract_km_step": 10000,
        "settings": {"settings_version_id": None, "overrides": None},
        "power_kw": 0,
        "paint_type_name": "",
        "body_type_name": "",
        "zabudowa_type_id": None,
        "samar_category": stan.get("samar_category", ""),
        "engine_name": stan.get("engine_category", "Dizel")
    }
    
    # Przebiegi i miesiace
    grid = [(48, 30000)] # 48m/120k
    payload["wibor_pct"] = 5.85

    payload_obj = SimpleNamespace(**payload)
    
    # Print what gets sent to matrix
    print(f"Base price net: {payload['base_price_net']}")
    print(f"Discount: {payload['discount_pct']}, Margin: {payload['margin_pct']}")
    
    import sys
    sys.path.append('.')
    from core.models import ControlCenterSettings
    
    settings_obj = ControlCenterSettings(
        default_wibor=3.83,
        default_ltr_margin=15.0,
        vat_rate=23.0,
        bank_spread=2.2,
        samar_segment_b_adjustment=-1,
        samar_segment_c_adjustment=-1,
        samar_segment_d_adjustment=0,
        value_threshold_1=140000.0,
        value_threshold_2=190000.0,
        resale_time_days=45,
        inventory_financing_cost=1.5,
        samar_rv_apply_color_correction=True,
        samar_rv_apply_body_correction=True,
        samar_rv_apply_options_depreciation=True,
        samar_rv_base_mileage=140000,
        samar_rv_mileage_unit_km=10000,
        cost_gsm_subscription_monthly=2.5,
        cost_gsm_device=656.25,
        cost_gsm_installation=210.0,
        cost_hook_installation=80.0,
        cost_grid_dismantling=0.0,
        cost_registration=233.5,
        cost_sales_prep=800.0,
        ins_avg_damage_value=2587.0,
        ins_avg_damage_mileage=80000,
        ins_nnw_annual_rate=150.0,
        ins_ass_annual_rate=200.0,
        ins_green_card_annual_rate=50.0,
        normatywny_przebieg_mc=1666,
        przewidywana_cena_sprzedazy_lo=0.15,
        cost_transport=0.0,
        gsm_amortization_years=4.0,
        budzet_marketingowy_ltr=0.0,
        last_settings_update="2026-03-24T10:25:20.203408+00:00"
    )
    
    calc = LTRKalkulator(payload_obj, settings_obj)
    mat = calc.build_matrix()
    calc = LTRKalkulator(payload_obj, settings_obj)
    mat = calc.build_matrix()
    for row in mat:
        if row["Okres"] == 48 and row["PrzebiegKontrakt"] == 120000:
            print(f"FOUND 48m/120k: {row['LacznaStawka']} PLN netto")
            with open('d:/kalk_v3/backend/trace_ab33.json', 'w', encoding='utf-8') as f:
                json.dump(row['calculation_trace'], f, indent=2, ensure_ascii=False)
            break

if __name__ == "__main__":
    asyncio.run(main())
