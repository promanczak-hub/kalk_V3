"""LTR Matrix orchestrator — buduje siatkę wariantów dla CalculatorInput.

Refactor 2026-05-19:
- Per-cell calc (był duplikowany ~500 LOC w `build_matrix` ↔ `build_reverse`)
  wyniesiony do `core/ltr_cell_calculator.py` (`calculate_cell`).
- VAT / engine_power / transport_fee / grid builders — tamże.
- Tutaj zostaje **tylko orchestrator**: setup (vehicle, overrides, service),
  capex, WR options split, thin public API. Wersja: 1159 → ~350 LOC.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from core.LTRSubCalculatorCenaZakupu import (
    PurchasePriceCalculator,
    PurchasePriceInput,
    PurchasePriceOption,
)
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony
from core.ltr_cell_calculator import (
    CellContext,
    build_grid_full,
    build_grid_reverse,
    calculate_cell,
    fetch_transport_fee_net,
)
from core.finance_input_resolver import _require_setting  # noqa: F401 (export for future use)
from core.ltr_db_fetchers import get_vehicle_from_db
from core.ltr_vehicle_resolvers import (
    _resolve_body_type_id_from_name,
    _resolve_engine_type_id,
    _resolve_paint_type_id_from_name,
    _resolve_samar_class_id_from_name,
    _resolve_zabudowa_type_id_from_name,
)

logger = logging.getLogger(__name__)


class LTRKalkulator:
    """Rdzeń budujący Matrix dla zadanego CalculatorInput."""

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

        self.tires_calc = LTRSubCalculatorOpony(
            z_oponami=getattr(self.input_data, "z_oponami", True),
            klasa_opony_string=getattr(self.input_data, "klasa_opony_string", ""),
            srednica_felgi=getattr(self.input_data, "srednica_felgi", 0) or 0,
            sets_needed_override=getattr(self.input_data, "liczba_kompletow_opon", None),
            odkup_opon_enabled=getattr(self.input_data, "odkup_opon_enabled", False),
        )

        self._load_vehicle_and_samar()
        self._apply_explicit_input_overrides()

        self.include_servicing = bool(getattr(self.input_data, "include_servicing", True))
        self.express_pays_insurance = bool(
            getattr(self.input_data, "express_pays_insurance", True)
        )
        self.service_cost_type = str(
            getattr(self.input_data, "service_cost_type", "ASO") or "ASO"
        ).strip()
        normalised = self.service_cost_type.upper().replace("-", "").replace("_", "")
        if normalised in {"NONASO", "NIEASO"}:
            self._opcja_serwisowa = "NON-ASO"
        elif normalised == "ASO":
            self._opcja_serwisowa = "ASO"
        else:
            raise ValueError(
                f"Nieobslugiwany service_cost_type: '{self.service_cost_type}'. "
                "Dozwolone: ASO / NON-ASO."
            )

    # ── Setup helpers ───────────────────────────────────────────────────

    def _load_vehicle_and_samar(self) -> None:
        from core.models import VehicleDataDTO

        if self.pipeline_dto:
            self.vehicle = self.pipeline_dto.vehicle
            self.samar_id = self.vehicle.samar_class_id
            self.samar_klasa = self.pipeline_dto.samar_class.model_dump()
            return

        vid = getattr(self.input_data, "vehicle_id", "")
        if isinstance(self.input_data, dict):
            vid = self.input_data.get("vehicle_id", "")
        raw_v = get_vehicle_from_db(vid) if vid else {}

        self.samar_id = raw_v.get("samar_class_id", 0)
        if raw_v:
            raw_v["samar_class_id"] = self.samar_id
            extras = {
                k: v for k, v in raw_v.items()
                if k not in {"id", "brand", "model", "engine_type_id", "samar_class_id"}
            }
            self.vehicle = VehicleDataDTO(
                id=str(raw_v.get("id", "0")),
                brand=str(raw_v.get("brand", "UNKNOWN")),
                model=str(raw_v.get("model", "UNKNOWN")),
                engine_type_id=int(raw_v.get("engine_type_id", 0)),
                samar_class_id=int(self.samar_id),
                **extras,
            )
        else:
            self.vehicle = VehicleDataDTO(
                id="0", brand="UNKNOWN", model="UNKNOWN",
                engine_type_id=0, samar_class_id=0,
            )
        self.samar_klasa = {}

    def _apply_explicit_input_overrides(self) -> None:
        if not self.vehicle:
            from core.models import VehicleDataDTO
            self.vehicle = VehicleDataDTO(
                id="0", brand="UNKNOWN", model="UNKNOWN",
                engine_type_id=0, samar_class_id=0,
            )

        input_samar = str(getattr(self.input_data, "samar_category", "") or "").strip()
        if input_samar:
            resolved_samar_id = _resolve_samar_class_id_from_name(input_samar)
            if resolved_samar_id <= 0:
                logger.warning("Ignored SAMAR class from dropdown: '%s'", input_samar)
            else:
                self.vehicle.Segment = input_samar
                self.vehicle.samar_class_id = int(resolved_samar_id)
                self.samar_id = int(resolved_samar_id)

        if getattr(self.input_data, "power_kw", None):
            self.vehicle.power_kw = float(self.input_data.power_kw)
        elif getattr(self.input_data, "power_hp", None):
            self.vehicle.power_kw = float(round(self.input_data.power_hp / 1.36))

        input_engine = str(getattr(self.input_data, "engine_name", "") or "").strip()
        if input_engine:
            try:
                self.vehicle.engine_type_id = int(_resolve_engine_type_id(input_engine))
            except ValueError as exc:
                logger.warning("Ignored engine category '%s': %s", input_engine, exc)

        input_body = str(getattr(self.input_data, "body_type_name", "") or "").strip()
        if input_body:
            resolved_body_id = _resolve_body_type_id_from_name(input_body)
            if resolved_body_id:
                self.vehicle.body_type_id = int(resolved_body_id)
            else:
                logger.warning("Body type not resolved from dropdown: '%s'", input_body)
            self.vehicle.body_type_name = input_body
            if not getattr(self.vehicle, "zabudowa_type_id", None):
                inferred = _resolve_zabudowa_type_id_from_name(input_body)
                if inferred:
                    self.vehicle.zabudowa_type_id = int(inferred)

        input_paint_id = getattr(self.input_data, "paint_type_id", None)
        if input_paint_id is not None:
            try:
                pid = int(input_paint_id)
                if pid > 0:
                    self.vehicle.paint_type_id = pid
            except (TypeError, ValueError):
                pass
        else:
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
                inferred = _resolve_zabudowa_type_id_from_name(str(getattr(opt, "name", "") or ""))
                if inferred:
                    self.vehicle.zabudowa_type_id = int(inferred)
                    break

        self.vehicle.zabudowa_apr_wr = bool(
            getattr(self.vehicle, "zabudowa_apr_wr", False)
            or getattr(self.vehicle, "zabudowa_type_id", None)
        )

        if hasattr(self.input_data, "vehicle_vintage"):
            self.vehicle.rocznik = getattr(self.input_data, "vehicle_vintage")
        if hasattr(self.input_data, "is_metalic"):
            self.vehicle.is_metalic = bool(getattr(self.input_data, "is_metalic"))

    # ── Capex / WR pre-computations ────────────────────────────────────

    def _calculate_wr_options_split(self) -> Tuple[float, float, float]:
        """(discountable_wr_options, non_discountable_wr_options, service_options_in_wr)."""
        discountable = sum(
            opt.price_net for opt in self.input_data.factory_options
            if not getattr(opt, "no_discount", False)
        )
        non_discountable = sum(
            opt.price_net for opt in self.input_data.factory_options
            if getattr(opt, "no_discount", False)
        )
        service_in_wr = sum(
            opt.price_net for opt in self.input_data.service_options
            if getattr(opt, "include_in_wr", False)
        )
        return discountable, non_discountable, service_in_wr

    def _calculate_capex(self) -> Tuple[float, float, Any]:
        """Kalkuluje wejściową sumę finansowaną (CAPEX)."""
        base_net = self.input_data.base_price_net

        options: List[PurchasePriceOption] = []
        for opt in self.input_data.factory_options:
            options.append(PurchasePriceOption(
                price_net=opt.price_net, name=opt.name,
                is_service=False, is_discountable=not opt.no_discount,
            ))
        for opt in self.input_data.service_options:
            options.append(PurchasePriceOption(
                price_net=opt.price_net, name=opt.name,
                is_service=True, is_discountable=not opt.no_discount,
            ))

        tires_capex = self.tires_calc.tire_set_price if self.tires_calc.z_oponami else 0.0
        brand = getattr(self.vehicle, "brand", "").strip()
        transport_fee_net = float(getattr(self.input_data, "transport_fee_net", 0.0))
        if brand and transport_fee_net == 0.0:
            transport_fee_net = fetch_transport_fee_net(brand)

        pp_input = PurchasePriceInput(
            base_price_net=base_net,
            options=options,
            discount_pct=self.input_data.discount_pct,
            tires_capex_net=tires_capex,
            add_gsm_to_capex=True,
            gsm_device_cost_net=float(_require_setting(self.settings, "cost_gsm_device", "GPS/GSM device cost")),
            gsm_installation_cost_net=float(_require_setting(self.settings, "cost_gsm_installation", "GPS/GSM instalacja")),
            pakiet_serwisowy_net=float(getattr(self.input_data, "pakiet_serwisowy", 0.0)),
            transport_fee_net=transport_fee_net,
        )
        res = PurchasePriceCalculator(pp_input).calculate()

        discounted_options_capex = (
            res.total_capex
            - res.discounted_base
            - res.tires_capex_net
            - res.gsm_capex_net
            - res.transport_fee_net
        )
        return res.discounted_base, discounted_options_capex, res

    def _build_cell_context(self, *, margin_override: float | None = None) -> CellContext:
        vehicle_capex, options_capex, capex_res = self._calculate_capex()
        base_price_net_full = float(getattr(self.vehicle, "price_net", 0.0)) or float(
            getattr(self.input_data, "base_price_net", 0.0)
        )
        wr_disc, wr_non_disc, wr_service = self._calculate_wr_options_split()

        if margin_override is not None:
            margin_pct = margin_override
        else:
            calc_mode = getattr(self.input_data, "calculation_mode", "standard")
            if calc_mode == "base_cost_only":
                margin_pct = 0.0001
            else:
                margin_pct = self.input_data.pricing_margin_pct / 100.0
            if margin_pct >= 1.0:
                margin_pct = 0.9999  # avoid division by zero in stawka calc

        return CellContext(
            vehicle_capex=vehicle_capex,
            options_capex=options_capex,
            capex_res=capex_res,
            base_price_net_full=base_price_net_full,
            wr_disc_opts=wr_disc,
            wr_non_disc_opts=wr_non_disc,
            wr_service_in_wr=wr_service,
            base_wr_options=wr_disc + wr_non_disc + wr_service,
            margin_pct=margin_pct,
        )

    # ── Public API ─────────────────────────────────────────────────────

    def build_matrix(self, only_exact: bool = False) -> List[Dict[str, Any]]:
        """Przelicza wszystkie warianty i zwraca siatkę (List of Cells)."""
        ctx = self._build_cell_context()

        correction_map: Dict[str, float] = (
            getattr(self.input_data, "koszt_opon_korekta", {}) or {}
        )
        correction_active = bool(getattr(self.input_data, "korekta_kosztu_opon", False))

        if only_exact:
            req_months = int(getattr(self.input_data, "okres_bazowy", 48) or 48) or 48
            req_total_km = int(
                getattr(self.input_data, "przebieg_bazowy", 140000) or 140000
            )
            req_km_per_year = int(round((req_total_km / req_months) * 12))
            grid = [(req_months, req_km_per_year)]
            contract_km_by_pair = {(req_months, req_km_per_year): req_total_km}
        else:
            grid, contract_km_by_pair = build_grid_full(self.input_data)

        cells: List[Dict[str, Any]] = []
        for months, km_per_year in grid:
            total_km = contract_km_by_pair.get(
                (months, km_per_year), int((km_per_year / 12) * months)
            )
            correction = (
                correction_map.get(f"{months}_{total_km}", 0.0)
                if correction_active else 0.0
            )
            cells.append(calculate_cell(
                kalk=self,
                months=months,
                km_per_year=km_per_year,
                total_km=total_km,
                ctx=ctx,
                include_full_output=True,
                correction_for_cell=correction,
            ))
        return cells

    def build_reverse_search_matrix(self) -> List[Dict[str, Any]]:
        """Reverse-search matrix — 212 cells, zero-margin, only LacznaStawka."""
        ctx = self._build_cell_context(margin_override=0.0001)
        grid, contract_km_by_pair = build_grid_reverse()
        cells: List[Dict[str, Any]] = []
        for months, km_per_year in grid:
            total_km = contract_km_by_pair[(months, km_per_year)]
            cells.append(calculate_cell(
                kalk=self,
                months=months,
                km_per_year=km_per_year,
                total_km=total_km,
                ctx=ctx,
                include_full_output=False,
            ))
        return cells
