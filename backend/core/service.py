import logging


from pydantic import BaseModel, Field

from core.database import supabase

logger = logging.getLogger(__name__)


class ServiceCalculatorInput(BaseModel):
    z_serwisem: bool = Field(default=False)
    opcja_serwisowa: str = Field(default="ASO", pattern="^(ASO|NON-ASO)$")
    pakiet_serwisowy: float = Field(default=0.0)
    inne_koszty_serwisowania_netto: float = Field(default=0.0)

    # Vehicle specific params required for DB lookup
    samar_class_id: int
    engine_type_id: int
    power_kw: float

    # Contract params expected
    przebieg: int
    okres: int


class ServiceCalculator:
    """
    Kalkulator kosztów serwisowych bazujący na stawkach za km (ASO / Non-ASO).
    """

    def __init__(self, data: ServiceCalculatorInput):
        self.data = data
        self.supabase = supabase
        self._rate_per_km = 0.0

    def calculate(self) -> float:
        """
        Zwraca miesięczny koszt serwisu (Czynsz Techniczny Netto).
        """
        # 1. Z serwisem flag bypass
        if not self.data.z_serwisem:
            logger.info("Service costs skipped (z_serwisem=False).")
            return 0.0

        base_cost = 0.0

        # 2. Pakiet Serwisowy Override
        if self.data.pakiet_serwisowy > 0:
            logger.info(
                f"Using fixed service package cost: {self.data.pakiet_serwisowy}"
            )
            base_cost = self.data.pakiet_serwisowy
        else:
            # 3. Standard DB rate * Mileage calculation
            self._fetch_rate_from_db()
            base_cost = self._rate_per_km * self.data.przebieg
            logger.info(
                f"Calculated service cost from mileage: {self.data.przebieg} km * {self._rate_per_km} = {base_cost}"
            )

        # 4. Inne koszty (Additional Net Cost)
        total_cost = base_cost + self.data.inne_koszty_serwisowania_netto

        # 5. Distribute over contract months
        if self.data.okres <= 0:
            return 0.0

        monthly_cost = total_cost / self.data.okres
        return monthly_cost

    def _determine_power_band(self) -> str:
        """Determines the power band string used in the DB schema."""
        if self.data.power_kw < 100:
            return "LOW"
        elif 100 <= self.data.power_kw <= 150:
            return "MID"
        else:
            return "HIGH"

    def _fetch_rate_from_db(self) -> None:
        """
        Queries the 'samar_service_costs' table for the per-km rate
        based on class, engine, and power band.
        """
        power_band = self._determine_power_band()
        logger.debug(
            f"Fetching service rate for Samar Class: {self.data.samar_class_id}, Engine: {self.data.engine_type_id}, Power: {power_band}"
        )

        try:
            response = (
                self.supabase.table("samar_service_costs")
                .select("cost_aso_per_km, cost_non_aso_per_km")
                .eq("samar_class_id", self.data.samar_class_id)
                .eq("engine_type_id", self.data.engine_type_id)
                .eq("power_band", power_band)
                .execute()
            )

            if response.data and len(response.data) > 0:
                record = response.data[0]
                if self.data.opcja_serwisowa == "ASO":
                    self._rate_per_km = float(record["cost_aso_per_km"])
                else:
                    self._rate_per_km = float(record["cost_non_aso_per_km"])
            else:
                logger.warning(
                    "No matching service cost found in DB. Defaulting rate to 0."
                )
                self._rate_per_km = 0.0

        except Exception as e:
            logger.error(f"Error fetching service rates: {str(e)}")
            self._rate_per_km = 0.0
