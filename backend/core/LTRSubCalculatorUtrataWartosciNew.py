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
        if hasattr(self.vehicle, "model_dump"):
            self.vehicle = self.vehicle.model_dump()
        elif hasattr(self.vehicle, "__dict__"):
            self.vehicle = vars(self.vehicle)
        self.input = calc_input

        # Resolve SAMAR class + engine_id
        class_name = self.vehicle.get("Segment", "") or ""
        self.samar_class_id = get_samar_class_id(class_name) or int(
            self.vehicle.get("samar_class_id", 0) or 0
        )
        self.engine_id = int(self.vehicle.get("engine_type_id", 0) or 0)

        if self.samar_class_id <= 0:
            raise ValueError("Brak `samar_class_id` w danych pojazdu dla kalkulacji WR.")
        if self.engine_id <= 0:
            raise ValueError("Brak `engine_type_id` w danych pojazdu dla kalkulacji WR.")

        # Brand
        self.brand_name = (
            (self.vehicle.get("brand") or self.vehicle.get("Marka") or "")
            .strip()
            .upper()
        )

        # Model
        self.model_name = (
            (self.vehicle.get("model") or self.vehicle.get("Model") or "")
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

        # Zabudowa flag + type
        self.zabudowa_apr_wr = bool(self.vehicle.get("zabudowa_apr_wr", False))
        self.zabudowa_type_id: Optional[int] = None
        raw_zab = self.vehicle.get("zabudowa_type_id")
        if raw_zab:
            self.zabudowa_type_id = int(raw_zab)

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
            model_name=self.model_name,
            months=months,
            total_km=total_km,
            capex_base_net=base_net,
            capex_options_net=options_net,
            paint_type_id=self.paint_type_id,
            is_metalic=self.is_metalic,
            body_type_id=self.body_type_id,
            rocznik=self.rocznik,
            zabudowa_apr_wr=self.zabudowa_apr_wr,
            zabudowa_type_id=self.zabudowa_type_id,
            manual_wr_correction=manual_wr,
        )

        rv_calc = SamarRVCalculator(rv_input)
        result: RVOutput = rv_calc.calculate()

        # Konwersja debug logów na wystandaryzowany ślad kalkulacyjny (trace)
        d = result.debug
        trace: list[dict[str, Any]] = []

        trace.append({
            "krok": "WR Krok 1: Wartość Bazowa (klasa + marka)",
            "rownanie": f"CAPEX_NETTO * (WR_KLASA {d.get('krok1_wr_base_pct', 0)*100:.2f}% + KOR_MARKA {d.get('krok1_brand_correction', 0)*100:.2f}%)",
            "wynik": d.get('krok1_wr_value_netto', 0.0)
        })

        value_table = d.get('krok2_value_table_netto', {})
        trace.append({
            "krok": "WR Krok 2: Deprecjacja kaskadowa (Tabela)",
            "rownanie": f"Generowanie krzywej utraty wartości: {value_table}",
            "wynik": value_table.get(d.get("krok3_years", 0), 0.0) if value_table else 0.0
        })

        trace.append({
            "krok": "WR Krok 3: Wartość per lat + Opcje (V1 ułamek opcji)",
            "rownanie": f"Baza ({d.get('krok3_years', 0)} lat) {d.get('krok3_rv_base_netto', 0):.2f} + Opcje {d.get('krok3_rv_options_netto', 0):.2f} / (1 + lata)",
            "wynik": d.get('krok3_rv_total_netto', 0.0)
        })

        trace.append({
            "krok": "WR Krok 4: Korekta Przebiegu",
            "rownanie": f"Paczki 10k: Under {d.get('krok4_paczki_under', 0)} ({d.get('krok4_under_rate', 0)*100:.2f}%), Over: {d.get('krok4_paczki_over', 0)} ({d.get('krok4_over_rate', 0)*100:.2f}%)",
            "wynik": -d.get("krok4_korekta_przebieg_netto", 0.0)
        })

        trace.append({
            "krok": "WR Krok 5: Korekty Dodatkowe (Kolor, Nadwozie)",
            "rownanie": f"Kolor {d.get('krok5_color_netto', 0):.2f} + Nadwozie {d.get('krok5_body_netto', 0):.2f}",
            "wynik": d.get("krok5_color_netto", 0.0) + d.get("krok5_body_netto", 0.0)
        })

        trace.append({
            "krok": "WR Krok 6: Korekta Ręczna i Rocznik (Final_RV)",
            "rownanie": f"Mnożnik Rocznika: (1+ {d.get('krok6_vintage_pct', 0)*100:.2f}%), Korekta Ręczna {d.get('krok6_manual_correction_netto', 0):.2f}",
            "wynik": d.get("krok6_final_rv_netto", 0.0)
        })
        
        trace.append({
            "krok": "WR: Utrata Wartości Netto",
            "rownanie": f"MAX((CAPEX {base_net + options_net:.2f} - WR {d.get('krok6_final_rv_netto', 0):.2f}), 0)",
            "wynik": d.get("krok6_utrata", 0.0)
        })

        return {
            "WR_Gross": result.wr_net * self.vat_rate,
            "WR": result.wr_net,
            "WRdlaLO": result.wr_lo_net,
            "UtrataWartosciBEZczynszu": result.utrata_wartosci_net,
            "WR_percent": result.wr_percent,
            "debug": result.debug,
            "trace": trace,
        }
