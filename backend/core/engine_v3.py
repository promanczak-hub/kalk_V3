from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony
from core.additional_costs import AdditionalCostsCalculator
from core.service import ServiceCalculatorInput, ServiceCalculator
from core.engine import get_vehicle_from_db
from core.database import supabase
from core.models import ControlCenterSettings


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

    # V1 Additional Costs Flags
    add_gsm_subscription: bool = False
    add_hook_installation: bool = False
    add_sales_prep: bool = True

    # Vehicle Metadata for RV lookup
    brand: str = ""
    model: str = ""
    version: str = ""
    engine: str = ""
    fuel: str = ""
    transmission: str = ""
    body_type: str = ""

    # V3 TCO Flags
    z_oponami: bool = True
    klasa_opony_string: str = ""
    korekta_kosztu_opon: bool = False
    koszt_opon_korekta: float = 0.0
    liczba_kompletow_opon: Optional[float] = None
    replacement_car: bool
    samar_class_id: int = 2  # Domyślnie PODSTAWOWA B MAŁE
    engine_type_id: int = 1  # 1 = ICE, 2 = HEV, 3 = MHEV, 4 = PHEV, 5 = BEV
    power_kw: float = 110.0

    # Service Flags
    z_serwisem: bool = True
    opcja_serwisowa: str = "ASO"
    pakiet_serwisowy: float = 0.0
    inne_koszty_serwisowania_netto: float = 0.0


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

        # Fetch vehicle
        vid = getattr(self.input, "vehicle_id", "")
        self.vehicle = get_vehicle_from_db(vid) if vid else {}

        # Fetch Control Center Settings
        self.settings: Optional[ControlCenterSettings] = None
        try:
            res = supabase.table("control_center").select("*").eq("id", 1).execute()
            raw_settings = res.data[0] if res.data else {}
            self.settings = ControlCenterSettings(**raw_settings)
        except Exception as e:
            print(f"Error fetching control center settings: {e}")

        # Tires logic
        self.tires_calc = LTRSubCalculatorOpony(
            z_oponami=getattr(self.input, "z_oponami", True),
            klasa_opony_string=getattr(self.input, "klasa_opony_string", ""),
            srednica_felgi=self.vehicle.get("srednica_felgi", 16)
            if self.vehicle
            else 16,
            korekta_kosztu=getattr(self.input, "korekta_kosztu_opon", False),
            koszt_opon_korekta=getattr(self.input, "koszt_opon_korekta", 0.0),
            sets_needed_override=getattr(self.input, "liczba_kompletow_opon", None),
        )

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

        # Service
        svc_input = ServiceCalculatorInput(
            z_serwisem=self.input.z_serwisem,
            opcja_serwisowa=self.input.opcja_serwisowa,
            pakiet_serwisowy=self.input.pakiet_serwisowy,
            inne_koszty_serwisowania_netto=self.input.inne_koszty_serwisowania_netto,
            samar_class_id=self.input.samar_class_id,
            engine_type_id=self.input.engine_type_id,
            power_kw=self.input.power_kw,
            przebieg=mileage,
            okres=months,
        )
        svc_calc = ServiceCalculator(svc_input)
        monthly_service = svc_calc.calculate()

        # Opony (Pobierane z zewnetrznego kalkulatora opon LTRSubCalculatorOpony)
        tires_res = self.tires_calc.calculate_cost(months, mileage)
        tires_total_cost = float(tires_res.get("OponyNetto", 0.0))
        tires_monthly = tires_total_cost / n_periods if n_periods > 0 else 0.0

        # Koszty Dodatkowe (Rejestracja, Hak, Przygotowanie, GSM)
        additional_costs_monthly = 0.0
        if self.settings:
            ac_calc = AdditionalCostsCalculator(self.settings, self.input, months)
            ac_res = ac_calc.calculate_cost()
            additional_costs_monthly = float(
                ac_res.get("monthly_additional_costs", 0.0)
            )

        # Auto Zastępcze (Sztuczny koszt)
        replacement_monthly = 0.0
        if self.input.replacement_car:
            from core.replacement_car import ReplacementCarCalculator

            rc_calc = ReplacementCarCalculator(self.input.samar_class_id)
            rc_res = rc_calc.calculate_cost(months, self.input.replacement_car)
            replacement_monthly = float(rc_res.get("monthly_replacement_car", 0.0))

        return round(
            pmt
            + monthly_service
            + tires_monthly
            + additional_costs_monthly
            + replacement_monthly,
            2,
        )

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
