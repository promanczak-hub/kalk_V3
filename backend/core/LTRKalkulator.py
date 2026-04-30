

import logging
from typing import Any, Dict, List, Tuple

from core.database import supabase
from core.LTRSubCalculatorAmortyzacja import AmortyzacjaCalculator, AmortyzacjaInput
from core.LTRSubCalculatorBudzetMarketingowy import (
    BudzetMarketingowyCalculator,
    BudzetMarketingowyInput,
)
from core.LTRSubCalculatorCenaZakupu import (
    PurchasePriceCalculator,
    PurchasePriceInput,
    PurchasePriceOption,
)
from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput
from core.LTRSubCalculatorKosztDzienny import KosztDziennyCalculator, KosztDziennyInput
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony
from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput
from core.LTRSubCalculatorStawka import StawkaCalculator, StawkaInput
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator
from core.LTRSubCalculatorUtrataWartosciNew import LTRSubCalculatorUtrataWartosciNew
from core.ltr_db_fetchers import (
    get_damage_coefficients_from_db,
    get_insurance_rates_from_db,
    get_replacement_car_rate_from_db,
    get_vehicle_from_db,
)
from core.ltr_report_builder import build_report_html, to_koszt_dict
from core.ltr_vehicle_resolvers import (
    _resolve_body_type_id_from_name,
    _resolve_engine_type_id,
    _resolve_paint_type_id_from_name,
    _resolve_samar_class_id_from_name,
    _resolve_zabudowa_type_id_from_name,
)


