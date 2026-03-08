import logging
from typing import List, Dict, Any, cast, Tuple
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony
from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator
from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput
from core.LTRSubCalculatorCenaZakupu import (
    PurchasePriceCalculator,
    PurchasePriceInput,
    PurchasePriceOption,
)
from core.LTRSubCalculatorAmortyzacja import (
    AmortyzacjaCalculator,
    AmortyzacjaInput,
)
from core.LTRSubCalculatorBudzetMarketingowy import (
    BudzetMarketingowyCalculator,
    BudzetMarketingowyInput,
)
from core.LTRSubCalculatorKosztDzienny import (
    KosztDziennyCalculator,
    KosztDziennyInput,
)
from core.LTRSubCalculatorStawka import (
    StawkaCalculator,
    StawkaInput,
)
from functools import lru_cache


_ENGINE_CATEGORY_TO_ID: Dict[str, int] = {
    "BENZYNA": 1,
    "PB": 1,
    "BENZYNA MHEV": 1,
    "PB-MHEV": 1,
    "DIESEL": 2,
    "ON": 2,
    "DIESEL MHEV": 2,
    "ON-MHEV": 2,
    "HYBRYDA": 3,
    "HEV": 3,
    "PHEV": 4,
    "ELEKTRYCZNY": 5,
    "BEV": 5,
    "EV": 5,
    "LPG": 6,
    "CNG": 7,
    "HYBRYDA PLUG-IN": 4,
}


def _resolve_engine_type_id(engine_category: str) -> int:
    """Mapuje engine_category (np. 'Benzyna mHEV (PB-mHEV)') → engine_type_id."""
    if not engine_category:
        return 1
    upper = engine_category.strip().upper()
    # Try direct match first
    for key, eid in _ENGINE_CATEGORY_TO_ID.items():
        if key in upper:
            return eid
    return 1  # fallback: benzyna


@lru_cache(maxsize=128)
def get_vehicle_from_db(vid: str) -> Dict[str, Any]:
    """Pobiera dane pojazdu z vehicle_synthesis i mapuje na słownik
    zawierający pola wymagane przez sub-kalkulatory.

    Kluczowe pola wynikowe:
        - brand, model, Segment (full SAMAR name)
        - samar_class_id (PK z samar_classes)
        - klasa_wr_id (legacy WR ID → insurance/damage)
        - engine_type_id, power_kw
        - paint_type_id, body_type_id
        - zabudowa_apr_wr, is_metalic, rocznik
    """
    if not vid:
        return {}
    try:
        from core.database import supabase

        res = (
            supabase.table("vehicle_synthesis")
            .select("id, brand, model, synthesis_data, zabudowa_apr_wr")
            .eq("id", vid)
            .execute()
        )
        if not res.data or not isinstance(res.data, list) or len(res.data) == 0:
            return cast(Dict[str, Any], {})

        row = res.data[0]
        sd = row.get("synthesis_data") or {}
        cs = sd.get("card_summary") or {}
        mai = sd.get("mapped_ai_data") or {}

        # Resolve SAMAR class name → samar_classes row
        samar_category = cs.get("samar_category") or mai.get("samar_category") or ""
        samar_class_id = 0
        klasa_wr_id = 0

        if samar_category:
            # Resolve from samar_classes table
            cls_res = (
                supabase.table("samar_classes")
                .select("id, klasa_wr_id, name")
                .execute()
            )

            # Normalize: strip "KLASA " to handle both old and new naming
            # Old: "PODSTAWOWA D ŚREDNIA" vs New: "PODSTAWOWA Klasa D ŚREDNIA"
            def _norm_samar(s: str) -> str:
                return s.strip().upper().replace("KLASA ", "")

            cat_norm = _norm_samar(samar_category)
            for cls_row in cls_res.data or []:
                db_name = str(cls_row.get("name", ""))
                if _norm_samar(db_name) == cat_norm:
                    samar_class_id = int(cls_row["id"])
                    klasa_wr_id = int(cls_row.get("klasa_wr_id") or 0)
                    break

        # Engine type
        engine_category = cs.get("engine_category", "") or ""
        engine_type_id = _resolve_engine_type_id(engine_category)

        # Power
        power_kw_raw = cs.get("power_kw") or 0
        if not power_kw_raw:
            # Try to parse from powertrain string e.g. "1.5 TSI m-HEV (150 KM) 110 kW"
            powertrain = cs.get("powertrain", "") or ""
            import re

            kw_match = re.search(r"(\d+)\s*kW", powertrain, re.IGNORECASE)
            if kw_match:
                power_kw_raw = int(kw_match.group(1))

        vehicle_dict: Dict[str, Any] = {
            "id": vid,
            "brand": row.get("brand", ""),
            "model": row.get("model", ""),
            "Segment": samar_category,
            "samar_class_id": samar_class_id,
            "klasa_wr_id": klasa_wr_id,
            "engine_type_id": engine_type_id,
            "power_kw": float(power_kw_raw or 100),
            "paint_type_id": cs.get("paint_type_id"),
            "body_type_id": cs.get("body_type_id"),
            "zabudowa_apr_wr": bool(row.get("zabudowa_apr_wr", False)),
            "is_metalic": cs.get("is_metalic_paint", True),
            "rocznik": cs.get("rocznik", "current"),
        }
        return vehicle_dict

    except Exception as exc:
        import logging

        logging.warning("get_vehicle_from_db error for %s: %s", vid, exc)
    return cast(Dict[str, Any], {})


