"""
Wrapper: LTRSubCalculatorUtrataWartosciNew (V3).

Adapter pomiędzy LTRKalkulator a nowym SamarRVCalculator.
Zachowuje interfejs `calculate_values()` zwracający dict z kluczami:
  WR, WR_Gross, WRdlaLO, UtrataWartosciBEZczynszu
wymagany przez LTRKalkulator.build_matrix().
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.samar_rv import RVInput, RVOutput, SamarRVCalculator, get_samar_class_id

logger = logging.getLogger(__name__)


class LTRSubCalculatorUtrataWartosciNew:
    """Kalkulator Utraty Wartości SAMAR (V3) — wrapper.

    Deleguje obliczenie RV do ``SamarRVCalculator`` (algorytm Excel JŁ),
    a następnie konwertuje wynik na format wymagany przez LTRKalkulator.
    """

    def __init__(self, vehicle_data: Dict[str, Any], calc_input: Any) -> None:
        self.vehicle = vehicle_data
        self.input = calc_input

        # Resolve SAMAR class + engine_id
        class_name = self.vehicle.get("Segment", "") or ""
        self.samar_class_id = get_samar_class_id(class_name) or int(
            self.vehicle.get("klasa_wr_id", 0) or 0
        )
        self.engine_id = int(self.vehicle.get("engine_type_id", 1) or 1)

        # Brand
        self.brand_name = (
            (self.vehicle.get("brand") or self.vehicle.get("Marka") or "")
            .strip()
            .upper()
        )

        # Paint type ID
        self.paint_type_id: Optional[int] = None
        raw_paint = self.vehicle.get("paint_type_id")
        if raw_paint:
            self.paint_type_id = int(raw_paint)

        # Body type ID
        self.body_type_id: Optional[int] = None
        raw_body = self.vehicle.get("body_type_id")
        if raw_body:
            self.body_type_id = int(raw_body)

        # Zabudowa flag
        self.zabudowa_apr_wr = bool(self.vehicle.get("zabudowa_apr_wr", False))

        # Rocznik — priority: calc_input.vehicle_vintage → vehicle dict
        vintage_raw = getattr(self.input, "vehicle_vintage", None)
        if not vintage_raw and isinstance(self.input, dict):
            vintage_raw = self.input.get("vehicle_vintage")
        if not vintage_raw:
            vintage_raw = self.vehicle.get("rocznik", "current")
        self.rocznik = str(vintage_raw or "current")

        # Is metalic — priority: calc_input.is_metalic → vehicle dict
        is_meta = getattr(self.input, "is_metalic", None)
        if is_meta is None and isinstance(self.input, dict):
            is_meta = self.input.get("is_metalic")
        if is_meta is None:
            is_meta = bool(self.vehicle.get("is_metalic", True))
        self.is_metalic = bool(is_meta)

        # VAT
        self.vat_rate = self._resolve_vat()

    def _resolve_vat(self) -> float:
        """Pobiera stawkę VAT z ustawień lub domyślną."""
        vat = 1.23
        if hasattr(self.input, "settings"):
            settings = self.input.settings
            raw_vat = getattr(settings, "vat_rate", None)
            if raw_vat:
                vat = float(raw_vat)
                if vat > 10.0:
                    vat = 1.0 + (vat / 100.0)
                elif vat < 1.0:
                    vat = 1.23
        return vat

    # ── Public API (backward-compatible) ──────────────────────────

    def calculate_values(
        self,
        months: int,
        total_km: int,
        base_vehicle_capex_gross: float,
        options_capex_gross: float,
    ) -> Dict[str, Any]:
        """Zwraca słownik z WR, WRdlaLO, UtrataWartosciBEZczynszu.

        LTRKalkulator przekazuje ceny BRUTTO. Konwertujemy na netto
        dla SamarRVCalculator, a wynik zwracamy w netto.
        """
        # Konwersja brutto → netto
        base_net = base_vehicle_capex_gross / self.vat_rate
        options_net = options_capex_gross / self.vat_rate

        # Manual WR correction
        manual_wr = 0.0
        if hasattr(self.input, "manual_wr_correction"):
            manual_wr = float(getattr(self.input, "manual_wr_correction", 0.0))
        elif isinstance(self.input, dict):
            manual_wr = float(self.input.get("manual_wr_correction", 0.0))

        rv_input = RVInput(
            samar_class_id=self.samar_class_id,
            engine_id=self.engine_id,
            brand_name=self.brand_name,
            months=months,
            total_km=total_km,
            capex_base_net=base_net,
            capex_options_net=options_net,
            paint_type_id=self.paint_type_id,
            is_metalic=self.is_metalic,
            body_type_id=self.body_type_id,
            rocznik=self.rocznik,
            zabudowa_apr_wr=self.zabudowa_apr_wr,
            manual_wr_correction=manual_wr,
        )

        rv_calc = SamarRVCalculator(rv_input)
        result: RVOutput = rv_calc.calculate()

        return {
            "WR_Gross": result.wr_net * self.vat_rate,
            "WR": result.wr_net,
            "WRdlaLO": result.wr_lo_net,
            "UtrataWartosciBEZczynszu": result.utrata_wartosci_net,
            "WR_percent": result.wr_percent,
            "debug": result.debug,
        }