class LTRKalkulator:
    """RdzeĹ„ budujÄ…cy Matrix dla zadanego CalculatorInput"""

    def __init__(
        self,
        input_data: Any,
        settings: Any,
        pipeline_dto: Any = None,
        trace_id: str | None = None,
    ):
        self.input_data = input_data
        self.settings = settings
        self.pipeline_dto = pipeline_dto
        self.trace_id = trace_id or "UNKNOWN_TRACE_ID"

        # Inicjalizacja subkalkulatorów
        self.tires_calc = LTRSubCalculatorOpony(
            z_oponami=getattr(self.input_data, "z_oponami", True),
            klasa_opony_string=getattr(self.input_data, "klasa_opony_string", ""),
            srednica_felgi=getattr(self.input_data, "srednica_felgi", 0) or 0,
            sets_needed_override=getattr(
                self.input_data, "liczba_kompletow_opon", None
            ),
            odkup_opon_enabled=getattr(self.input_data, "odkup_opon_enabled", False),
        )

        # Load vehicle if needed
        from core.models import VehicleDataDTO

        if self.pipeline_dto:
            self.vehicle = self.pipeline_dto.vehicle
            self.samar_id = self.vehicle.samar_class_id
            self.samar_klasa = self.pipeline_dto.samar_class.model_dump()
        else:
            vid = getattr(self.input_data, "vehicle_id", "")
            if isinstance(self.input_data, dict):
                vid = self.input_data.get("vehicle_id", "")
            raw_v = get_vehicle_from_db(vid) if vid else {}

            self.samar_id = raw_v.get("samar_class_id", 0)
            raw_v["samar_class_id"] = self.samar_id

            raw_s = {}

            if raw_v:
                from core.models import VehicleDataDTO

                self.vehicle = VehicleDataDTO(
                    id=str(raw_v.get("id", "0")),
                    brand=str(raw_v.get("brand", "UNKNOWN")),
                    model=str(raw_v.get("model", "UNKNOWN")),
                    engine_type_id=int(raw_v.get("engine_type_id", 0)),
                    samar_class_id=int(self.samar_id),
                    **{
                        k: v
                        for k, v in raw_v.items()
                        if k
                        not in [
                            "id",
                            "brand",
                            "model",
                            "engine_type_id",
                            "samar_class_id",
                        ]
                    },
                )
            else:
                self.vehicle = VehicleDataDTO(
                    id="0",
                    brand="UNKNOWN",
                    model="UNKNOWN",
                    engine_type_id=0,
                    samar_class_id=0,
                )
            self.samar_klasa = raw_s

        # Override synthesized vehicle data with explicit dropdown input values.
        self._apply_explicit_input_overrides()

        # Service calculator (ASO/nonASO)
        self.include_servicing = bool(
            getattr(self.input_data, "include_servicing", True)
        )
        self.express_pays_insurance = bool(
            getattr(self.input_data, "express_pays_insurance", True)
        )
        self.service_cost_type = str(
            getattr(self.input_data, "service_cost_type", "ASO") or "ASO"
        ).strip()
        normalized_service_type = (
            self.service_cost_type.upper().replace("-", "").replace("_", "")
        )
        if normalized_service_type in {"NONASO", "NIEASO"}:
            self._opcja_serwisowa = "NON-ASO"
        elif normalized_service_type == "ASO":
            self._opcja_serwisowa = "ASO"
        else:
            raise ValueError(
                f"Nieobslugiwany service_cost_type: '{self.service_cost_type}'. "
                "Dozwolone: ASO / NON-ASO."
            )

    def _apply_explicit_input_overrides(self) -> None:
        if not self.vehicle:
            from core.models import VehicleDataDTO

            self.vehicle = VehicleDataDTO(
                id="0",
                brand="UNKNOWN",
                model="UNKNOWN",
                engine_type_id=0,
                samar_class_id=0,
            )

        input_samar = str(getattr(self.input_data, "samar_category", "") or "").strip()
        if input_samar:
            resolved_samar_id = _resolve_samar_class_id_from_name(input_samar)
            if resolved_samar_id <= 0:
                logging.warning(
                    f"Zignorowano wprowadzona klase SAMAR z dropdownu: '{input_samar}'. Nie rozpoznano ID."
                )
            else:
                self.vehicle.Segment = input_samar
                self.vehicle.samar_class_id = int(resolved_samar_id)
                self.samar_id = int(resolved_samar_id)

        # Nadpisanie mocy z UI payload
        if getattr(self.input_data, "power_kw", None):
            self.vehicle.power_kw = float(self.input_data.power_kw)
        elif getattr(self.input_data, "power_hp", None):
            self.vehicle.power_kw = float(round(self.input_data.power_hp / 1.36))

        input_engine = str(getattr(self.input_data, "engine_name", "") or "").strip()
        if input_engine:
            try:
                resolved_engine_id = _resolve_engine_type_id(input_engine)
                self.vehicle.engine_type_id = int(resolved_engine_id)
            except ValueError as e:
                logging.warning(
                    f"Zignorowano wprowadzona kategorie silnika '{input_engine}': {e}"
                )

        input_body = str(getattr(self.input_data, "body_type_name", "") or "").strip()
        if input_body:
            resolved_body_id = _resolve_body_type_id_from_name(input_body)
            if resolved_body_id:
                self.vehicle.body_type_id = int(resolved_body_id)
            else:
                logging.warning(
                    "Nie rozpoznano typu nadwozia z dropdownu: '%s'; zapis manualny bez body_type_id.",
                    input_body,
                )
            self.vehicle.body_type_name = input_body
            if not getattr(self.vehicle, "zabudowa_type_id", None):
                inferred_zabudowa = _resolve_zabudowa_type_id_from_name(input_body)
                if inferred_zabudowa:
                    self.vehicle.zabudowa_type_id = int(inferred_zabudowa)

        input_paint = str(getattr(self.input_data, "paint_type_name", "") or "").strip()
        if input_paint:
            resolved_paint_id = _resolve_paint_type_id_from_name(input_paint)
            if not resolved_paint_id:
                raise ValueError(
                    f"Nie rozpoznano typu lakieru z dropdownu: '{input_paint}'."
                )
            self.vehicle.paint_type_id = int(resolved_paint_id)

        input_drive = str(getattr(self.input_data, "drive_type", "") or "").strip()
        if input_drive:
            self.vehicle.drive_type = input_drive

        input_zab_type = getattr(self.input_data, "zabudowa_type_id", None)
        if input_zab_type not in (None, ""):
            self.vehicle.zabudowa_type_id = int(input_zab_type)
        elif getattr(self.vehicle, "zabudowa_type_id", None) is None:
            for opt in getattr(self.input_data, "service_options", []) or []:
                opt_name = str(getattr(opt, "name", "") or "")
                inferred_zabudowa = _resolve_zabudowa_type_id_from_name(opt_name)
                if inferred_zabudowa:
                    self.vehicle.zabudowa_type_id = int(inferred_zabudowa)
                    break

        self.vehicle.zabudowa_apr_wr = bool(
            getattr(self.vehicle, "zabudowa_apr_wr", False)
            or getattr(self.vehicle, "zabudowa_type_id", None)
        )

        if hasattr(self.input_data, "vehicle_vintage"):
            self.vehicle.rocznik = getattr(self.input_data, "vehicle_vintage")
        if hasattr(self.input_data, "is_metalic"):
            self.vehicle.is_metalic = bool(getattr(self.input_data, "is_metalic"))

    def _calculate_wr_options_split(self) -> Tuple[float, float, float]:
        """Rozdziel opcje wchodzące do Wartości Rezydualnej na rabatowalne i poza-rabatowe.

        Zwraca: (discountable_wr_options, non_discountable_wr_options, service_options_in_wr)
        - discountable: factory_options gdzie no_discount=False (objęte rabatem producenta)
        - non_discountable: factory_options gdzie no_discount=True (zabudowy dealera, akcesoria
          pozafabryczne — wliczane do amortyzacji w pełnej kwocie, bo również tracą wartość)
        - service_options_in_wr: service_options z include_in_wr=True (zawsze pełna kwota)
        """
        discountable = sum(
            opt.price_net
            for opt in self.input_data.factory_options
            if not getattr(opt, "no_discount", False)
        )
        non_discountable = sum(
            opt.price_net
            for opt in self.input_data.factory_options
            if getattr(opt, "no_discount", False)
        )
        service_in_wr = sum(
            opt.price_net
            for opt in self.input_data.service_options
            if getattr(opt, "include_in_wr", False)
        )
        return discountable, non_discountable, service_in_wr

    def _calculate_capex(self) -> Tuple[float, float, Any]:
        """Kalkuluje wejĹ›ciowÄ… sumÄ™ finansowanÄ… (CAPEX) autorskim kalkulatorem (V3)"""
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

        # Zmiana względem pierwotnego V1: użytkownik chce by wartość CAPEX wprost
        # odpowiadała wybranej klasie opon (np. Premium), eliminując niespójność "Ceny zakupu".
        tires_capex = (
            self.tires_calc.tire_set_price if self.tires_calc.z_oponami else 0.0
        )
        brand = getattr(self.vehicle, "brand", "").strip()
        transport_fee_net = float(getattr(self.input_data, "transport_fee_net", 0.0))
        if brand and transport_fee_net == 0.0:
            try:
                res = (
                    supabase.table("transport_fees")
                    .select("fee_net")
                    .eq("brand", brand)
                    .limit(1)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    transport_fee_net = float(res.data[0].get("fee_net", 0.0))
            except Exception as e:
                logging.getLogger(__name__).error(
                    f"Error fetching transport fee for {brand}: {e}"
                )

        pp_input = PurchasePriceInput(
            base_price_net=base_net,
            options=options,
            discount_pct=self.input_data.discount_pct,
            tires_capex_net=tires_capex,
            add_gsm_to_capex=True,  # Changed to True based on user feedback (V1 Parity)
            gsm_device_cost_net=float(getattr(self.settings, "cost_gsm_device", 469.0)),
            gsm_installation_cost_net=float(
                getattr(self.settings, "cost_gsm_installation", 150.0)
            ),
            pakiet_serwisowy_net=float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            ),
            transport_fee_net=transport_fee_net,
        )

        calc = PurchasePriceCalculator(pp_input)
        res = calc.calculate()

        # total_options_capex is undiscounted sum â€” we need the discounted value.
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
        return res.discounted_base, discounted_options_capex, res

    def build_matrix(self, only_exact: bool = False) -> List[Dict[str, Any]]:
        """Przelicza wszystkie warianty i zwraca siatkÄ™ (List of Cells)"""
        # V3 Matrix Generation: Linear 1D Grid (6 - 84 months) based on reference usage (Card Summary)
        cells = []

        vehicle_capex, options_capex, capex_res = self._calculate_capex()
        capex = vehicle_capex + options_capex
        # V1 parity: WR curve uses full catalogue prices (no discount)
        base_price_net_full = float(getattr(self.vehicle, "price_net", 0.0))
        if base_price_net_full == 0.0:
            base_price_net_full = float(getattr(self.input_data, "base_price_net", 0.0))

        # Instantiate RV calculator once (shared across all months)

        rv_calc = LTRSubCalculatorUtrataWartosciNew(self.vehicle, self.input_data)

        # Opcje pod Wartość Rezydualną (Zawsze Fabryczne + Serwisowe z include_in_wr)
        # Rozdzielamy na rabatowalne / nierabatowalne — flaga no_discount na opcji.
        # WR-options-catalog (do RV) liczymy pełną kwotą (bez rabatu) — odzwierciedla
        # katalogową wartość pojazdu z osprzętem na rynku wtórnym.
        wr_disc_opts, wr_non_disc_opts, wr_service_in_wr = self._calculate_wr_options_split()
        base_wr_options = wr_disc_opts + wr_non_disc_opts + wr_service_in_wr

        # Tryb kalkulacji biznesowej (standard vs bez marży w Reverse Lookup)
        calc_mode = getattr(self.input_data, "calculation_mode", "standard")
        if calc_mode == "base_cost_only":
            margin_pct = 0.0001
        else:
            margin_pct = self.input_data.pricing_margin_pct / 100.0

        if margin_pct >= 1.0:
            margin_pct = 0.9999  # Prevention of division by zero

        matrix_km_mode = str(
            getattr(self.input_data, "matrix_km_mode", "annual") or "annual"
        ).lower()
        if matrix_km_mode not in {"annual", "contract"}:
            matrix_km_mode = "annual"

        # Requested base variant (used to derive default contract-km axis).
        req_months = int(getattr(self.input_data, "okres_bazowy", 48) or 48)
        req_total_km = int(
            getattr(self.input_data, "przebieg_bazowy", 140000) or 140000
        )
        if req_months <= 0:
            req_months = 48

        contract_km_step = int(
            getattr(self.input_data, "matrix_contract_km_step", 10000) or 10000
        )
        if contract_km_step <= 0:
            contract_km_step = 10000

        grid_params: List[tuple[int, int]] = []
        seen_pairs = set()
        contract_km_by_pair: Dict[tuple[int, int], int] = {}

        def add_grid_pair(
            months_val: int,
            km_per_year_val: int,
            contract_km_val: int | None = None,
        ) -> None:
            pair = (int(months_val), int(km_per_year_val))
            if pair in seen_pairs:
                return
            seen_pairs.add(pair)
            grid_params.append(pair)
            if contract_km_val is not None:
                contract_km_by_pair[pair] = int(contract_km_val)

        if only_exact:
            pass  # Skip building the full grid if we only want the exact requested tile
        else:
            # V3 Matrix Strategy: Use contract mileage mode with 5000km step
            # This significantly reduces the payload size and speeds up calculations.
            contract_km_min = 40000
            contract_km_max = 300000
            contract_km_step = 5000

            for m in (24, 36, 48, 60):
                for total_km_contract in range(
                    contract_km_min,
                    contract_km_max + 1,
                    contract_km_step,
                ):
                    km_py = int(round((total_km_contract / m) * 12))
                    add_grid_pair(m, km_py, total_km_contract)

        # Inject requested base period/mileage into the grid.
        if req_months > 0:
            req_km_per_year = int(round((req_total_km / req_months) * 12))
            add_grid_pair(req_months, req_km_per_year, req_total_km)

        for months, km_per_year in grid_params:
            total_km = contract_km_by_pair.get(
                (months, km_per_year), int((km_per_year / 12) * months)
            )

            # 1. Koszty Opon — per-komórka korekta z mapy wejściowej
            _correction_map: Dict[str, float] = (
                getattr(self.input_data, "koszt_opon_korekta", {}) or {}
            )
            _cell_key = f"{months}_{total_km}"
            _correction_for_cell = (
                _correction_map.get(_cell_key, 0.0)
                if getattr(self.input_data, "korekta_kosztu_opon", False)
                else 0.0
            )
            tires_res = self.tires_calc.calculate_cost(
                months=months, total_km=total_km, correction_gross=_correction_for_cell
            )
            capex_for_financing = (
                capex + tires_res["capex_initial_set"]
            )  # WartoĹ›Ä‡ opony do rat

            # 2. Koszty Techniczne/Operacyjne â€” legacy ops_calc usuniÄ™ty (Fix 2)

            # W V1 Utrata Wartości i WR liczone są na Cenie pojazdu (po rabacie) + opcje fabryczne
            # FIX: Rabat aplikujemy TYLKO do opcji rabatowalnych. Zabudowy dealera (no_discount=True)
            # i opcje serwisowe wchodzą do amortyzacji w pełnej kwocie — tracą wartość razem
            # z pojazdem ale nie są obniżone rabatem producenta przy zakupie.
            discount_pct = getattr(self.input_data, "discount_pct", 0) / 100.0
            discounted_factory_options = wr_disc_opts * (1 - discount_pct)
            wp_amortyzacja = (
                vehicle_capex
                + discounted_factory_options
                + wr_non_disc_opts
                + wr_service_in_wr
            )

            # VAT Rate to apply gross math
            vat_rate = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate > 10.0:
                vat_rate = 1.0 + (vat_rate / 100.0)

            # V1 parity: WR curve uses full catalogue brutto (no discount)
            # Uzywamy tylko opcji wp_amortyzacja do WR
            rv_calc_v3 = LTRSubCalculatorUtrataWartosciNew(
                self.vehicle, self.input_data
            )
            rv_res = rv_calc_v3.calculate_values(
                months=months,
                total_km=total_km,
                base_vehicle_catalog_gross=base_price_net_full * vat_rate,
                options_catalog_gross=base_wr_options * vat_rate,
            )

            vr_samar = rv_res["WR"]

            # Obliczenie PMT (V1 parity â€” dwa warianty z/bez czynszu)
            vat_rate_fin = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate_fin > 10.0:
                vat_rate_fin = 1.0 + (vat_rate_fin / 100.0)
            _initial_deposit_pct = float(
                getattr(self.input_data, "initial_deposit_pct", 0.0) or 0.0
            )
            finance_input = FinanseInput(
                WartoscPoczatkowaNetto=capex_for_financing,
                WrPrzewidywanaCenaSprzedazy=vr_samar,
                CzynszInicjalny=0.0,
                CzynszProcent=_initial_deposit_pct,
                RodzajCzynszu="Procentowo" if _initial_deposit_pct > 0 else "Kwotowo",
                StawkaVAT=vat_rate_fin,
                Okres=months,
                WIBORProcent=float(
                    self.input_data.wibor_pct
                    if getattr(self.input_data, "wibor_pct", None) is not None
                    else getattr(self.settings, "default_wibor", 5.0)
                ),
                MarzaFinansowaProcent=float(
                    self.input_data.margin_pct
                    if getattr(self.input_data, "margin_pct", None) is not None
                    else getattr(self.settings, "default_ltr_margin", 2.0)
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
            # Wynik Serwisu ? nowy ServiceCalculator (ASO/nonASO z DB + floor normatywnego przebiegu)
            normatywny_przebieg = int(
                getattr(self.settings, "normatywny_przebieg_mc", 0) or 0
            )
            if normatywny_przebieg <= 0:
                raise ValueError(
                    "Brak poprawnej wartosci `normatywny_przebieg_mc` w Control Center."
                )

            if not self.samar_id:
                raise ValueError(
                    "Brak `samar_class_id` dla pojazdu. Uzupelnij klase SAMAR w danych wejsciowych."
                )

            engine_type_id = int(getattr(self.vehicle, "engine_type_id", 0) or 0)
            if engine_type_id <= 0:
                engine_name_input = getattr(self.input_data, "engine_name", None)
                if engine_name_input:
                    try:
                        engine_type_id = _resolve_engine_type_id(engine_name_input)
                    except Exception:
                        pass

            if engine_type_id <= 0:
                raise ValueError(
                    "Brak `engine_type_id` dla pojazdu. Uzupelnij typ silnika w danych wejsciowych."
                )

            power_kw_input = getattr(self.input_data, "power_kw", None)
            if power_kw_input and float(power_kw_input) > 0:
                power_kw = float(power_kw_input)
            else:
                power_kw_val = getattr(self.vehicle, "power_kw", 0.0)
                power_kw = float(power_kw_val if power_kw_val is not None else 0.0)

            if power_kw <= 0.0:
                raise ValueError(
                    f"Brak poprawnej mocy `power_kw` pojazdu. power_kw_input={power_kw_input}, self.vehicle_power_kw={getattr(self.vehicle, 'power_kw', None)}"
                )

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
                z_serwisem=self.include_servicing,
                opcja_serwisowa=self._opcja_serwisowa,
                normatywny_przebieg_mc=normatywny_przebieg,
                samar_class_id=int(self.samar_id),
                brand_normalized=str(getattr(self.vehicle, "brand", "")),
                fuel_type=str(
                    getattr(
                        self.vehicle,
                        "engine_category",
                        getattr(self.input_data, "engine_name", ""),
                    )
                ),
                drive_type=str(getattr(self.vehicle, "drive_type", "")),
                gearbox_type=str(
                    getattr(
                        self.vehicle,
                        "gearbox",
                        getattr(self.input_data, "gearbox_name", ""),
                    )
                ),
                przebieg=total_km,
                okres=months,
                pakiet_serwisowy=pakiet_serwisowy_val,
                inne_koszty_serwisowania_netto=inne_koszty_val,
            )
            service_calc = ServiceCalculator(service_input)
            service_from_new_dict = service_calc.calculate()
            service_from_new = float(service_from_new_dict["monthly_service"])
            # Use new ServiceCalculator result; fail-fast for missing table parameters.
            service_base = service_from_new
            service_fallback_used = False
            if self.include_servicing and service_from_new <= 0:
                service_fallback_used = True
                raise ValueError(
                    f"Brak stawek serwisowych (ServiceCalculator zwrocil 0) dla "
                    f"okres={months}, klasa={getattr(self.vehicle, 'samar_class_id', '?')}, "
                    f"silnik={getattr(self.vehicle, 'engine_type_id', '?')}. "
                    f"Uzupelnij brakujace dane w tabeli `samar_service_costs`."
                )

            # --- SUB-KALKULATOR: AMORTYZACJA (V1 port) ---
            if getattr(self.input_data, "depreciation_pct", None) is not None:
                procent_amortyzacji_miesiecznie = float(
                    self.input_data.depreciation_pct
                )
            else:
                amort_input = AmortyzacjaInput(
                    wp=wp_amortyzacja,
                    wr=vr_samar,
                    okres=months,
                )
                amort_result = AmortyzacjaCalculator(amort_input).calculate()
                procent_amortyzacji_miesiecznie = amort_result.amortyzacja_procent

            # --- SUB-KALKULATOR: UBEZPIECZENIE ---
            s_class_id = str(self.samar_id)
            insurance_rates = get_insurance_rates_from_db(s_class_id)
            damage_coeffs = get_damage_coefficients_from_db(s_class_id)
            ins_calc = InsuranceCalculator(
                insurance_rates=insurance_rates,  # type: ignore
                damage_coefficients=damage_coeffs,  # type: ignore
                settings=self.settings,  # type: ignore
                amortization_pct=procent_amortyzacji_miesiecznie,  # type: ignore
                total_km=total_km,  # type: ignore
            )

            insurance_res = ins_calc.calculate_cost(months, capex_for_financing, enabled=self.express_pays_insurance)  # type: ignore
            insurance_base = float(insurance_res["monthly_insurance"])
            insurance_total = float(
                insurance_res.get("total_insurance", insurance_base * months)
            )

            # --- SUB-KALKULATOR: SAMOCHOD ZASTEPCZY ---
            rc_rate = get_replacement_car_rate_from_db(s_class_id)
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

            # Totale do sub-kalkulatorĂłw V1
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

            # --- SUB-KALKULATOR: STAWKA (V1 port â€“ peĹ‚ny rozkĹ‚ad marĹĽy) ---
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

            # --- SUB-KALKULATOR: BUDĹ»ET MARKETINGOWY (V1 port) ---
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

            # Wyniki z nowego StawkaCalculator (uĹĽyte bezpoĹ›rednio niĹĽej)

            # --- WYNIK OSTATECZNY (FLAT V1 FORMAT) ---
            print(f"[DEBUG_LTR_FIN] Monate: {months}, KM: {total_km}")
            print(f"[DEBUG_LTR_FIN] WP (capex_for_financing): {capex_for_financing}")
            print(f"[DEBUG_LTR_FIN] RV (vr_samar): {vr_samar}")
            print(
                f"[DEBUG_LTR_FIN] Finance SUMA ODSETEK Z CZYN: {finance_res.SumaOdsetekZczynszem}"
            )
            print(f"[DEBUG_LTR_STAWKA] Podstawa Marzy: {stawka_result.podstawa_marzy}")
            print(f"[DEBUG_LTR_STAWKA] Marza MC: {stawka_result.marza_mc}")
            print(
                f"[DEBUG_LTR_STAWKA] CF (Czynsz Finansowy): {stawka_result.czynsz_finansowy}"
            )
            print(
                f"[DEBUG_LTR_STAWKA] CT (Czynsz Techniczny): {stawka_result.czynsz_techniczny}"
            )
            print(
                f"[DEBUG_LTR_STAWKA] Admin Cost (korekta): {stawka_result.koszt_admin.koszt_plus_marza_korekta}"
            )

            # to_koszt_dict imported from ltr_report_builder

            report_html = ""

            cells.append(
                {
                    "Okres": months,
                    "Przebieg": km_per_year,
                    "PrzebiegKontrakt": total_km,
                    # 1. Stawka (Math.Round(0))
                    "LacznaStawka": round(stawka_result.oferowana_stawka, 0),
                    "CzynszFinansowy": round(stawka_result.czynsz_finansowy, 0),
                    "CzynszTechniczny": round(stawka_result.czynsz_techniczny, 0),
                    "Ubezpieczenie": round(
                        stawka_result.koszt_ubezpieczenie.koszt_plus_marza_korekta, 0
                    ),
                    "Serwis": round(
                        stawka_result.koszt_serwis.koszt_plus_marza_korekta, 0
                    ),
                    "Admin": round(
                        stawka_result.koszt_admin.koszt_plus_marza_korekta, 0
                    ),
                    "Opony": round(
                        stawka_result.koszt_opony.koszt_plus_marza_korekta, 0
                    ),
                    "SamochodZastepczy": round(
                        stawka_result.koszt_samochod_zastepczy.koszt_plus_marza_korekta,
                        0,
                    ),
                    "Przychod": round(stawka_result.przychod, 0),
                    "PodstawaMarzy": stawka_result.podstawa_marzy,
                    "MarzaMiesiac": round(stawka_result.marza_mc, 0),
                    "MarzaNaKontrakcie": round(stawka_result.marza_na_kontrakcie, 0),
                    "MarzaNaKontrakcieProcent": stawka_result.marza_na_kontrakcie_procent,
                    "KosztyLaczneMC": stawka_result.koszty_laczne_mc,
                    "KosztFinansowyLacznie": round(
                        stawka_result.koszt_finansowy_lacznie, 0
                    ),
                    "KosztFinansowyMiesiecznie": round(
                        stawka_result.koszt_finansowy_miesiecznie, 0
                    ),
                    "Koszt": [
                        to_koszt_dict(stawka_result.koszt_finansowy),
                        to_koszt_dict(stawka_result.koszt_ubezpieczenie),
                        to_koszt_dict(stawka_result.koszt_samochod_zastepczy),
                        to_koszt_dict(stawka_result.koszt_serwis),
                        to_koszt_dict(stawka_result.koszt_opony),
                        to_koszt_dict(stawka_result.koszt_admin),
                    ],
                    # 2. Zakup (decimal - bez zaokrÄ…gleĹ„)
                    "CenaZakupu": capex_res.CenaZakupu,
                    "CenaZakupuBezOpon": capex_res.CenaZakupuBezOpon,
                    "CenaZakupuBezOponIOpcjiSerwisowych": capex_res.CenaZakupuBezOponIOpcjiSerwisowych,
                    "CenaZakupuBezOponIOpcjiSerwisowychIPakietu": capex_res.CenaZakupuBezOponIOpcjiSerwisowychIPakietu,
                    "CenaKatalogowaNetto": capex_res.CenaKatalogowaNetto,
                    "RabatKwotowo": capex_res.RabatKwotowo,
                    "GsmCapexNetto": capex_res.gsm_capex_net,
                    "OpcjeSerwisoweSumaNetto": capex_res.total_service_options,
                    # 3. Utrata WartoĹ›ci
                    "WR": vr_samar,
                    "WRdlaLO": round(rv_res.get("WRdlaLO", vr_samar), 0),
                    "UtrataWartosci": round(utrata_z_czynszem, 0),
                    "KorektaZaPrzebiegKwotowo": round(
                        rv_res.get("KorektaZaPrzebiegKwotowo", 0.0), 0
                    ),
                    "KorektaAdministracyjnaKwotowo": 0.0,
                    # 4. Finanse
                    "CzynszInicjalnyProcent": finance_res.CzynszInicjalnyProcent,
                    "CzynszInicjalnyNetto": round(finance_res.CzynszInicjalnyNetto, 0),
                    "LacznyKosztCzesciOdsetkowejRaty": round(
                        finance_res.SumaOdsetekZczynszem, 0
                    ),
                    "SumaOdsetekBezCzynszuInicjalnego": round(
                        finance_res.SumaOdsetekBEZczynszu, 0
                    ),
                    # 5. Opony
                    "LacznyKosztOpon": round(tires_total, 0),
                    "IloscOpon": round(tires_res["IloscOpon"], 0),
                    "Cena1KompletOpon": round(
                        tires_res.get("Cena1KompletOpon", 0.0), 0
                    ),
                    "Koszt1KplOpon": round(tires_res.get("Koszt1KplOpon", 0.0), 0),
                    # 6. Serwis
                    "LacznieKosztySerwisowe": round(service_total, 0),
                    "KosztySerwisowe": round(service_total, 0),
                    # 7. PozostaĹ‚e
                    "LacznieUbezpieczenie": round(insurance_total, 0),
                    "KosztyDodatkowe": round(additional_costs_total, 0),
                    "LacznieSamochodZastepczy": round(rc_total, 0),
                    "KosztyOgolem": round(kd_result.koszty_ogolem, 0),
                    "KosztDzienny": round(kd_result.koszt_dzienny, 2),
                    "AmortyzacjaProcent": procent_amortyzacji_miesiecznie,
                    "KorektaWRMaks": round(bm_result.korekta_wr_maks, 2),
                    # 8. Diagnostyka
                    "ReportHtml": report_html,
                    # 9. Ĺšlad rewizyjny (Calculation Trace)
                    "calculation_trace": (
                        [f"=== LTR MATRIX TILE TRACE. TRACE_ID: {self.trace_id} ==="]
                        + capex_res.trace
                        + rv_res.get("trace", [])
                        + (amort_result.trace if "amort_result" in locals() else [])
                        + tires_res.get("trace", [])
                        + service_from_new_dict.get("trace", [])
                        + insurance_res.get("trace", [])
                        + rc_res.get("trace", [])
                        + add_calc_res.get("trace", [])
                        + finance_res.trace
                        + kd_result.trace
                        + stawka_result.trace
                        + bm_result.trace
                    ),
                    # Extra technical output (status/warnings)
                    "status": "OK",
                    "warnings": {
                        "service_fallback_used": service_fallback_used,
                        "replacement_car_missing": rc_base == 0.0
                        and self.input_data.replacement_car_enabled,
                    },
                }
            )
            cells[-1]["ReportHtml"] = build_report_html(cells[-1])

        return cells

    def build_reverse_search_matrix(self) -> List[Dict[str, Any]]:
        """Przelicza siatke kwot na potrzebe zapytan masowych w tle (Reverse Search).
        Tylko minimalne wymagane klucze dla zadania matrix_cache_job.py, by odciazyc zbedne koszty obliczeniowe (brak PDF HTML).
        Rozdzielczosc kroku umozliwia 212 unikatowych wyliczen: od 40k do 300 000 km co 5k.
        """
        cells = []

        vehicle_capex, options_capex, capex_res = self._calculate_capex()
        capex = vehicle_capex + options_capex

        base_price_net_full = float(getattr(self.vehicle, "price_net", 0.0))
        if base_price_net_full == 0.0:
            base_price_net_full = float(getattr(self.input_data, "base_price_net", 0.0))

        # Opcje pod Wartość Rezydualną — analogicznie do build_matrix.
        wr_disc_opts, wr_non_disc_opts, wr_service_in_wr = self._calculate_wr_options_split()
        base_wr_options = wr_disc_opts + wr_non_disc_opts + wr_service_in_wr

        margin_pct = 0.0001  # Fix for division by zero - Reverse Search operates solely on base net cost 0 margin

        grid_params: List[tuple[int, int]] = []
        contract_km_by_pair: Dict[tuple[int, int], int] = {}

        # 4 periods, from 40k to 300k step 5k => ensures <=300k is explicitly calculated
        for months in (24, 36, 48, 60):
            for total_km in range(40000, 300001, 5000):
                km_per_year = int(round((total_km / months) * 12))
                pair = (months, km_per_year)
                grid_params.append(pair)
                contract_km_by_pair[pair] = total_km

        for months, km_per_year in grid_params:
            total_km = contract_km_by_pair[(months, km_per_year)]

            # 1. Koszty Opon
            tires_res = self.tires_calc.calculate_cost(months=months, total_km=total_km)
            capex_for_financing = capex + tires_res["capex_initial_set"]

            # FIX: Rabat aplikujemy TYLKO do opcji rabatowalnych — analogicznie do build_matrix.
            discount_pct = getattr(self.input_data, "discount_pct", 0) / 100.0
            discounted_factory_options = wr_disc_opts * (1 - discount_pct)
            wp_amortyzacja = (
                vehicle_capex
                + discounted_factory_options
                + wr_non_disc_opts
                + wr_service_in_wr
            )

            vat_rate = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate > 10.0:
                vat_rate = 1.0 + (vat_rate / 100.0)

            rv_calc_v3 = LTRSubCalculatorUtrataWartosciNew(
                self.vehicle, self.input_data
            )
            rv_res = rv_calc_v3.calculate_values(
                months=months,
                total_km=total_km,
                base_vehicle_catalog_gross=base_price_net_full * vat_rate,
                options_catalog_gross=base_wr_options * vat_rate,
            )
            vr_samar = rv_res["WR"]

            # PMT
            vat_rate_fin = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate_fin > 10.0:
                vat_rate_fin = 1.0 + (vat_rate_fin / 100.0)

            _initial_deposit_pct = float(
                getattr(self.input_data, "initial_deposit_pct", 0.0) or 0.0
            )
            finance_input = FinanseInput(
                WartoscPoczatkowaNetto=capex_for_financing,
                WrPrzewidywanaCenaSprzedazy=vr_samar,
                CzynszInicjalny=0.0,
                CzynszProcent=_initial_deposit_pct,
                RodzajCzynszu="Procentowo" if _initial_deposit_pct > 0 else "Kwotowo",
                StawkaVAT=vat_rate_fin,
                Okres=months,
                WIBORProcent=float(
                    self.input_data.wibor_pct
                    if getattr(self.input_data, "wibor_pct", None) is not None
                    else getattr(self.settings, "default_wibor", 5.0)
                ),
                MarzaFinansowaProcent=float(
                    self.input_data.margin_pct
                    if getattr(self.input_data, "margin_pct", None) is not None
                    else getattr(self.settings, "default_ltr_margin", 2.0)
                ),
            )
            finance_calc = FinanseCalculator(finance_input)
            finance_res = finance_calc.calculate()

            tires_base = float(
                tires_res["monthly_hardware"]
                + tires_res["monthly_storage"]
                + tires_res["monthly_swaps"]
            )

            normatywny_przebieg = int(
                getattr(self.settings, "normatywny_przebieg_mc", 0) or 0
            )
            if normatywny_przebieg <= 0:
                raise ValueError(
                    "Brak poprawnej wartosci `normatywny_przebieg_mc` w Control Center."
                )
            if not self.samar_id:
                raise ValueError(
                    "Brak `samar_class_id` dla pojazdu. Uzupelnij klase SAMAR w danych wejsciowych."
                )

            engine_type_id = int(getattr(self.vehicle, "engine_type_id", 0) or 0)
            if engine_type_id <= 0:
                engine_name_input = getattr(self.input_data, "engine_name", None)
                if engine_name_input:
                    try:
                        engine_type_id = _resolve_engine_type_id(engine_name_input)
                    except Exception:
                        pass
            if engine_type_id <= 0:
                raise ValueError(
                    "Brak `engine_type_id` dla pojazdu. Uzupelnij typ silnika w danych wejsciowych."
                )

            power_kw_input = getattr(self.input_data, "power_kw", None)
            if power_kw_input and float(power_kw_input) > 0:
                power_kw = float(power_kw_input)
            else:
                power_kw_val = getattr(self.vehicle, "power_kw", 0.0)
                power_kw = float(power_kw_val if power_kw_val is not None else 0.0)
            if power_kw <= 0.0:
                raise ValueError(
                    f"Brak poprawnej mocy `power_kw` pojazdu. power_kw_input={power_kw_input}, self.vehicle_power_kw={getattr(self.vehicle, 'power_kw', None)}"
                )

            pakiet_serwisowy_val = float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            )
            inne_koszty_val = float(
                getattr(self.input_data, "inne_koszty_serwisowania_netto", 0.0)
            )

            service_input = ServiceCalculatorInput(
                z_serwisem=self.include_servicing,
                opcja_serwisowa=self._opcja_serwisowa,
                normatywny_przebieg_mc=normatywny_przebieg,
                samar_class_id=int(self.samar_id),
                brand_normalized=str(getattr(self.vehicle, "brand", "")),
                fuel_type=str(
                    getattr(
                        self.vehicle,
                        "engine_category",
                        getattr(self.input_data, "engine_name", ""),
                    )
                ),
                drive_type=str(getattr(self.vehicle, "drive_type", "")),
                gearbox_type=str(
                    getattr(
                        self.vehicle,
                        "gearbox",
                        getattr(self.input_data, "gearbox_name", ""),
                    )
                ),
                przebieg=total_km,
                okres=months,
                pakiet_serwisowy=pakiet_serwisowy_val,
                inne_koszty_serwisowania_netto=inne_koszty_val,
            )
            service_calc = ServiceCalculator(service_input)
            service_from_new_dict = service_calc.calculate()
            service_from_new = float(service_from_new_dict["monthly_service"])

            service_base = service_from_new
            if self.include_servicing and service_from_new <= 0:
                raise ValueError(
                    f"Brak stawek serwisowych (ServiceCalculator zwrocil 0) dla "
                    f"okres={months}, klasa={getattr(self.vehicle, 'samar_class_id', '?')}, "
                    f"silnik={getattr(self.vehicle, 'engine_type_id', '?')}."
                )

            if getattr(self.input_data, "depreciation_pct", None) is not None:
                procent_amortyzacji_miesiecznie = float(
                    self.input_data.depreciation_pct
                )
            else:
                amort_input = AmortyzacjaInput(
                    wp_finansowanie=capex_for_financing,
                    wp_amortyzacja=wp_amortyzacja,
                    wr=vr_samar,
                    okres=months,
                )
                amort_result = AmortyzacjaCalculator(amort_input).calculate()
                procent_amortyzacji_miesiecznie = amort_result.amortyzacja_procent

            s_class_id = str(self.samar_id)
            insurance_rates = get_insurance_rates_from_db(s_class_id)
            damage_coeffs = get_damage_coefficients_from_db(s_class_id)
            ins_calc = InsuranceCalculator(
                insurance_rates=insurance_rates,  # type: ignore
                damage_coefficients=damage_coeffs,  # type: ignore
                settings=self.settings,  # type: ignore
                amortization_pct=procent_amortyzacji_miesiecznie,  # type: ignore
                total_km=total_km,  # type: ignore
            )
            insurance_res = ins_calc.calculate_cost(months, capex_for_financing, enabled=self.express_pays_insurance)  # type: ignore
            insurance_base = float(insurance_res["monthly_insurance"])
            insurance_total = float(
                insurance_res.get("total_insurance", insurance_base * months)
            )

            rc_rate = get_replacement_car_rate_from_db(s_class_id)
            rc_calc = ReplacementCarCalculator(rc_rate)  # type: ignore
            rc_res = rc_calc.calculate_cost(
                months=months, enabled=self.input_data.replacement_car_enabled
            )
            rc_base = float(rc_res["monthly_replacement_car"])
            rc_total = float(rc_res.get("total_replacement_car", rc_base * months))

            add_calc = AdditionalCostsCalculator(self.settings, self.input_data, months)
            add_calc_res = add_calc.calculate_cost()
            additional_costs_base = float(add_calc_res["monthly_additional_costs"])
            additional_costs_total = additional_costs_base * months

            tires_total = tires_base * months
            service_total = service_base * months
            utrata_z_czynszem = float(
                rv_res.get(
                    "UtrataWartosciZCzynszemInicjalnym", capex_for_financing - vr_samar
                )
            )
            utrata_bez_czynszu = float(rv_res["UtrataWartosciBEZczynszu"])

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

            cells.append(
                {
                    "Okres": months,
                    "Przebieg": km_per_year,
                    "PrzebiegKontrakt": total_km,
                    "LacznaStawka": round(stawka_result.oferowana_stawka, 0),
                }
            )

        return cells
