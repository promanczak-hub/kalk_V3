import logging
from functools import lru_cache
from typing import Any, cast

from pydantic import BaseModel, Field

from core.database import supabase

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def get_base_service_rate(samar_class_id: int, target_mileage: int) -> dict[str, Any]:
    """Pobiera bazową stawkę serwisową za km opartą o klasę SAMAR i prób przebiegu."""
    try:
        response = (
            supabase.table("samar_class_service_rates")
            .select("przebieg_do, stawka_aso_per_km, stawka_non_aso_per_km")
            .eq("klasa_samar_fk", samar_class_id)
            .order("przebieg_do")
            .execute()
        )
        if response.data:
            data = cast(list[dict[str, Any]], response.data)
            for r in data:
                if int(r["przebieg_do"]) >= target_mileage:
                    return r
            # Fallback oparty o max przebieg zawarty w cenniku (jeśli przekroczono max tabelę)
            return data[-1]
        else:
            raise ValueError(f"Brak stawek w bazie dany dla klasy_id {samar_class_id}")
    except Exception as e:
        logger.error(f"Error fetching service rates: {e!s}")
        raise ValueError(f"Failed to fetch rates: {e!s}")


@lru_cache(maxsize=128)
def get_all_service_rates(samar_class_id: int) -> list[dict[str, Any]]:
    """Pobiera wszystkie progi serwisowe dla klasy, posortowane od najmniejszego."""
    try:
        response = (
            supabase.table("samar_class_service_rates")
            .select("przebieg_do, stawka_aso_per_km, stawka_non_aso_per_km")
            .eq("klasa_samar_fk", samar_class_id)
            .order("przebieg_do")
            .execute()
        )
        if response.data:
            return cast(list[dict[str, Any]], response.data)
        else:
            raise ValueError(
                f"Brak stawek w bazie dany dla klasy_id {samar_class_id}. Wymagane dla kalkulacji (Fail-Fast)."
            )
    except Exception as e:
        logger.error(f"Error fetching all service rates: {e!s}")
        raise ValueError(f"Failed to fetch all rates: {e!s}")


