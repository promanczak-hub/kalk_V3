from typing import List, Dict, Any
from pydantic import BaseModel


class V3OptionItem(BaseModel):
    name: str
    price_net: float
    is_service: bool = False  # False = Fabryczne, True = Serwisowe


class CalculatorInputV3(BaseModel):
    vehicle_id: str
    base_price_net: float
    discount_pct: float
    selected_options: List[V3OptionItem]
    wibor_pct: float
    margin_pct: float
    upfront_pct: float

    # Vehicle Metadata for RV lookup
    brand: str = ""
    model: str = ""
    version: str = ""
    engine: str = ""
    fuel: str = ""
    transmission: str = ""
    body_type: str = ""

    # V3 TCO Flags
    all_season_tires: bool
    replacement_car: bool


class CalculationEngineV3:
    """
    Nowy, zoptymalizowany silnik V3 pod strukturę AI (Digital Twin).
    Generuje surową Matrix 4x6 i zwraca wartości gotowe dla Frontend.
    """

    def __init__(self, input_data: CalculatorInputV3):
        self.input = input_data

        # 1. Podział i agregacja CAPEX
        self.options_capex = sum(
            opt.price_net for opt in self.input.selected_options if not opt.is_service
        )
        self.service_capex = sum(
            opt.price_net for opt in self.input.selected_options if opt.is_service
        )

        self.base_price_after_discount = self.input.base_price_net * (
            1 - (self.input.discount_pct / 100.0)
        )

        # Pojazd gotowy do finansowania (Cena Bazy po Rabacie + Fabryczne)
        self.total_capex = self.base_price_after_discount + self.options_capex

        self.months_grid = [24, 36, 48, 60]
        self.mileage_grid = [10000, 20000, 30000, 40000, 50000, 60000]

    def _fetch_rv(self, months: int, mileage: int) -> float:
        """Pobiera Wartość Rezydualną % z MOCK RV. W przyszłości integracja API Samar."""

        # Fallback RV
        default_rvs: Dict[int, float] = {24: 0.65, 36: 0.55, 48: 0.45, 60: 0.35}

        base_rv = default_rvs.get(months, 0.50)
        # Lekka degradacja RV za przebieg
        degradation = (mileage - 10000) / 10000 * 0.02
        return max(0.10, base_rv - degradation)

    def _calculate_pmt(self, months: int, mileage: int, rv_pct: float) -> float:
        """Kalkulacja raty finansowej uproszczonym PMT (Rata stała z lokatą i wykupem)"""
        if months <= 0:
            return 0.0

        rate = (self.input.wibor_pct + self.input.margin_pct) / 100.0 / 12.0
        n_periods = months

        # Wartość Bieżąca
        pv = self.total_capex - (self.total_capex * (self.input.upfront_pct / 100.0))
        # Wartość Końcowa (Wykup) - RV liczone od ceny Karkasu (Cena KATALOGOWA bazy ze wszystkim)
        # RV zazwyczaj liczy się od pełnej wartości MSRP, ew transakcji.
        # Ustalamy jako standard rynek: RV_PLN = CAPEX * RV%
        fv = self.total_capex * rv_pct

        # Excel: PMT(rate, nper, pv, [fv], [type])
        # W Pythonie prosty wzór dla PMT(type=0 - end of month)
        if rate == 0:
            return (pv - fv) / n_periods

        pmt = (rate * (pv - fv / ((1 + rate) ** n_periods))) / (
            1 - (1 + rate) ** -n_periods
        )

        # Dodajemy amortyzację usług serwisowych na cały kontrakt
        monthly_service = self.service_capex / n_periods if n_periods > 0 else 0

        # Dodatki LTR
        # Opony (Sztuczny koszt)
        tires_monthly = 50.0 if not self.input.all_season_tires else 20.0

        # Auto Zastępcze (Sztuczny koszt)
        replacement_monthly = 30.0 if self.input.replacement_car else 0.0

        return round(pmt + monthly_service + tires_monthly + replacement_monthly, 2)

    def build_matrix(self) -> List[Dict[str, Any]]:
        result = []
        for m in self.months_grid:
            for km in self.mileage_grid:
                rv_pct = self._fetch_rv(m, km)
                pmt_net = self._calculate_pmt(m, km, rv_pct)

                result.append(
                    {
                        "months": m,
                        "km_per_year": km,
                        "total_capex": round(self.total_capex, 2),
                        "rv_pct": round(rv_pct * 100, 2),  # Jak 0.52 to 52.0%
                        "price_net": pmt_net,
                        "price_gross": round(pmt_net * 1.23, 2),
                    }
                )
        return result
