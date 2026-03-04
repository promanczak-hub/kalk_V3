import logging
from functools import lru_cache
from typing import Any, cast

from pydantic import BaseModel, Field

from core.database import supabase

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def get_service_rate_from_db(
    samar_class_id: int, engine_type_id: int, power_band: str
) -> dict:
    try:
        response = (
            supabase.table("samar_service_costs")
            .select("cost_aso_per_km, cost_non_aso_per_km")
            .eq("samar_class_id", samar_class_id)
            .eq("engine_type_id", engine_type_id)
            .eq("power_band", power_band)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return cast(dict[str, Any], response.data[0])
    except Exception as e:
        logger.error(f"Error fetching service rates: {str(e)}")
    return {}


class ServiceCalculatorInput(BaseModel):
    """Parametry wejściowe sub-kalkulatora serwisowego V3."""

    z_serwisem: bool = Field(default=True)
    opcja_serwisowa: str = Field(default="ASO", pattern="^(ASO|NON-ASO)$")

    # Normatywny przebieg floty (floor) — z control_center
    normatywny_przebieg_mc: int = Field(
        default=2916,
        description="Normatywny przebieg floty km/mc (= 35 000 km/rok). Floor dla kosztu serwisu.",
    )

    # Vehicle params for DB rate lookup
    samar_class_id: int
    engine_type_id: int
    power_kw: float

    # Contract params
    przebieg: int
    okres: int


class ServiceCalculator:
    """
    Kalkulator kosztów serwisowych V3.

    Logika:
        stawka_za_km = z samar_service_costs (ASO lub nonASO, wg power_band)
        effective_km = max(total_km, normatywny_przebieg_mc × months)
        service_total = effective_km × stawka_za_km
        monthly = service_total / months
    """

    def __init__(self, data: ServiceCalculatorInput):
        self.data = data
        self._rate_per_km = 0.0

    def calculate(self) -> float:
        """Zwraca miesięczny koszt serwisu (netto)."""
        if not self.data.z_serwisem:
            logger.info("Service costs skipped (z_serwisem=False).")
            return 0.0

        if self.data.okres <= 0:
            return 0.0

        self._fetch_rate_from_db()

        # Floor: normatywny przebieg floty × miesiące kontraktu
        floor_km = self.data.normatywny_przebieg_mc * self.data.okres
        effective_km = max(self.data.przebieg, floor_km)

        service_total = effective_km * self._rate_per_km

        logger.info(
            f"Service cost: effective_km={effective_km} "
            f"(actual={self.data.przebieg}, floor={floor_km}), "
            f"rate={self._rate_per_km}/km, total={service_total:.2f}"
        )

        monthly_cost = service_total / self.data.okres
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
        """Queries the cached function for the per-km rate."""
        power_band = self._determine_power_band()

        record = get_service_rate_from_db(
            self.data.samar_class_id, self.data.engine_type_id, power_band
        )

        if record:
            if self.data.opcja_serwisowa == "ASO":
                self._rate_per_km = float(record.get("cost_aso_per_km", 0.0))
            else:
                self._rate_per_km = float(record.get("cost_non_aso_per_km", 0.0))
        else:
            logger.warning(
                "No matching service cost found in DB. Defaulting rate to 0."
            )
            self._rate_per_km = 0.0