@lru_cache(maxsize=512)
def get_service_multiplier(table_name: str, key_column: str, key_val: str) -> float:
    """Pobiera mnożnik wprost z bazy, używając wartości z wiersza 'multiplier'."""
    if not key_val:
        return 1.0
    try:
        response = (
            supabase.table(table_name)
            .select("multiplier")
            .eq(key_column, key_val)
            .execute()
        )
        if response.data and len(response.data) > 0:
            data = cast(list[dict[str, Any]], response.data)
            return float(data[0]["multiplier"])
    except Exception as e:
        logger.error(f"Error fetching service multiplier from {table_name}: {e!s}")
    return 1.0


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
        default=1666,
        description=(
            "Normatywny przebieg floty km/mc (= ok. 20 000 km/rok). "
            "Floor dla kosztu serwisu."
        ),
    )

    # Vehicle params for DB rate lookup
    samar_class_id: int
    brand_normalized: str | None = Field(default=None)
    fuel_type: str | None = Field(default=None)
    drive_type: str | None = Field(default=None)
    gearbox_type: str | None = Field(default=None)

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

    def calculate(self) -> dict[str, Any]:
        """Zwraca miesięczny koszt serwisu (netto) wraz z trajektorią."""
        trace: list[dict[str, Any]] = []

        if not self.data.z_serwisem:
            logger.info("Service costs skipped (z_serwisem=False).")
            trace.append(
                {
                    "krok": "Serwis (Wyłączony)",
                    "rownanie": "z_serwisem = False",
                    "wynik": 0.0,
                }
            )
            return {"monthly_service": 0.0, "trace": trace}

        if self.data.okres <= 0:
            return {"monthly_service": 0.0, "trace": trace}

        base_res = self._calculate_base_monthly()
        monthly_base = base_res["monthly"]
        trace.extend(base_res["trace"])

        monthly_extra = self.data.inne_koszty_serwisowania_netto
        if monthly_extra > 0:
            trace.append(
                {
                    "krok": "Serwis: Inne Koszty Serwisowania (miesięcznie)",
                    "rownanie": f"Kwota z konfiguracji ręcznej: {monthly_extra:.2f}",
                    "wynik": monthly_extra,
                }
            )

        total_monthly = monthly_base + monthly_extra

        trace.append(
            {
                "krok": "Serwis: Razem Miesięcznie",
                "rownanie": f"{monthly_base:.2f} (Baza) + {monthly_extra:.2f} (Koszty Dodatkowe)",
                "wynik": total_monthly,
            }
        )

        logger.info(
            f"Service monthly: base={monthly_base:.2f}, "
            f"extra={monthly_extra:.2f}, total={total_monthly:.2f}"
        )

        return {"monthly_service": total_monthly, "trace": trace}

    def _calculate_base_monthly(self) -> dict[str, Any]:
        """Oblicza bazowy koszt miesięczny serwisu.

        PakietSerwisowy > 0 → override (total na kontrakt / miesiące).
        W przeciwnym razie → km-ówka z DB.
        """
        trace: list[dict[str, Any]] = []
        if self.data.pakiet_serwisowy > 0:
            monthly = self.data.pakiet_serwisowy / self.data.okres
            trace.append(
                {
                    "krok": "Serwis: Pakiet Serwisowy (Nadpisanie)",
                    "rownanie": f"Całkowity pakiet {self.data.pakiet_serwisowy:.2f} PLN / {self.data.okres} msc",
                    "wynik": monthly,
                }
            )
            logger.info(
                f"PakietSerwisowy override: "
                f"{self.data.pakiet_serwisowy:.2f} / "
                f"{self.data.okres} mc = {monthly:.2f}/mc"
            )
            return {"monthly": monthly, "trace": trace}

        return self._calculate_km_based_monthly()

    def _calculate_km_based_monthly(self) -> dict[str, Any]:
        """Logika km-owa (progresywna): sumuje iteracyjnie przedziały km × stawka, stosuje mnożniki + korekta %."""
        trace: list[dict[str, Any]] = []

        floor_km = self.data.normatywny_przebieg_mc * self.data.okres
        effective_km = max(self.data.przebieg, floor_km)

        trace.append(
            {
                "krok": "Serwis: Efektywny przebieg (km-ówka)",
                "rownanie": f"MAX({self.data.przebieg} km, (Normatywny {self.data.normatywny_przebieg_mc} * {self.data.okres} = {floor_km}))",
                "wynik": effective_km,
            }
        )

        service_total = self._calculate_progressive_service_total(effective_km, trace)

        # Korekta serwis ±% (V1: KorektaSerwisProcent = 5% admin)
        if self.data.korekta_serwis_procent != 0.0:
            korekta_kwota = service_total * self.data.korekta_serwis_procent
            service_total += korekta_kwota
            trace.append(
                {
                    "krok": "Serwis: Korekta Serwis Procent",
                    "rownanie": f"Korekta o {self.data.korekta_serwis_procent * 100:.2f}% ({korekta_kwota:+.2f} PLN)",
                    "wynik": service_total,
                }
            )
            logger.info(
                f"Service correction: {self.data.korekta_serwis_procent:+.2%} "
                f"= {korekta_kwota:+.2f} PLN"
            )

        logger.info(
            f"Service km-based progressive: effective_km={effective_km} "
            f"(actual={self.data.przebieg}, floor={floor_km}), "
            f"total={service_total:.2f}"
        )

        monthly = service_total / self.data.okres
        trace.append(
            {
                "krok": "Serwis: Miesięczna rata (km-ówka)",
                "rownanie": f"{service_total:.2f} PLN / {self.data.okres} msc",
                "wynik": monthly,
            }
        )

        return {"monthly": monthly, "trace": trace}

    def _calculate_progressive_service_total(
        self, effective_km: int, trace: list[dict[str, Any]]
    ) -> float:
        """Kalkulacja progresywna kosztów bazowych i aplikacja 4 mnożników."""
        # Kategoryczna blokada - brak stawek natychmiast wyrzuca z logiki biznesowej
        rates = get_all_service_rates(self.data.samar_class_id)
        if not rates:
            raise ValueError(
                f"Brak stawek serwisowych dla id={self.data.samar_class_id}"
            )

        total_base_cost = 0.0
        remaining_km = effective_km
        previous_threshold = 0

        for record in rates:
            threshold = int(record["przebieg_do"])
            if self.data.opcja_serwisowa == "ASO":
                rate = float(record.get("stawka_aso_per_km", 0.0))
            else:
                rate = float(record.get("stawka_non_aso_per_km", 0.0))

            # W danym segmencie mamy do dyspozycji interwał:
            segment_size = threshold - previous_threshold

            # Jeśli przeskakujemy przez aktualny segment w pełni:
            if remaining_km > segment_size:
                cost = segment_size * rate
                total_base_cost += cost
                remaining_km -= segment_size

                trace.append(
                    {
                        "krok": f"Serwis: Segment {previous_threshold} - {threshold} km",
                        "rownanie": f"{segment_size} km * {rate:.5f} PLN/km",
                        "wynik": cost,
                    }
                )
                previous_threshold = threshold
            else:
                # Wypełniamy tylko część lub całość ostatniego potrzebebnmego interwału
                cost = remaining_km * rate
                total_base_cost += cost
                trace.append(
                    {
                        "krok": f"Serwis: Ostatni Segment do {previous_threshold + remaining_km} km",
                        "rownanie": f"{remaining_km} km * {rate:.5f} PLN/km",
                        "wynik": cost,
                    }
                )
                remaining_km = 0
                break

        # Zabezpieczenie na wypadek ekstremalnie wysokich przebiegów wykraczających poza max prób w bazie
        if remaining_km > 0 and rates:
            last_record = rates[-1]
            if self.data.opcja_serwisowa == "ASO":
                last_rate = float(last_record.get("stawka_aso_per_km", 0.0))
            else:
                last_rate = float(last_record.get("stawka_non_aso_per_km", 0.0))

            cost = remaining_km * last_rate
            total_base_cost += cost
            trace.append(
                {
                    "krok": "Serwis: Przekroczenie limitu (Fallback przebiegu)",
                    "rownanie": f"Pozostało {remaining_km} km * {last_rate:.5f} PLN/km (Ostatnia użyta z tabeli)",
                    "wynik": cost,
                }
            )

        trace.append(
            {
                "krok": "Serwis: Suma kosztów bazowych przed mnożnikami",
                "rownanie": "Suma wszystkich segmentów kilometrowych (kaskadowo)",
                "wynik": total_base_cost,
            }
        )

        # --- APLIKACJA MNOŻNIKÓW TECHNICZNYCH ---
        val_brand = (self.data.brand_normalized or "").strip().upper()
        val_fuel = (self.data.fuel_type or "").strip().upper()
        val_drive = (self.data.drive_type or "").strip().upper()
        val_gearbox = (self.data.gearbox_type or "").strip().upper()

        m_brand = get_service_multiplier(
            "samar_service_brand_multipliers", "brand_normalized", val_brand
        )
        m_fuel = get_service_multiplier(
            "samar_service_fuel_multipliers", "fuel_normalized", val_fuel
        )
        m_drive = get_service_multiplier(
            "samar_service_drive_multipliers", "drive_normalized", val_drive
        )
        m_gearbox = get_service_multiplier(
            "samar_service_gearbox_multipliers", "gearbox_normalized", val_gearbox
        )

        total_multiplier = m_brand * m_fuel * m_drive * m_gearbox
        service_total = total_base_cost * total_multiplier

        trace.append(
            {
                "krok": "Serwis: Aplikacja 4 mnożników systemowych",
                "rownanie": f"Baza={total_base_cost:.2f} PLN | "
                f"Marka({val_brand or 'Brak'})={m_brand:.2f} | "
                f"Paliwo({val_fuel or 'Brak'})={m_fuel:.2f} | "
                f"Napęd({val_drive or 'Brak'})={m_drive:.2f} | "
                f"Skrzynia({val_gearbox or 'Brak'})={m_gearbox:.2f} | "
                f"Łączny mnożnik = x{total_multiplier:.3f}",
                "wynik": service_total,
            }
        )

        return service_total
