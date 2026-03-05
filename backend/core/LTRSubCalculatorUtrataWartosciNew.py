from typing import Dict, Any, cast

from core.database import supabase
from core.samar_rv import SamarRVCalculator


class LTRSubCalculatorUtrataWartosciNew:
    """Kalkulator Utraty Wartości SAMAR (V3).

    Deleguje obliczenie RV do ``SamarRVCalculator`` (tabele V2),
    a następnie dodaje wrapper: WRdlaLO, UtrataWartosciBEZczynszu,
    konwersję brutto→netto i korektę ręczną.
    """

    def __init__(self, vehicle_data: Dict[str, Any], calc_input: Any) -> None:
        self.vehicle = vehicle_data
        self.input = calc_input

        # Delegat – właściwy silnik RV
        self.rv_engine = SamarRVCalculator(vehicle_data, calc_input)

        # Parametry globalne z bazy
        self.vat_rate = self._fetch_global_param("VAT", fallback=1.23)
        self.przewidywana_cena_lo = self._fetch_global_param(
            "PrzewidywanaCenaSprzedazyLO", fallback=0.0
        )

        # Normalizacja VAT rate
        if self.vat_rate > 2.0:
            self.vat_rate = 1.0 + (self.vat_rate / 100.0)
        elif self.vat_rate < 1.0:
            self.vat_rate = 1.23

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_global_param(self, param_name: str, fallback: float) -> float:
        """Pobiera parametry globalne z tabeli ``LTRAdminParametry_czak``."""
        try:
            response = (
                supabase.table("LTRAdminParametry_czak")
                .select("col_2")
                .ilike("col_1", param_name)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                row = cast(Dict[str, Any], response.data[0])
                val = row.get("col_2")
                if val is not None:
                    return float(str(val).replace(",", "."))
        except Exception:
            pass
        return fallback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_values(
        self,
        months: int,
        total_km: int,
        base_vehicle_capex_gross: float,
        options_capex_gross: float,
    ) -> Dict[str, float]:
        """Zwraca słownik z WR, WRdlaLO oraz UtrataWartosciBEZczynszu (netto)."""

        # 1. WR Brutto z SamarRVCalculator (operuje na brutto)
        wr_brutto = self.rv_engine.calculate_rv(
            months=months,
            total_km=total_km,
            base_vehicle_capex=base_vehicle_capex_gross,
            options_capex=options_capex_gross,
        )

        # 2. Korekta ręczna WR
        korekta_reczna_wr = 0.0
        if hasattr(self.input, "manual_wr_correction"):
            korekta_reczna_wr = float(getattr(self.input, "manual_wr_correction", 0.0))
        elif isinstance(self.input, dict) and "manual_wr_correction" in self.input:
            korekta_reczna_wr = float(self.input.get("manual_wr_correction", 0.0))

        wr_brutto += korekta_reczna_wr * self.vat_rate

        # 3. Clamp WR do 5–95% ceny zakupu
        laczna_cena_zakupu_brutto = base_vehicle_capex_gross + options_capex_gross
        min_rv = laczna_cena_zakupu_brutto * 0.05
        max_rv = laczna_cena_zakupu_brutto * 0.95
        wr_brutto = max(min_rv, min(max_rv, wr_brutto))

        # 4. Konwersje na netto
        wr_net = wr_brutto / self.vat_rate

        # 5. WRdlaLO
        wr_lo_brutto = wr_brutto * (1.0 + self.przewidywana_cena_lo)
        wr_lo_net = wr_lo_brutto / self.vat_rate

        # 6. UtrataWartosciBEZczynszu
        utrata_brutto = max(laczna_cena_zakupu_brutto - wr_brutto, 0.0)
        utrata_net = utrata_brutto / self.vat_rate

        return {
            "WR_Gross": float(wr_brutto),
            "WR": float(wr_net),
            "WRdlaLO": float(wr_lo_net),
            "UtrataWartosciBEZczynszu": float(utrata_net),
        }
