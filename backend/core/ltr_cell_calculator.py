"""Per-cell calculation for the LTR matrix.

Extracted from `LTRKalkulator.py` (refactor 2026-05-19). Pre-refactor the
per-cell body was inlined and duplicated ~500 LOC across `build_matrix()`
and `build_reverse_search_matrix()`. Now it lives here in one place, with
the shared inputs frozen in `CellContext` and the orchestrator passing
both to `calculate_cell()`.

Public surface:
- `CellContext` — frozen-ish snapshot of inputs that don't vary across cells
- `calculate_cell()` — single per-cell calc; toggle `include_full_output`
  to switch between full UI/export dict and minimal reverse-search shape
- `resolve_vat_multiplier()` / `fetch_transport_fee_net()` — small helpers
  used both here and by `LTRKalkulator._calculate_capex()`
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.database import supabase
from core.supabase_retry import execute_with_retry
from core.finance_input_resolver import _resolve_finance_rate, _require_setting
from core.LTRSubCalculatorAmortyzacja import AmortyzacjaCalculator, AmortyzacjaInput
from core.LTRSubCalculatorBudzetMarketingowy import (
    BudzetMarketingowyCalculator,
    BudzetMarketingowyInput,
)
from core.LTRSubCalculatorFinanse import (
    FinanseCalculator,
    FinanseInput,
    resolve_czynsz_inicjalny_netto,
)
from core.LTRSubCalculatorKosztDzienny import KosztDziennyCalculator, KosztDziennyInput
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator
from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput
from core.LTRSubCalculatorStawka import StawkaCalculator, StawkaInput
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew
from core.ltr_db_fetchers import (
    get_damage_coefficients_from_db,
    get_insurance_rates_from_db,
    get_replacement_car_rate_from_db,
)
from core.ltr_report_builder import build_report_html, to_koszt_dict
from core.ltr_vehicle_resolvers import _resolve_engine_type_id

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Small helpers
# ────────────────────────────────────────────────────────────────────────────


def resolve_vat_multiplier(raw: Any, default: float = 1.23) -> float:
    """Normalise a control-center VAT entry to a *multiplier*.

    Settings sometimes store VAT as the percentage (23) and sometimes as
    the multiplier (1.23). Anything > 10 is treated as a percentage.
    """
    val = float(raw if raw is not None else default)
    return 1.0 + val / 100.0 if val > 10.0 else val


def fetch_transport_fee_net(brand: str) -> float:
    """Look up the transport fee for a brand. 0.0 on miss / error."""
    if not brand:
        return 0.0
    try:
        res = execute_with_retry(
            supabase.table("transport_fees")
            .select("fee_net")
            .eq("brand", brand)
            .limit(1)
        )
        if res.data:
            return float(res.data[0].get("fee_net", 0.0))
    except Exception as exc:
        logger.error("Error fetching transport fee for %s: %s", brand, exc)
    return 0.0


def build_grid_full(input_data: Any) -> Tuple[List[Tuple[int, int]], Dict[Tuple[int, int], int]]:
    """Full matrix grid used by `build_matrix()` (24/36/48/60 mc × 40k-300k km step 5k)."""
    contract_km_min, contract_km_max, contract_km_step = 40000, 300000, 5000

    grid: List[Tuple[int, int]] = []
    seen: set[Tuple[int, int]] = set()
    contract_km_by_pair: Dict[Tuple[int, int], int] = {}

    def add(months: int, km_per_year: int, contract_km: int) -> None:
        pair = (int(months), int(km_per_year))
        if pair in seen:
            return
        seen.add(pair)
        grid.append(pair)
        contract_km_by_pair[pair] = int(contract_km)

    for m in (24, 36, 48, 60):
        for total_km in range(contract_km_min, contract_km_max + 1, contract_km_step):
            km_py = int(round((total_km / m) * 12))
            add(m, km_py, total_km)

    req_months = int(getattr(input_data, "okres_bazowy", 48) or 48) or 48
    req_total_km = int(getattr(input_data, "przebieg_bazowy", 140000) or 140000)
    add(req_months, int(round((req_total_km / req_months) * 12)), req_total_km)

    return grid, contract_km_by_pair


def build_grid_reverse() -> Tuple[List[Tuple[int, int]], Dict[Tuple[int, int], int]]:
    """Reduced grid used by `build_reverse_search_matrix()` (212 cells)."""
    grid: List[Tuple[int, int]] = []
    contract_km_by_pair: Dict[Tuple[int, int], int] = {}
    for months in (24, 36, 48, 60):
        for total_km in range(40000, 300001, 5000):
            km_per_year = int(round((total_km / months) * 12))
            pair = (months, km_per_year)
            grid.append(pair)
            contract_km_by_pair[pair] = total_km
    return grid, contract_km_by_pair


@dataclass
class CellContext:
    """Shared inputs for `calculate_cell()` — set once per build_matrix() call."""

    vehicle_capex: float
    options_capex: float
    capex_res: Any
    base_price_net_full: float
    wr_disc_opts: float
    wr_non_disc_opts: float
    wr_service_in_wr: float
    base_wr_options: float
    margin_pct: float


def resolve_engine_and_power(vehicle: Any, input_data: Any) -> Tuple[int, float]:
    """Fail-fast resolution of engine_type_id + power_kw used by ServiceCalculator."""
    engine_type_id = int(getattr(vehicle, "engine_type_id", 0) or 0)
    if engine_type_id <= 0:
        engine_name_input = getattr(input_data, "engine_name", None)
        if engine_name_input:
            try:
                engine_type_id = _resolve_engine_type_id(engine_name_input)
            except Exception:
                pass
    if engine_type_id <= 0:
        raise ValueError(
            "Brak `engine_type_id` dla pojazdu. Uzupelnij typ silnika w danych wejsciowych."
        )

    power_kw_input = getattr(input_data, "power_kw", None)
    if power_kw_input and float(power_kw_input) > 0:
        power_kw = float(power_kw_input)
    else:
        power_kw_val = getattr(vehicle, "power_kw", 0.0)
        power_kw = float(power_kw_val if power_kw_val is not None else 0.0)
    if power_kw <= 0.0:
        raise ValueError(
            f"Brak poprawnej mocy `power_kw` pojazdu. "
            f"power_kw_input={power_kw_input}, vehicle.power_kw={getattr(vehicle, 'power_kw', None)}"
        )
    return engine_type_id, power_kw


# ────────────────────────────────────────────────────────────────────────────
# Per-cell computation (THE big extraction)
# ────────────────────────────────────────────────────────────────────────────


def calculate_cell(  # noqa: PLR0915 — per-cell calc; further split would obscure pipeline order
    *,
    kalk: Any,                  # LTRKalkulator instance (avoids circular import)
    months: int,
    km_per_year: int,
    total_km: int,
    ctx: CellContext,
    include_full_output: bool,
    correction_for_cell: float = 0.0,
) -> Dict[str, Any]:
    """Compute a single matrix cell.

    `include_full_output=False` returns the minimal reverse-search dict
    (Okres / Przebieg / PrzebiegKontrakt / LacznaStawka). `True` returns
    the full dict with HTML report + calculation trace + warnings.
    """
    # 1. Opony (with optional per-cell correction)
    tires_res = kalk.tires_calc.calculate_cost(
        months=months, total_km=total_km, correction_gross=correction_for_cell
    )
    capex_for_financing = (
        ctx.vehicle_capex + ctx.options_capex + tires_res["capex_initial_set"]
    )

    # 2. Amortyzacja prep (rabat tylko na opcje rabatowalne)
    discount_pct = getattr(kalk.input_data, "discount_pct", 0) / 100.0
    wp_amortyzacja = (
        ctx.vehicle_capex
        + ctx.wr_disc_opts * (1 - discount_pct)
        + ctx.wr_non_disc_opts
        + ctx.wr_service_in_wr
    )

    # 3. VAT multiplier — wymagane w Control Center (brak literal-default 1.23).
    vat_rate = resolve_vat_multiplier(_require_setting(kalk.settings, "vat_rate", "VAT rate"))

    # 4. Czynsz inicjalny — upfront, żeby V1 mógł zredukować pulę amortyzacji
    _initial_deposit_pct = float(getattr(kalk.input_data, "initial_deposit_pct", 0.0) or 0.0)
    _rodzaj_czynszu = "Procentowo" if _initial_deposit_pct > 0 else "Kwotowo"
    _czynsz_inicjalny_netto = resolve_czynsz_inicjalny_netto(
        wartosc_poczatkowa_netto=capex_for_financing,
        rodzaj_czynszu=_rodzaj_czynszu,
        czynsz_inicjalny_brutto=0.0,
        czynsz_procent=_initial_deposit_pct,
        stawka_vat=vat_rate,
    )

    # 5. WR (samar_rv) — V1 parity: full catalogue brutto
    rv_calc_v3 = LTRSubCalculatorUtrataWartosciNew(kalk.vehicle, kalk.input_data)
    rv_res = rv_calc_v3.calculate_values(
        months=months,
        total_km=total_km,
        base_vehicle_catalog_gross=ctx.base_price_net_full * vat_rate,
        options_catalog_gross=ctx.base_wr_options * vat_rate,
        czynsz_inicjalny_netto=_czynsz_inicjalny_netto,
    )
    vr_samar = rv_res["WR"]

    # 6. Finanse (PMT — wariant z/bez czynszu)
    finance_input = FinanseInput(
        WartoscPoczatkowaNetto=capex_for_financing,
        WrPrzewidywanaCenaSprzedazy=vr_samar,
        CzynszInicjalny=0.0,
        CzynszProcent=_initial_deposit_pct,
        RodzajCzynszu=_rodzaj_czynszu,
        StawkaVAT=vat_rate,
        Okres=months,
        WIBORProcent=_resolve_finance_rate(
            "wibor_pct", kalk.input_data, kalk.settings, "default_wibor"
        ),
        MarzaFinansowaProcent=_resolve_finance_rate(
            "margin_pct", kalk.input_data, kalk.settings, "bank_spread"
        ),
    )
    finance_res = FinanseCalculator(finance_input).calculate()

    tires_base = float(
        tires_res["monthly_hardware"]
        + tires_res["monthly_storage"]
        + tires_res["monthly_swaps"]
    )

    # 7. Serwis (fail-fast bez control_center / class / engine / power)
    normatywny_przebieg = int(getattr(kalk.settings, "normatywny_przebieg_mc", 0) or 0)
    if normatywny_przebieg <= 0:
        raise ValueError(
            "Brak poprawnej wartosci `normatywny_przebieg_mc` w Control Center."
        )
    if not kalk.samar_id:
        raise ValueError(
            "Brak `samar_class_id` dla pojazdu. Uzupelnij klase SAMAR."
        )

    resolve_engine_and_power(kalk.vehicle, kalk.input_data)  # raises on miss

    service_input = ServiceCalculatorInput(
        z_serwisem=kalk.include_servicing,
        opcja_serwisowa=kalk._opcja_serwisowa,
        normatywny_przebieg_mc=normatywny_przebieg,
        samar_class_id=int(kalk.samar_id),
        brand_normalized=str(getattr(kalk.vehicle, "brand", "")),
        fuel_type=str(
            getattr(kalk.vehicle, "engine_category",
                    getattr(kalk.input_data, "engine_name", ""))
        ),
        drive_type=str(getattr(kalk.vehicle, "drive_type", "")),
        gearbox_type=str(
            getattr(kalk.vehicle, "gearbox",
                    getattr(kalk.input_data, "gearbox_name", ""))
        ),
        przebieg=total_km,
        okres=months,
        pakiet_serwisowy=float(getattr(kalk.input_data, "pakiet_serwisowy", 0.0)),
        inne_koszty_serwisowania_netto=float(
            getattr(kalk.input_data, "inne_koszty_serwisowania_netto", 0.0)
        ),
    )
    service_dict = ServiceCalculator(service_input).calculate()
    service_base = float(service_dict["monthly_service"])
    service_fallback_used = False
    if kalk.include_servicing and service_base <= 0:
        service_fallback_used = True
        raise ValueError(
            f"Brak stawek serwisowych dla okres={months}, "
            f"klasa={getattr(kalk.vehicle, 'samar_class_id', '?')}, "
            f"silnik={getattr(kalk.vehicle, 'engine_type_id', '?')}."
        )

    # 8. Amortyzacja (procent miesięczny)
    amort_result = None
    if getattr(kalk.input_data, "depreciation_pct", None) is not None:
        procent_amortyzacji = float(kalk.input_data.depreciation_pct)
    else:
        amort_result = AmortyzacjaCalculator(
            AmortyzacjaInput(wp=wp_amortyzacja, wr=vr_samar, okres=months)
        ).calculate()
        procent_amortyzacji = amort_result.amortyzacja_procent

    # 9. Ubezpieczenie
    s_class_id = str(kalk.samar_id)
    ins_calc = InsuranceCalculator(
        insurance_rates=get_insurance_rates_from_db(s_class_id),  # type: ignore
        damage_coefficients=get_damage_coefficients_from_db(s_class_id),  # type: ignore
        settings=kalk.settings,  # type: ignore
        amortization_pct=procent_amortyzacji,  # type: ignore
        total_km=total_km,  # type: ignore
    )
    insurance_res = ins_calc.calculate_cost(
        months, capex_for_financing, enabled=kalk.express_pays_insurance
    )  # type: ignore
    insurance_base = float(insurance_res["monthly_insurance"])
    insurance_total = float(insurance_res.get("total_insurance", insurance_base * months))

    # 10. Samochód zastępczy
    rc_calc = ReplacementCarCalculator(get_replacement_car_rate_from_db(s_class_id))  # type: ignore
    rc_res = rc_calc.calculate_cost(
        months=months, enabled=kalk.input_data.replacement_car_enabled
    )
    rc_base = float(rc_res["monthly_replacement_car"])
    rc_total = float(rc_res.get("total_replacement_car", rc_base * months))

    # 11. Koszty dodatkowe
    add_calc = AdditionalCostsCalculator(kalk.settings, kalk.input_data, months)
    add_calc_res = add_calc.calculate_cost()
    additional_costs_base = float(add_calc_res["monthly_additional_costs"])
    additional_costs_total = additional_costs_base * months

    # 12. Agregaty miesięczne → KosztDzienny → Stawka
    tires_total = tires_base * months
    service_total = service_base * months
    utrata_z_czynszem = float(rv_res["UtrataWartosciZCzynszemInicjalnym"])
    utrata_bez_czynszu = float(rv_res["UtrataWartosciBEZczynszu"])

    kd_result = KosztDziennyCalculator(KosztDziennyInput(
        utrata_wartosci_z_czynszem=utrata_z_czynszem,
        utrata_wartosci_bez_czynszu=utrata_bez_czynszu,
        koszt_finansowy=finance_res.SumaOdsetekZczynszem,
        samochod_zastepczy_netto=rc_total,
        koszty_dodatkowe_netto=additional_costs_total,
        ubezpieczenie_netto=insurance_total,
        opony_netto=tires_total,
        serwis_netto=service_total,
        suma_odsetek_bez_czynszu=finance_res.SumaOdsetekBEZczynszu,
        okres=months,
    )).calculate()

    stawka_result = StawkaCalculator(StawkaInput(
        koszt_mc=kd_result.koszt_mc,
        koszt_mc_bez_czynszu=kd_result.koszt_mc_bez_czynszu,
        utrata_wartosci_netto=utrata_z_czynszem,
        koszty_finansowe_netto=finance_res.SumaOdsetekZczynszem,
        ubezpieczenie_netto=insurance_total,
        samochod_zastepczy_netto=rc_total,
        koszty_dodatkowe_netto=additional_costs_total,
        opony_netto=tires_total,
        serwis_netto=service_total,
        okres=months,
        marza=ctx.margin_pct,
        czynsz_inicjalny=float(finance_res.CzynszInicjalnyNetto),
    )).calculate()

    # Minimal output — reverse-search cache only needs the rate.
    if not include_full_output:
        return {
            "Okres": months,
            "Przebieg": km_per_year,
            "PrzebiegKontrakt": total_km,
            "LacznaStawka": round(stawka_result.oferowana_stawka, 0),
        }

    # Full output — UI / export consumers.
    bm_result = BudzetMarketingowyCalculator(BudzetMarketingowyInput(
        wr_przewidywana_cena_sprzedazy=vr_samar,
        stawka_vat=vat_rate,
        budzet_marketingowy_ltr=_require_setting(
            kalk.settings, "budzet_marketingowy_ltr", "Budżet marketingowy LTR"
        ),
    )).calculate()

    logger.debug(
        "LTR cell trace: months=%d, km=%d, WP=%.2f, RV=%.2f, marza_mc=%.2f, czynsz_fin=%.2f",
        months, total_km, capex_for_financing, vr_samar,
        stawka_result.marza_mc, stawka_result.czynsz_finansowy,
    )

    cell: Dict[str, Any] = {
        "Okres": months,
        "Przebieg": km_per_year,
        "PrzebiegKontrakt": total_km,
        "LacznaStawka": round(stawka_result.oferowana_stawka, 0),
        "CzynszFinansowy": round(stawka_result.czynsz_finansowy, 0),
        "CzynszTechniczny": round(stawka_result.czynsz_techniczny, 0),
        "Ubezpieczenie": round(stawka_result.koszt_ubezpieczenie.koszt_plus_marza_korekta, 0),
        "Serwis": round(stawka_result.koszt_serwis.koszt_plus_marza_korekta, 0),
        "Admin": round(stawka_result.koszt_admin.koszt_plus_marza_korekta, 0),
        "Opony": round(stawka_result.koszt_opony.koszt_plus_marza_korekta, 0),
        "SamochodZastepczy": round(
            stawka_result.koszt_samochod_zastepczy.koszt_plus_marza_korekta, 0
        ),
        "Przychod": round(stawka_result.przychod, 0),
        "PodstawaMarzy": stawka_result.podstawa_marzy,
        "MarzaMiesiac": round(stawka_result.marza_mc, 0),
        "MarzaNaKontrakcie": round(stawka_result.marza_na_kontrakcie, 0),
        "MarzaNaKontrakcieProcent": stawka_result.marza_na_kontrakcie_procent,
        "KosztyLaczneMC": stawka_result.koszty_laczne_mc,
        "KosztFinansowyLacznie": round(stawka_result.koszt_finansowy_lacznie, 0),
        "KosztFinansowyMiesiecznie": round(stawka_result.koszt_finansowy_miesiecznie, 0),
        "Koszt": [
            to_koszt_dict(stawka_result.koszt_finansowy),
            to_koszt_dict(stawka_result.koszt_ubezpieczenie),
            to_koszt_dict(stawka_result.koszt_samochod_zastepczy),
            to_koszt_dict(stawka_result.koszt_serwis),
            to_koszt_dict(stawka_result.koszt_opony),
            to_koszt_dict(stawka_result.koszt_admin),
        ],
        "CenaZakupu": ctx.capex_res.CenaZakupu,
        "CenaZakupuBezOpon": ctx.capex_res.CenaZakupuBezOpon,
        "CenaZakupuBezOponIOpcjiSerwisowych": ctx.capex_res.CenaZakupuBezOponIOpcjiSerwisowych,
        "CenaZakupuBezOponIOpcjiSerwisowychIPakietu":
            ctx.capex_res.CenaZakupuBezOponIOpcjiSerwisowychIPakietu,
        "CenaKatalogowaNetto": ctx.capex_res.CenaKatalogowaNetto,
        "RabatKwotowo": ctx.capex_res.RabatKwotowo,
        "GsmCapexNetto": ctx.capex_res.gsm_capex_net,
        "OpcjeSerwisoweSumaNetto": ctx.capex_res.total_service_options,
        "WR": vr_samar,
        "WRdlaLO": round(rv_res.get("WRdlaLO", vr_samar), 0),
        "UtrataWartosci": round(utrata_z_czynszem, 0),
        "KorektaZaPrzebiegKwotowo": round(rv_res.get("KorektaZaPrzebiegKwotowo", 0.0), 0),
        "KorektaAdministracyjnaKwotowo": 0.0,
        "CzynszInicjalnyProcent": finance_res.CzynszInicjalnyProcent,
        "CzynszInicjalnyNetto": round(finance_res.CzynszInicjalnyNetto, 0),
        "LacznyKosztCzesciOdsetkowejRaty": round(finance_res.SumaOdsetekZczynszem, 0),
        "SumaOdsetekBezCzynszuInicjalnego": round(finance_res.SumaOdsetekBEZczynszu, 0),
        "LacznyKosztOpon": round(tires_total, 0),
        "IloscOpon": round(tires_res["IloscOpon"], 0),
        "Cena1KompletOpon": round(tires_res.get("Cena1KompletOpon", 0.0), 0),
        "Koszt1KplOpon": round(tires_res.get("Koszt1KplOpon", 0.0), 0),
        "LacznieKosztySerwisowe": round(service_total, 0),
        "KosztySerwisowe": round(service_total, 0),
        "LacznieUbezpieczenie": round(insurance_total, 0),
        "KosztyDodatkowe": round(additional_costs_total, 0),
        "LacznieSamochodZastepczy": round(rc_total, 0),
        "KosztyOgolem": round(kd_result.koszty_ogolem, 0),
        "KosztDzienny": round(kd_result.koszt_dzienny, 2),
        "AmortyzacjaProcent": procent_amortyzacji,
        "KorektaWRMaks": round(bm_result.korekta_wr_maks, 2),
        "ReportHtml": "",
        "calculation_trace": (
            [f"=== LTR MATRIX TILE TRACE. TRACE_ID: {kalk.trace_id} ==="]
            + ctx.capex_res.trace
            + rv_res.get("trace", [])
            + (amort_result.trace if amort_result else [])
            + tires_res.get("trace", [])
            + service_dict.get("trace", [])
            + insurance_res.get("trace", [])
            + rc_res.get("trace", [])
            + add_calc_res.get("trace", [])
            + finance_res.trace
            + kd_result.trace
            + stawka_result.trace
            + bm_result.trace
        ),
        "status": "OK",
        "warnings": {
            "service_fallback_used": service_fallback_used,
            "replacement_car_missing": rc_base == 0.0
                and kalk.input_data.replacement_car_enabled,
        },
    }
    cell["ReportHtml"] = build_report_html(cell)
    return cell
