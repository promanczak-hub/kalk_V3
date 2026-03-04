from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, cast
from core.database import supabase
from core.LTRKalkulator import LTRKalkulator

router = APIRouter(prefix="/budget-finder", tags=["Budget Finder"])


class BudgetVariant(BaseModel):
    id: str
    dane_pojazdu: str
    cena_netto: float
    rata_mc: float
    wklad_wlasny_pct: float
    wklad_wlasny_kwota: float
    marza_pct: float
    wariant_nazwa: str
    score: float


class BudgetFinderResponse(BaseModel):
    status: str
    results: List[BudgetVariant]


@router.get("", response_model=BudgetFinderResponse)
def find_budget_offers(
    target_rate: float = Query(3000.0, description="Docelowa rata miesięczna Netto"),
    tolerance: float = Query(
        200.0, description="Akceptowalne odchylenie od raty (+/- PLN)"
    ),
    months_min: int = Query(24, description="Minimalny docelowy miesiac"),
    months_max: int = Query(60, description="Maksymalny docelowy miesiac"),
    mileage_min: int = Query(10000, description="Minimalny roczny przebieg km"),
    mileage_max: int = Query(60000, description="Maksymalny roczny przebieg km"),
    max_upfront_value: float = Query(
        10.0, description="Max akceptowalny wkład (kwota lub %)"
    ),
    upfront_type: str = Query("pct", description="Typ wkładu: 'pct' lub 'pln'"),
    margin_min: float = Query(0.0, description="Minimalna marża dla LTR %"),
    margin_max: float = Query(20.0, description="Maksymalna marża dla LTR %"),
    fuels: List[str] = Query(default=[], description="Filtry Paliwa"),
    transmissions: List[str] = Query(default=[], description="Filtry Skrzyni"),
    bodies: List[str] = Query(default=[], description="Filtry Nadwozia"),
    samar_categories: List[str] = Query(default=[], description="Filtry Kat SAMAR"),
):
    from main import CalculatorInput, ControlCenterSettings, GridVariant

    # 1. Pobranie ustawien z DB (lub fallback)
    try:
        cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not cc_res.data:
            raise HTTPException(status_code=500, detail="Brak ustawień CC")
        settings = ControlCenterSettings(**cc_res.data[0])  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Pobierz wszystkie z ltr_kalkulacje
    try:
        kalk_res = supabase.table("ltr_kalkulacje").select("*").execute()
        all_kalks = kalk_res.data or []
    except Exception:
        raise HTTPException(status_code=500, detail="Błąd pobierania kalkulacji z bazy")

    matching_variants: List[BudgetVariant] = []

    # Valid grid boundaries for initial fast scan (Cheapest configuration usually is max length, min mileage)
    valid_months = [m for m in [24, 36, 48, 60] if months_min <= m <= months_max]
    if not valid_months:
        valid_months = [24, 36, 48, 60]

    valid_mileages = [
        km
        for km in [10000, 20000, 30000, 40000, 50000, 60000]
        if mileage_min <= km <= mileage_max
    ]
    if not valid_mileages:
        valid_mileages = [10000, 20000, 30000, 40000, 50000, 60000]

    # OPTIMIZATION: To find the absolute lowest rate, we only need to calculate 1 cell: max months, min mileage
    cheapest_month = max(valid_months)
    cheapest_mileage = min(valid_mileages)

    # Limit maximum margin from user to setting constraint if not overriden
    capped_default_margin = min(settings.default_ltr_margin, margin_max)

    def calculate_score(
        final_rate: float,
        target_r: float,
        tol: float,
        final_margin: float,
        final_upfront: float,
    ) -> float:
        score = 0.0

        # Rate Match Score (Up to 40 points) -> Ideal target gives 40, bounds of tolerance give 0
        dist = abs(final_rate - target_r)
        if dist <= tol:
            rate_score = 40.0 * (1.0 - (dist / tol))
            score += max(0.0, rate_score)

        # Margin Score (Up to 30 points) -> 0% gives 0, capped_default gives 30.
        if capped_default_margin > 0:
            margin_score = 30.0 * (final_margin / capped_default_margin)
            score += min(30.0, max(0.0, margin_score))

        # Upfront Score (Up to 30 points) -> 0% gives 30, max_upfront gives 0.
        if max_upfront_pct > 0:
            upfront_score = 30.0 * (1.0 - (final_upfront / max_upfront_pct))
            score += min(30.0, max(0.0, upfront_score))
        else:
            if final_upfront == 0.0:
                score += 30.0

        return round(score, 2)

    # 3. Iteracja (In-Memory Processing)
    for k in all_kalks:
        stan_json = cast(Dict[str, Any], k.get("stan_json", {}))  # type: ignore
        if not stan_json:
            continue

        vehicle_mapped = stan_json.get("vehicle_mapped", {})
        samar_cat = stan_json.get("samar_category")

        # Prefiltering Multi-selects
        if fuels and vehicle_mapped.get("fuel_type") not in fuels:
            continue
        if transmissions and vehicle_mapped.get("transmission") not in transmissions:
            continue
        if bodies and vehicle_mapped.get("body_type") not in bodies:
            continue
        if samar_categories and samar_cat not in samar_categories:
            continue

        cena = float(k.get("cena_netto", 0.0))  # type: ignore
        k_id = cast(str, k.get("id", ""))  # type: ignore
        k_dane = cast(str, k.get("dane_pojazdu", ""))  # type: ignore

        if upfront_type == "pln":
            max_upfront_pct = (
                (float(max_upfront_value) / cena * 100.0) if cena > 0 else 0.0
            )
        else:
            max_upfront_pct = max_upfront_value

        try:
            calc_input = CalculatorInput(
                vehicle_id=cast(str, stan_json.get("vehicle_id", "")),  # type: ignore
                base_price_net=float(stan_json.get("base_price_net", 0.0)),  # type: ignore
                discount_pct=float(stan_json.get("discount_pct", 0.0)),  # type: ignore
                factory_options=cast(list, stan_json.get("factory_options", [])),  # type: ignore
                service_options=cast(list, stan_json.get("service_options", [])),  # type: ignore
                grid=GridVariant(
                    months=[cheapest_month], km_per_year=[cheapest_mileage]
                ),  # Fast single cell calculation
                pricing_margin_pct=capped_default_margin,
                wibor_pct=settings.default_wibor,
                initial_deposit_pct=0.0,
            )
        except Exception:
            continue

        def get_rate(wklad: float, marza: float) -> float:
            calc_input.initial_deposit_pct = wklad
            calc_input.pricing_margin_pct = marza
            calc_input.margin_pct = marza

            eng = LTRKalkulator(input_data=calc_input, settings=settings)
            matrix = eng.build_matrix()
            if not matrix:
                return 999999.0
            return float(matrix[0].get("price_net", 999999.0))

        base_rate = get_rate(0.0, capped_default_margin)

        # Scenario A: Base rate is within budget
        if abs(base_rate - target_rate) <= tolerance:
            score = calculate_score(
                base_rate, target_rate, tolerance, capped_default_margin, 0.0
            )
            matching_variants.append(
                BudgetVariant(
                    id=k_id,
                    dane_pojazdu=k_dane,
                    cena_netto=cena,
                    rata_mc=round(base_rate, 2),
                    wklad_wlasny_pct=0.0,
                    wklad_wlasny_kwota=0.0,
                    marza_pct=capped_default_margin,
                    wariant_nazwa="Wariant Optymalny (0% Wkładu)",
                    score=score,
                )
            )
            continue

        # Scenario B: Base rate is TOO LOW, we can INCREASE MARGIN! (Up-sell Bisekcja)
        if base_rate < target_rate - tolerance:
            low_m = settings.default_ltr_margin
            high_m = 15.0
            best_m = low_m

            for i in range(12):
                mid_m = (low_m + high_m) / 2.0
                r = get_rate(0.0, mid_m)
                print(f"Scenario B Loop {i} for {k_id}: mid_m={mid_m} r={r}")
                if abs(r - target_rate) <= tolerance:
                    best_m = mid_m
                    break
                if r < target_rate:
                    low_m = mid_m
                    best_m = mid_m
                else:
                    high_m = mid_m

            r_final = get_rate(0.0, best_m)
            if abs(r_final - target_rate) <= tolerance:
                score = calculate_score(r_final, target_rate, tolerance, best_m, 0.0)
                matching_variants.append(
                    BudgetVariant(
                        id=k_id,
                        dane_pojazdu=k_dane,
                        cena_netto=cena,
                        rata_mc=round(r_final, 2),
                        wklad_wlasny_pct=0.0,
                        wklad_wlasny_kwota=0.0,
                        marza_pct=round(best_m, 2),
                        wariant_nazwa=f"Wariant Zyskowny (Zwiększona marża do {best_m:.1f}%)",
                        score=score,
                    )
                )
            continue

        # Scenario C: Base rate is TOO HIGH, try cutting margin first
        if base_rate > target_rate + tolerance:
            r_min_margin = get_rate(0.0, margin_min)
            if r_min_margin <= target_rate + tolerance:
                low_m = margin_min
                high_m = capped_default_margin
                best_m = margin_min

                for i in range(12):
                    mid_m = (low_m + high_m) / 2.0
                    r = get_rate(0.0, mid_m)
                    print(f"Scenario C(1) Loop {i} for {k_id}: mid_m={mid_m} r={r}")
                    if abs(r - target_rate) <= tolerance:
                        best_m = mid_m
                        break
                    if r > target_rate:
                        high_m = mid_m
                    else:
                        low_m = mid_m
                        best_m = mid_m

                r_final = get_rate(0.0, best_m)
                if abs(r_final - target_rate) <= tolerance:
                    score = calculate_score(
                        r_final, target_rate, tolerance, best_m, 0.0
                    )
                    matching_variants.append(
                        BudgetVariant(
                            id=k_id,
                            dane_pojazdu=k_dane,
                            cena_netto=cena,
                            rata_mc=round(r_final, 2),
                            wklad_wlasny_pct=0.0,
                            wklad_wlasny_kwota=0.0,
                            marza_pct=round(best_m, 2),
                            wariant_nazwa=f"Wariant Kompromisowy (Zmniejszona marża do {best_m:.1f}%)",
                            score=score,
                        )
                    )
                continue

            # Cutting margin didn't work. Try upfront payment with nominal margin
            r_max_upfront = get_rate(max_upfront_pct, settings.default_ltr_margin)
            if r_max_upfront <= target_rate + tolerance:
                low_u = 0.0
                high_u = max_upfront_pct
                best_u = max_upfront_pct

                for _ in range(12):
                    mid_u = (low_u + high_u) / 2.0
                    r = get_rate(mid_u, settings.default_ltr_margin)
                    if abs(r - target_rate) <= tolerance:
                        best_u = mid_u
                        break
                    if r > target_rate:
                        low_u = mid_u
                        best_u = mid_u
                    else:
                        high_u = mid_u

                r_final = get_rate(best_u, settings.default_ltr_margin)
                if abs(r_final - target_rate) <= tolerance:
                    score = calculate_score(
                        r_final,
                        target_rate,
                        tolerance,
                        settings.default_ltr_margin,
                        best_u,
                    )
                    kwota_wkladu = cena * (best_u / 100.0)
                    matching_variants.append(
                        BudgetVariant(
                            id=k_id,
                            dane_pojazdu=k_dane,
                            cena_netto=cena,
                            rata_mc=round(r_final, 2),
                            wklad_wlasny_pct=round(best_u, 2),
                            wklad_wlasny_kwota=float(kwota_wkladu),
                            marza_pct=settings.default_ltr_margin,
                            wariant_nazwa=f"Wariant z Wpłatą Własną ({best_u:.1f}%)",
                            score=score,
                        )
                    )
                continue

            # Last resort: max upfront AND max margin cut
            r_max_cut = get_rate(max_upfront_pct, margin_min)
            if r_max_cut <= target_rate + tolerance:
                low_m = margin_min
                high_m = capped_default_margin
                best_m = margin_min

                for _ in range(12):
                    mid_m = (low_m + high_m) / 2.0
                    r = get_rate(max_upfront_pct, mid_m)
                    if abs(r - target_rate) <= tolerance:
                        best_m = mid_m
                        break
                    if r > target_rate:
                        high_m = mid_m
                    else:
                        low_m = mid_m
                        best_m = mid_m

                r_final = get_rate(max_upfront_pct, best_m)
                if abs(r_final - target_rate) <= tolerance:
                    score = calculate_score(
                        r_final, target_rate, tolerance, best_m, max_upfront_pct
                    )
                    kwota_wkladu = cena * (max_upfront_pct / 100.0)
                    matching_variants.append(
                        BudgetVariant(
                            id=k_id,
                            dane_pojazdu=k_dane,
                            cena_netto=cena,
                            rata_mc=round(r_final, 2),
                            wklad_wlasny_pct=round(max_upfront_pct, 2),
                            wklad_wlasny_kwota=float(kwota_wkladu),
                            marza_pct=round(best_m, 2),
                            wariant_nazwa=f"Wariant Ratunkowy (Wkład {max_upfront_pct:.1f}% + Marża {best_m:.1f}%)",
                            score=score,
                        )
                    )

    # Sort matching variants: Highest score first
    matching_variants.sort(key=lambda x: x.score, reverse=True)

    # Return top 50 matches to protect frontend
    top_50 = matching_variants[:50]

    return BudgetFinderResponse(status="success", results=top_50)