@lru_cache(maxsize=128)
def get_samar_klasa_from_db(klasa_id: str) -> Dict[str, Any]:
    """Pobiera parametry serwisowe (i nie tylko) przypisane do klasy pojazdu"""
    if not klasa_id:
        return {}
    try:
        from core.database import supabase

        res = supabase.table("samar_klasa_wr").select("*").eq("id", klasa_id).execute()
        if res.data and len(res.data) > 0:
            return cast(Dict[str, Any], res.data[0])
    except Exception:
        pass
    return {}


@lru_cache(maxsize=128)
def get_insurance_rates_from_db(klasa_id: str) -> List[Dict[str, Any]]:
    """Pobiera tabelę ubezpieczeń dla danej klasy z fallbackiem na domyślne (NULL)."""
    try:
        from core.database import supabase

        # 1. Szukaj stawek dla konkretnej klasy
        if klasa_id:
            res = (
                supabase.table("ltr_admin_ubezpieczenia")
                .select("*")
                .eq("KlasaId", klasa_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(List[Dict[str, Any]], res.data)

        # 2. Fallback: stawki domyślne (KlasaId IS NULL)
        res_default = (
            supabase.table("ltr_admin_ubezpieczenia")
            .select("*")
            .is_("KlasaId", "null")
            .execute()
        )
        if res_default.data and len(res_default.data) > 0:
            return cast(List[Dict[str, Any]], res_default.data)

    except Exception as e:
        print(f"Error fetching insurance rates: {e}")
    return []


@lru_cache(maxsize=128)
def _resolve_klasa_wr_to_samar_id(klasa_wr_id: str) -> int | None:
    """Mapuje klasa_wr_id (WR) → samar_classes.id (PK)."""
    try:
        from core.database import supabase

        res = (
            supabase.table("samar_classes")
            .select("id")
            .eq("klasa_wr_id", klasa_wr_id)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return int(res.data[0]["id"])
    except Exception as e:
        print(f"Error resolving klasa_wr_id={klasa_wr_id}: {e}")
    return None


@lru_cache(maxsize=128)
def get_replacement_car_rate_from_db(klasa_id: str) -> Dict[str, Any]:
    """Pobiera parametry auta zastępczego z tabeli replacement_car_rates.

    UWAGA: klasa_id to klasa_wr_id z pojazdy_master (system WR).
    replacement_car_rates używa samar_class_id (PK z samar_classes).
    Wymagana translacja: klasa_wr_id → samar_classes.id → replacement_car_rates.
    """
    try:
        from core.database import supabase

        if klasa_id:
            # Krok 1: Przetłumacz klasa_wr_id → samar_classes.id (PK)
            samar_pk = _resolve_klasa_wr_to_samar_id(klasa_id)
            if samar_pk is None:
                print(
                    f"WARN: brak samar_classes z klasa_wr_id={klasa_id}"
                    " — auto zastępcze = 0"
                )
                return {}

            # Krok 2: Pobierz stawkę z replacement_car_rates
            res = (
                supabase.table("replacement_car_rates")
                .select("*")
                .eq("samar_class_id", samar_pk)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])

        # Fallback: brak danych dla tej klasy — zwróć pusty dict (koszt = 0)
    except Exception as e:
        print(f"Error fetching replacement car rate: {e}")
    return {}


@lru_cache(maxsize=128)
def get_damage_coefficients_from_db(klasa_id: str) -> Dict[str, Any]:
    """Pobiera współczynniki szkodowe dla klasy pojazdu (bez fallbacku na null)"""
    try:
        from core.database import supabase

        if klasa_id:
            res = (
                supabase.table("ltr_admin_wspolczynniki_szkodowe")
                .select("*")
                .eq("klasa_wr_id", klasa_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])

    except Exception as e:
        print(f"Error fetching damage coefficients: {e}")
    return {}


class LTRKalkulator:
    """Rdzeń budujący Matrix dla zadanego CalculatorInput"""

    def __init__(self, input_data: Any, settings: Any):
        self.input_data = input_data
        self.settings = settings

        # Inicjalizacja subkalkulatorów
        self.tires_calc = LTRSubCalculatorOpony(
            z_oponami=getattr(self.input_data, "z_oponami", True),
            klasa_opony_string=getattr(self.input_data, "klasa_opony_string", ""),
            srednica_felgi=getattr(self.input_data, "srednica_felgi", 0) or 0,
            korekta_kosztu=getattr(self.input_data, "korekta_kosztu_opon", False),
            koszt_opon_korekta=getattr(self.input_data, "koszt_opon_korekta", 0.0),
            sets_needed_override=getattr(
                self.input_data, "liczba_kompletow_opon", None
            ),
        )

        # Load vehicle if needed
        vid = getattr(self.input_data, "vehicle_id", "")
        if isinstance(self.input_data, dict):
            vid = self.input_data.get("vehicle_id", "")
        self.vehicle = get_vehicle_from_db(vid) if vid else {}

        klasa_id = self.vehicle.get("klasa_wr_id", "")
        self.samar_klasa = get_samar_klasa_from_db(klasa_id) if klasa_id else {}

        # Service calculator (ASO/nonASO)
        self.service_cost_type = getattr(self.input_data, "service_cost_type", "ASO")
        # Map frontend "nonASO" → backend pattern "NON-ASO"
        self._opcja_serwisowa = (
            "NON-ASO" if self.service_cost_type == "nonASO" else "ASO"
        )

    def _calculate_capex(self) -> Tuple[float, float]:
        """Kalkuluje wejściową sumę finansowaną (CAPEX) autorskim kalkulatorem (V3)"""
        base_net = self.input_data.base_price_net

        options = []
        for opt in self.input_data.factory_options:
            options.append(
                PurchasePriceOption(
                    price_net=opt.price_net,
                    name=opt.name,
                    is_service=False,
                    is_discountable=not opt.no_discount,
                )
            )

        for opt in self.input_data.service_options:
            options.append(
                PurchasePriceOption(
                    price_net=opt.price_net,
                    name=opt.name,
                    is_service=True,
                    is_discountable=not opt.no_discount,
                )
            )

        # W nowej architekturze V3 moduł GSM zawsze doliczany jest do Ceny Zakupu.
        pp_input = PurchasePriceInput(
            base_price_net=base_net,
            options=options,
            discount_pct=self.input_data.discount_pct,
            add_gsm_to_capex=True,
            gsm_device_cost_net=float(getattr(self.settings, "cost_gsm_device", 469.0)),
            gsm_installation_cost_net=float(
                getattr(self.settings, "cost_gsm_installation", 150.0)
            ),
            pakiet_serwisowy_net=float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            ),
        )

        calc = PurchasePriceCalculator(pp_input)
        res = calc.calculate()

        # total_options_capex is undiscounted sum — we need the discounted value.
        # total_capex includes: discounted_base + disc_opts*factor + non_disc
        #   + svc_opts + pakiet + transport + tires + gsm
        # We want only: disc_opts*factor + non_disc + svc_opts + pakiet
        discounted_options_capex = (
            res.total_capex
            - res.discounted_base
            - res.tires_capex_net
            - res.gsm_capex_net
            - res.transport_fee_net
        )
        return res.discounted_base, discounted_options_capex

    def build_matrix(self) -> List[Dict[str, Any]]:
        """Przelicza wszystkie warianty i zwraca siatkę (List of Cells)"""
        # V3 Matrix Generation: Linear 1D Grid (6 - 84 months) based on reference usage (Card Summary)
        okres_bazowy = getattr(self.input_data, "okres_bazowy", 48)
        przebieg_bazowy = getattr(self.input_data, "przebieg_bazowy", 140000)

        if okres_bazowy <= 0:
            okres_bazowy = 48

        # Obliczenie wskaźnika stałego zużycia na miesiąc
        km_per_month = przebieg_bazowy / okres_bazowy

        cells = []

        vehicle_capex, options_capex = self._calculate_capex()
        capex = vehicle_capex + options_capex
        # V1 parity: WR curve uses full catalogue prices (no discount)
        base_price_net_full = float(getattr(self.input_data, "base_price_net", 0))

        # Instantiate RV calculator once (shared across all months)
        from core.LTRSubCalculatorUtrataWartosciNew import (
            LTRSubCalculatorUtrataWartosciNew,
        )

        rv_calc = LTRSubCalculatorUtrataWartosciNew(self.vehicle, self.input_data)

        # Opcje pod Wartość Rezydualną (Zawsze Fabryczne + Serwisowe z include_in_wr)
        base_wr_options = sum(opt.price_net for opt in self.input_data.factory_options)
        base_wr_options += sum(
            opt.price_net
            for opt in self.input_data.service_options
            if getattr(opt, "include_in_wr", False)
        )

        # Raw margin percentage (e.g. 2.0%)
        margin_pct = self.input_data.pricing_margin_pct / 100.0
        if margin_pct >= 1.0:
            margin_pct = 0.9999  # Prevention of division by zero

        for months in range(6, 85, 6):
            total_km = int(km_per_month * months)
            km_per_year = int(12 * total_km / months) if months > 0 else 0

            # 1. Koszty Opon
            tires_res = self.tires_calc.calculate_cost(months=months, total_km=total_km)
            capex_for_financing = (
                capex + tires_res["capex_initial_set"]
            )  # Wartość opony do rat

            # 2. Koszty Techniczne/Operacyjne — legacy ops_calc usunięty (Fix 2)

            # 3. Finansowanie i Utrata Wartości (SAMAR SQL Subcalculator / UtrataWartosciNew)

            # VAT Rate to apply gross math
            vat_rate = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate > 10.0:
                vat_rate = 1.0 + (vat_rate / 100.0)

            # V1 parity: WR curve uses full catalogue brutto (no discount)
            rv_res = rv_calc.calculate_values(
                months=months,
                total_km=total_km,
                base_vehicle_capex_gross=base_price_net_full * vat_rate,
                options_capex_gross=(base_wr_options + tires_res["capex_initial_set"])
                * vat_rate,
            )

            vr_samar = rv_res["WR"]

            # Obliczenie PMT (V1 parity — dwa warianty z/bez czynszu)
            vat_rate_fin = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate_fin > 10.0:
                vat_rate_fin = 1.0 + (vat_rate_fin / 100.0)
            finance_input = FinanseInput(
                WartoscPoczatkowaNetto=capex_for_financing,
                WrPrzewidywanaCenaSprzedazy=vr_samar,
                CzynszInicjalny=float(
                    getattr(self.input_data, "CzynszKwota", 0.0) or 0.0
                ),
                CzynszProcent=float(
                    getattr(self.input_data, "CzynszProcent", 0.0) or 0.0
                ),
                RodzajCzynszu=str(getattr(self.input_data, "RodzajCzynszu", "Kwotowo")),
                StawkaVAT=vat_rate_fin,
                Okres=months,
                WIBORProcent=float(getattr(self.input_data, "wibor_pct", 0.0) or 0.0),
                MarzaFinansowaProcent=float(
                    getattr(self.input_data, "margin_pct", 0.0) or 0.0
                ),
            )
            finance_calc = FinanseCalculator(finance_input)
            finance_res = finance_calc.calculate()

            # Wynik Opon z dict
            tires_base = float(
                tires_res["monthly_hardware"]
                + tires_res["monthly_storage"]
                + tires_res["monthly_swaps"]
            )
            # Wynik Serwisu — nowy ServiceCalculator (ASO/nonASO z DB + floor normatywnego przebiegu)
            normatywny_przebieg = getattr(self.settings, "normatywny_przebieg_mc", 1667)
            pakiet_serwisowy_val = float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            )
            inne_koszty_val = float(
                getattr(
                    self.input_data,
                    "inne_koszty_serwisowania_netto",
                    0.0,
                )
            )
            service_input = ServiceCalculatorInput(
                z_serwisem=True,
                opcja_serwisowa=self._opcja_serwisowa,
                normatywny_przebieg_mc=normatywny_przebieg,
                samar_class_id=int(self.vehicle.get("samar_class_id", 0))
                if self.vehicle
                else 0,
                engine_type_id=int(self.vehicle.get("engine_type_id", 1))
                if self.vehicle
                else 1,
                power_kw=float(self.vehicle.get("power_kw", 100))
                if self.vehicle
                else 100.0,
                przebieg=total_km,
                okres=months,
                pakiet_serwisowy=pakiet_serwisowy_val,
                inne_koszty_serwisowania_netto=inne_koszty_val,
            )
            service_calc = ServiceCalculator(service_input)
            service_from_new = service_calc.calculate()
            # Use new ServiceCalculator result; warn if zero (no legacy fallback)
            service_base = service_from_new
            service_fallback_used = service_from_new <= 0
            if service_fallback_used:
                logging.warning(
                    "ServiceCalculator returned 0 for months=%d, "
                    "samar_class_id=%s, engine_type_id=%s — brak stawek serwisowych w DB",
                    months,
                    self.vehicle.get("samar_class_id", "?") if self.vehicle else "?",
                    self.vehicle.get("engine_type_id", "?") if self.vehicle else "?",
                )

            # --- SUB-KALKULATOR: AMORTYZACJA (V1 port) ---
            if getattr(self.input_data, "depreciation_pct", None) is not None:
                procent_amortyzacji_miesiecznie = float(
                    self.input_data.depreciation_pct
                )
            else:
                amort_input = AmortyzacjaInput(
                    wp=capex_for_financing, wr=vr_samar, okres=months
                )
                amort_result = AmortyzacjaCalculator(amort_input).calculate()
                procent_amortyzacji_miesiecznie = amort_result.amortyzacja_procent

            # --- SUB-KALKULATOR: UBEZPIECZENIE ---
            klasa_id = self.vehicle.get("klasa_wr_id", "") if self.vehicle else ""
            insurance_rates = get_insurance_rates_from_db(klasa_id)
            damage_coeffs = get_damage_coefficients_from_db(klasa_id)
            ins_calc = InsuranceCalculator(
                insurance_rates=insurance_rates,  # type: ignore
                damage_coefficients=damage_coeffs,  # type: ignore
                settings=self.settings,  # type: ignore
                amortization_pct=procent_amortyzacji_miesiecznie,  # type: ignore
                total_km=total_km,  # type: ignore
            )

            insurance_res = ins_calc.calculate_cost(months, capex_for_financing)  # type: ignore
            insurance_base = float(insurance_res["monthly_insurance"])
            insurance_total = float(
                insurance_res.get("total_insurance", insurance_base * months)
            )

            # --- SUB-KALKULATOR: SAMOCHÓD ZASTĘPCZY ---
            rc_rate = get_replacement_car_rate_from_db(klasa_id)
            rc_calc = ReplacementCarCalculator(rc_rate)  # type: ignore
            rc_res = rc_calc.calculate_cost(
                months=months, enabled=self.input_data.replacement_car_enabled
            )
            rc_base = float(rc_res["monthly_replacement_car"])
            rc_total = float(rc_res.get("total_replacement_car", rc_base * months))

            # --- SUB-KALKULATOR: KOSZTY DODATKOWE ---
            add_calc = AdditionalCostsCalculator(self.settings, self.input_data, months)
            add_calc_res = add_calc.calculate_cost()
            additional_costs_base = float(add_calc_res["monthly_additional_costs"])
            additional_costs_total = additional_costs_base * months

            # Totale do sub-kalkulatorów V1
            tires_total = tires_base * months
            service_total = service_base * months
            utrata_z_czynszem = float(
                rv_res.get(
                    "UtrataWartosciZCzynszemInicjalnym", capex_for_financing - vr_samar
                )
            )
            utrata_bez_czynszu = float(rv_res["UtrataWartosciBEZczynszu"])

            # --- SUB-KALKULATOR: KOSZT DZIENNY (V1 port) ---
            kd_input = KosztDziennyInput(
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
            )
            kd_result = KosztDziennyCalculator(kd_input).calculate()

            # --- SUB-KALKULATOR: STAWKA (V1 port – pełny rozkład marży) ---
            stawka_input = StawkaInput(
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
                marza=margin_pct,
                czynsz_inicjalny=float(finance_res.CzynszInicjalnyNetto),
            )
            stawka_result = StawkaCalculator(stawka_input).calculate()

            # --- SUB-KALKULATOR: BUDŻET MARKETINGOWY (V1 port) ---
            vat_rate_mult = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate_mult > 10.0:
                vat_rate_mult = 1.0 + (vat_rate_mult / 100.0)
            budzet_mktg_ltr = getattr(self.settings, "budzet_marketingowy_ltr", 0.0)
            bm_input = BudzetMarketingowyInput(
                wr_przewidywana_cena_sprzedazy=vr_samar,
                stawka_vat=vat_rate_mult,
                budzet_marketingowy_ltr=budzet_mktg_ltr,
            )
            bm_result = BudzetMarketingowyCalculator(bm_input).calculate()

            # Wyniki z nowego StawkaCalculator
            total_base = kd_result.koszt_mc
            total_price = stawka_result.oferowana_stawka

            cells.append(
                {
                    "months": months,
                    "km_per_year": km_per_year,
                    "total_km": total_km,
                    "base_cost_net": round(total_base, 2),
                    "price_net": round(total_price, 2),
                    "rv_samar_net": round(vr_samar, 2),
                    "rv_lo_net": round(rv_res["WRdlaLO"], 2),
                    "utrata_wartosci_bez_czynszu_net": round(
                        rv_res["UtrataWartosciBEZczynszu"], 2
                    ),
                    # Nowe pola V1
                    "koszt_dzienny": round(kd_result.koszt_dzienny, 2),
                    "koszty_ogolem": round(kd_result.koszty_ogolem, 2),
                    "amortyzacja_pct": round(procent_amortyzacji_miesiecznie, 6),
                    "korekta_wr_maks": round(bm_result.korekta_wr_maks, 2),
                    "marza_mc": round(stawka_result.marza_mc, 2),
                    "marza_na_kontrakcie": round(stawka_result.marza_na_kontrakcie, 2),
                    "marza_na_kontrakcie_pct": round(
                        stawka_result.marza_na_kontrakcie_procent, 6
                    ),
                    "czynsz_finansowy": round(stawka_result.czynsz_finansowy, 2),
                    "czynsz_techniczny": round(stawka_result.czynsz_techniczny, 2),
                    "breakdown": {
                        "finance": {
                            "base": round(stawka_result.koszt_finansowy.koszt_mc, 2),
                            "margin": round(
                                stawka_result.koszt_finansowy.kwota_marzy_korekta, 2
                            ),
                            "price": round(
                                stawka_result.koszt_finansowy.koszt_plus_marza_korekta,
                                2,
                            ),
                            "monthly_pmt_z_czynszem": round(
                                finance_res.monthly_pmt_z_czynszem, 2
                            ),
                            "monthly_pmt_bez_czynszu": round(
                                finance_res.monthly_pmt_bez_czynszu, 2
                            ),
                            "suma_odsetek_z_czynszem": round(
                                finance_res.SumaOdsetekZczynszem, 2
                            ),
                            "suma_odsetek_bez_czynszu": round(
                                finance_res.SumaOdsetekBEZczynszu, 2
                            ),
                            "czynsz_inicjalny_netto": round(
                                finance_res.CzynszInicjalnyNetto, 2
                            ),
                            "czynsz_procent": round(
                                finance_res.CzynszInicjalnyProcent, 2
                            ),
                            "wykup_kwota": round(finance_res.WykupKwota, 2),
                            "rozklad_marzy": round(
                                stawka_result.koszt_finansowy.rozklad_marzy, 4
                            ),
                        },
                        "technical": {
                            "service": {
                                "base": round(stawka_result.koszt_serwis.koszt_mc, 2),
                                "margin": round(
                                    stawka_result.koszt_serwis.kwota_marzy_korekta, 2
                                ),
                                "price": round(
                                    stawka_result.koszt_serwis.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_serwis.rozklad_marzy, 4
                                ),
                            },
                            "tires": {
                                "base": round(stawka_result.koszt_opony.koszt_mc, 2),
                                "margin": round(
                                    stawka_result.koszt_opony.kwota_marzy_korekta, 2
                                ),
                                "price": round(
                                    stawka_result.koszt_opony.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_opony.rozklad_marzy, 4
                                ),
                                "ilosc_opon": tires_res["IloscOpon"],
                            },
                            "insurance": {
                                "base": round(
                                    stawka_result.koszt_ubezpieczenie.koszt_mc, 2
                                ),
                                "margin": round(
                                    stawka_result.koszt_ubezpieczenie.kwota_marzy_korekta,
                                    2,
                                ),
                                "price": round(
                                    stawka_result.koszt_ubezpieczenie.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_ubezpieczenie.rozklad_marzy, 4
                                ),
                            },
                            "replacement_car": {
                                "base": round(
                                    stawka_result.koszt_samochod_zastepczy.koszt_mc, 2
                                ),
                                "margin": round(
                                    stawka_result.koszt_samochod_zastepczy.kwota_marzy_korekta,
                                    2,
                                ),
                                "price": round(
                                    stawka_result.koszt_samochod_zastepczy.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_samochod_zastepczy.rozklad_marzy,
                                    4,
                                ),
                            },
                            "additional_costs": {
                                "base": round(stawka_result.koszt_admin.koszt_mc, 2),
                                "margin": round(
                                    stawka_result.koszt_admin.kwota_marzy_korekta, 2
                                ),
                                "price": round(
                                    stawka_result.koszt_admin.koszt_plus_marza_korekta,
                                    2,
                                ),
                                "rozklad_marzy": round(
                                    stawka_result.koszt_admin.rozklad_marzy, 4
                                ),
                            },
                        },
                    },
                    "status": "OK" if total_km <= 200000 else "WARNING_HIGH_KM",
                    "warnings": {
                        "service_fallback_used": service_fallback_used,
                        "replacement_car_missing": rc_base == 0.0
                        and self.input_data.replacement_car_enabled,
                    },
                }
            )

        return cells
