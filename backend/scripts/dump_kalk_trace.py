"""
dump_kalk_trace.py — Pipeline trace dla konkretnej kalkulacji + komórki matrycy.

Ładuje rekord z `ltr_kalkulacje` po prefiksie ID, odtwarza `CalculatorInput`
ze `stan_json`, ustawia `okres_bazowy` / `przebieg_bazowy` na żądaną komórkę,
i wypisuje stage-by-stage 12-step pipeline z trace z `PipelineDebugger`.

Użycie:
    cd backend
    poetry run python scripts/dump_kalk_trace.py <id_prefix> [months] [total_km]

Przykład (Octavia RS, 200k/48mc):
    poetry run python scripts/dump_kalk_trace.py d0bc32a2 48 200000
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.database import supabase
from core.control_center import fetch_control_center_settings
from core.PipelineDebugger import PipelineDebugger
from api.schemas.calculator import CalculatorInput, VehicleOptions


SEP = "=" * 78
SUB = "-" * 78
BULLET = "*"


def load_kalk(id_prefix: str) -> Dict[str, Any]:
    # UUID column doesn't support ILIKE — use raw RPC-style filter via PostgREST text cast.
    if len(id_prefix) == 36:
        res = (
            supabase.table("ltr_kalkulacje")
            .select("id, numer_kalkulacji, cena_netto, stan_json")
            .eq("id", id_prefix)
            .limit(1)
            .execute()
        )
    else:
        # Prefix mode: list ids, filter Python-side. OK on dev (few hundred rows).
        all_ids = (
            supabase.table("ltr_kalkulacje").select("id").execute().data or []
        )
        matches = [r["id"] for r in all_ids if str(r["id"]).startswith(id_prefix)]
        if not matches:
            raise SystemExit(f"Nie znaleziono kalkulacji o prefiksie '{id_prefix}'")
        if len(matches) > 1:
            raise SystemExit(f"Wieloznaczny prefiks '{id_prefix}' → {len(matches)} matches: {matches[:3]}")
        res = (
            supabase.table("ltr_kalkulacje")
            .select("id, numer_kalkulacji, cena_netto, stan_json")
            .eq("id", matches[0])
            .limit(1)
            .execute()
        )
    if not res.data:
        raise SystemExit(f"Nie znaleziono kalkulacji o prefiksie '{id_prefix}'")
    return res.data[0]


def build_input(stan: Dict[str, Any], okres: int, przebieg: int) -> CalculatorInput:
    """Zbuduj CalculatorInput ze stan_json, podmieniając okres/przebieg na cel."""
    def _opt_list(raw):
        out = []
        for o in raw or []:
            try:
                out.append(
                    VehicleOptions(
                        name=str(o.get("name", "")),
                        price_net=float(o.get("price_net", 0.0)),
                        price_gross=float(o.get("price_gross", 0.0)),
                        no_discount=bool(o.get("no_discount", False)),
                        include_in_wr=bool(o.get("include_in_wr", False)),
                    )
                )
            except (TypeError, ValueError):
                continue
        return out

    fin = stan.get("financial_params") or {}

    return CalculatorInput(
        vehicle_id=str(stan.get("vehicle_id") or ""),
        base_price_net=float(stan.get("base_price_net") or 0.0),
        discount_pct=float(stan.get("discount_pct") or 0.0),
        factory_options=_opt_list(stan.get("factory_options")),
        service_options=_opt_list(stan.get("service_options")),
        okres_bazowy=okres,
        przebieg_bazowy=przebieg,
        pricing_margin_pct=float(stan.get("pricing_margin_pct") or fin.get("pricing_margin_pct") or 15.0),
        wibor_pct=fin.get("wibor_pct"),
        margin_pct=fin.get("margin_pct"),
        depreciation_pct=stan.get("depreciation_pct") or fin.get("depreciation_pct"),
        initial_deposit_pct=float(stan.get("initial_deposit_pct") or fin.get("initial_deposit_pct") or 0.0),
        z_oponami=bool(stan.get("z_oponami", True)),
        klasa_opony_string=str(stan.get("klasa_opony_string") or "Medium"),
        srednica_felgi=int(stan.get("srednica_felgi") or 17),
        liczba_kompletow_opon=stan.get("liczba_kompletow_opon"),
        replacement_car_enabled=bool(stan.get("replacement_car_enabled", True)),
        include_servicing=bool(stan.get("include_servicing", True)),
        service_cost_type=str(stan.get("service_cost_type") or "ASO"),
        pakiet_serwisowy=float(stan.get("pakiet_serwisowy") or 0.0),
        inne_koszty_serwisowania_netto=float(stan.get("inne_koszty_serwisowania_netto") or 0.0),
        paint_type_id=stan.get("paint_type_id"),
        body_type_name=stan.get("body_type_name"),
        zabudowa_type_id=stan.get("zabudowa_type_id"),
        engine_name=stan.get("engine_name"),
        gearbox_name=stan.get("gearbox_name"),
        trim_level=stan.get("trim_level"),
        power_kw=stan.get("power_kw"),
        vehicle_vintage=stan.get("vehicle_vintage"),
        add_gsm_subscription=bool(stan.get("add_gsm_subscription", False)),
        add_hook_installation=bool(stan.get("add_hook_installation", False)),
    )


def fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", " ")
    return str(v)


def dump_step(s: Dict[str, Any]) -> None:
    print(f"\n{SUB}")
    print(f"  KROK {s['step']}: {s['name']}")
    print(SUB)

    outs = s.get("outputs") or {}
    if outs:
        print("  Outputs:")
        for k, v in outs.items():
            print(f"    {k:35s} = {fmt(v)}")

    trace = s.get("trace") or []
    if trace:
        print("  Trace (top 8):")
        for t in trace[:8]:
            if isinstance(t, dict):
                krok = t.get("krok", "")
                row = t.get("rownanie", "")
                wyn = t.get("wynik", "")
                print(f"    {BULLET} {krok}")
                print(f"        {row}")
                print(f"        -> {fmt(wyn)}")
            else:
                print(f"    {BULLET} {t}")


def main():
    args = sys.argv[1:]
    id_prefix = args[0] if args else "d0bc32a2"
    months = int(args[1]) if len(args) > 1 else 48
    total_km = int(args[2]) if len(args) > 2 else 200_000

    przebieg_bazowy = total_km  # so km_per_month*months == total_km when okres_bazowy == months

    print(SEP)
    print(f"  Dump: id~{id_prefix}, cell = {months} mc / {total_km:,} km".replace(",", " "))
    print(SEP)

    kalk = load_kalk(id_prefix)
    stan = kalk["stan_json"] or {}

    print(f"  Numer kalkulacji : {kalk.get('numer_kalkulacji')}")
    print(f"  Cena netto       : {fmt(float(kalk.get('cena_netto') or 0))}")
    print(f"  Brand / Model    : {stan.get('brand')} / {stan.get('model')}")
    print(f"  Engine / Body    : {stan.get('engine_name')} / {stan.get('body_type_name')}")
    print(f"  Trim / Power kW  : {stan.get('trim_level')} / {stan.get('power_kw')}")
    print(f"  Discount %       : {stan.get('discount_pct')}")
    print(f"  Init deposit %   : {stan.get('initial_deposit_pct')}")
    print(f"  Pricing margin % : {(stan.get('financial_params') or {}).get('pricing_margin_pct')}")

    settings = fetch_control_center_settings()
    print(f"\n  control_center.default_wibor  = {getattr(settings, 'default_wibor', '?')}")
    print(f"  control_center.bank_spread    = {getattr(settings, 'bank_spread', '?')}")
    print(f"  Oprocentowanie rocznie ~      = {float(getattr(settings, 'default_wibor', 0)) + float(getattr(settings, 'bank_spread', 0)):.2f} %")

    calc_input = build_input(stan, okres=months, przebieg=przebieg_bazowy)

    debugger = PipelineDebugger(calc_input, settings)
    steps = debugger.calculate_steps(months=months, overrides={})

    for s in steps:
        dump_step(s)

    print(f"\n{SEP}")
    print("  FINAL RATA / SUMMARY (last step)")
    print(SEP)
    last = steps[-1] if steps else {}
    print(json.dumps(last.get("outputs", {}), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