@router.get("/matrix")
def get_matrix(
    kalkulacja_id: str = Query(..., description="ID kalkulacji bazowej"),
    marza_pct: float = Query(..., description="Zastosowana marza %"),
    wklad_wlasny_pct: float = Query(..., description="Zastosowany wklad %"),
    months_min: int = Query(24, description="Minimalny docelowy miesiac"),
    months_max: int = Query(60, description="Maksymalny docelowy miesiac"),
    mileage_min: int = Query(10000, description="Minimalny roczny przebieg km"),
    mileage_max: int = Query(60000, description="Maksymalny roczny przebieg km"),
):
    from main import CalculatorInput, ControlCenterSettings, GridVariant

    try:
        cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not cc_res.data:
            raise HTTPException(status_code=500, detail="Brak ustawień CC")
        settings = ControlCenterSettings(**cc_res.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        kalk_res = (
            supabase.table("ltr_kalkulacje")
            .select("*")
            .eq("id", kalkulacja_id)
            .execute()
        )
        if not kalk_res.data:
            raise HTTPException(status_code=404, detail="Nie znaleziono kalkulacji")
        k = cast(Dict[str, Any], kalk_res.data[0])
    except Exception:
        raise HTTPException(status_code=500, detail="Błąd pobierania kalkulacji z bazy")

    stan_json = cast(Dict[str, Any], k.get("stan_json", {}))
    if not stan_json:
        raise HTTPException(
            status_code=400, detail="Brak poprawnych danych JSON kalkulacji"
        )

    valid_months = [m for m in [24, 36, 48, 60] if months_min <= m <= months_max]
    if not valid_months:
        valid_months = [24, 36, 48, 60]

    valid_mileages = [
        km
        for km in [10000, 20000, 30000, 40000, 50000, 60000]
        if mileage_min <= km <= mileage_max
    ]
    if not valid_mileages:
        valid_mileages = [10000, 20000, 30000, 40000, 50000, 60000]

    try:
        calc_input = CalculatorInput(
            vehicle_id=cast(str, stan_json.get("vehicle_id", "")),
            base_price_net=float(stan_json.get("base_price_net", 0.0)),
            discount_pct=float(stan_json.get("discount_pct", 0.0)),
            factory_options=cast(list, stan_json.get("factory_options", [])),
            service_options=cast(list, stan_json.get("service_options", [])),
            grid=GridVariant(months=valid_months, km_per_year=valid_mileages),
            pricing_margin_pct=marza_pct,
            wibor_pct=settings.default_wibor,
            initial_deposit_pct=wklad_wlasny_pct,
            margin_pct=marza_pct,
        )

        eng = LTRKalkulator(input_data=calc_input, settings=settings)
        matrix = eng.build_matrix()
        return matrix
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bład generowania macierzy: {e}")
