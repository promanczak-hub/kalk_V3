import logging
from functools import lru_cache
from typing import Any, cast

from pydantic import BaseModel, Field

from core.database import supabase

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def get_service_rate_from_db(
    samar_class_id: int, engine_type_id: int, power_band: str
) -> dict[str, Any]:
    """Pobiera stawkę serwisową za km z tabeli samar_service_costs."""
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
        logger.error(f"Error fetching service rates: {e!s}")
    return {}


class ServiceCalculatorInput(BaseModel):
    """Parametry wejściowe sub-kalkulatora serwisowego V3.

    Logika priorytetu:
        1. PakietSerwisowy > 0 → override (zastępuje km-ówkę)
        2. W przeciwnym razie: km-ówka z samar_service_costs
        3. InneKosztySerwisowania dolicza się ZAWSZE (miesięcznie)
    """

    z_serwisem: bool = Field(default=True)
    opcja_serwisowa: str = Field(default="ASO", pattern="^(ASO|NON-ASO)$")

    # Normatywny przebieg floty (floor) — z control_center
    normatywny_przebieg_mc: int = Field(
        default=1667,
        description=(
            "Normatywny przebieg floty km/mc (= 20 000 km/rok). "
            "Floor dla kosztu serwisu."
        ),
    )

    # Vehicle params for DB rate lookup
    samar_class_id: int
    engine_type_id: int
    power_kw: float

    # Contract params
    przebieg: int
    okres: int

    # --- Pola V1 port ---
    pakiet_serwisowy: float = Field(
        default=0.0,
        description=(
            "Dedykowany pakiet serwisowy (netto na kontrakt). "
            "Jeśli > 0, zastępuje logikę km-ową."
        ),
    )
    inne_koszty_serwisowania_netto: float = Field(
        default=0.0,
        description=(
            "Dodatkowe koszty serwisowania netto MIESIĘCZNIE. "
            "Doliczane do wyniku niezależnie od trybu."
        ),
    )
    korekta_serwis_procent: float = Field(
        default=0.0,
        description=(
            "Korekta kosztu serwisu w %. Dodatnia = drożej, ujemna = taniej. "
            "Np. 0.05 = +5%, -0.10 = -10%. Stosowana do kosztu bazowego (km-ówka)."
        ),
    )


class ServiceCalculator:
    """Kalkulator kosztów serwisowych V3.

    Algorytm:
        1. Jeśli pakiet_serwisowy > 0 → koszt = pakiet / okres
        2. W przeciwnym razie:
           stawka_za_km = z samar_service_costs (ASO/nonASO, wg power_band)
           effective_km = max(total_km, normatywny_przebieg_mc × months)
           koszt = effective_km × stawka_za_km / months
        3. Do wyniku ZAWSZE dodaje inne_koszty_serwisowania_netto (mc)
    """

    def __init__(self, data: ServiceCalculatorInput) -> None:
        self.data = data
        self._rate_per_km = 0.0

    def calculate(self) -> float:
        """Zwraca miesięczny koszt serwisu (netto)."""
        if not self.data.z_serwisem:
            logger.info("Service costs skipped (z_serwisem=False).")
            return 0.0

        if self.data.okres <= 0:
            return 0.0

        monthly_base = self._calculate_base_monthly()
        monthly_extra = self.data.inne_koszty_serwisowania_netto

        total_monthly = monthly_base + monthly_extra

        logger.info(
            f"Service monthly: base={monthly_base:.2f}, "
            f"extra={monthly_extra:.2f}, total={total_monthly:.2f}"
        )

        return total_monthly

    def _calculate_base_monthly(self) -> float:
        """Oblicza bazowy koszt miesięczny serwisu.

        PakietSerwisowy > 0 → override (total na kontrakt / miesiące).
        W przeciwnym razie → km-ówka z DB.
        """
        if self.data.pakiet_serwisowy > 0:
            monthly = self.data.pakiet_serwisowy / self.data.okres
            logger.info(
                f"PakietSerwisowy override: "
                f"{self.data.pakiet_serwisowy:.2f} / "
                f"{self.data.okres} mc = {monthly:.2f}/mc"
            )
            return monthly

        return self._calculate_km_based_monthly()

    def _calculate_km_based_monthly(self) -> float:
        """Logika km-owa: stawka × effective_km / miesiące + korekta %."""
        self._fetch_rate_from_db()

        floor_km = self.data.normatywny_przebieg_mc * self.data.okres
        effective_km = max(self.data.przebieg, floor_km)

        service_total = effective_km * self._rate_per_km

        # Korekta serwis ±% (V1: KorektaSerwisProcent = 5% admin)
        if self.data.korekta_serwis_procent != 0.0:
            korekta = service_total * self.data.korekta_serwis_procent
            service_total += korekta
            logger.info(
                f"Service correction: {self.data.korekta_serwis_procent:+.2%} "
                f"= {korekta:+.2f} PLN"
            )

        logger.info(
            f"Service km-based: effective_km={effective_km} "
            f"(actual={self.data.przebieg}, floor={floor_km}), "
            f"rate={self._rate_per_km}/km, total={service_total:.2f}"
        )

        return service_total / self.data.okres

    def _determine_power_band(self) -> str:
        """Determines the power band string used in the DB schema."""
        if self.data.power_kw < 100:
            return "LOW"
        elif self.data.power_kw <= 150:
            return "MID"
        return "HIGH"

    def _fetch_rate_from_db(self) -> None:
        """Queries the cached function for the per-km rate."""
        power_band = self._determine_power_band()

        record = get_service_rate_from_db(
            self.data.samar_class_id,
            self.data.engine_type_id,
            power_band,
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
