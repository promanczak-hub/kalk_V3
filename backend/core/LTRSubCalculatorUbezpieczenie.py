from typing import Any, Dict, List


class InsuranceCalculator:
    def __init__(
        self,
        insurance_rates: List[Dict[str, Any]],
        damage_coefficients: Dict[str, Any],
        settings: Any,
        amortization_pct: float,
        total_km: int,
    ):
        self.insurance_rates = insurance_rates
        self.damage_coefficients = damage_coefficients
        self.settings = settings
        self.amortization_pct = amortization_pct
        self.total_km = total_km
        self.LICZBA_LAT = 7

    def calculate_cost(self, months: int, base_price: float) -> dict:
        if months <= 0:
            raise ValueError("Okres (months) musi być > 0")
        if base_price <= 0:
            raise ValueError("Cena bazowa (base_price) musi być > 0")

        trace: list[dict[str, Any]] = []
        total_cost_period = 0.0

        average_damage_value_base = float(
            getattr(self.settings, "ins_avg_damage_value", 0.0) or 0.0
        )
        average_damage_mileage = float(
            getattr(self.settings, "ins_avg_damage_mileage", 0.0) or 0.0
        )

        if average_damage_value_base <= 0:
            raise ValueError(
                "Brak poprawnego parametru `ins_avg_damage_value` w Control Center."
            )
        if average_damage_mileage <= 0:
            raise ValueError(
                "Brak poprawnego parametru `ins_avg_damage_mileage` w Control Center."
            )

        if not self.damage_coefficients:
            raise ValueError(
                "Brak współczynników szkodowych (Pusta tabela ltr_admin_wspolczynniki_szkodowe dla tej klasy pojazdu). Kalkulacja przerwana."
            )

        if "WspSredniPrzebieg" not in self.damage_coefficients:
            raise ValueError(
                "Brak parametru 'WspSredniPrzebieg' we współczynnikach szkodowych. Skonfiguruj ltr_admin_wspolczynniki_szkodowe."
            )
        wsp_sredni_przebieg = float(self.damage_coefficients["WspSredniPrzebieg"])

        if "WspWartoscSzkody" not in self.damage_coefficients:
            raise ValueError(
                "Brak parametru 'WspWartoscSzkody' we współczynnikach szkodowych. Skonfiguruj ltr_admin_wspolczynniki_szkodowe."
            )
        wsp_wartosc_szkody = float(self.damage_coefficients["WspWartoscSzkody"])

        if average_damage_mileage > 0:
            srednia_szkoda_calosc = average_damage_value_base * (
                (self.total_km / average_damage_mileage)
                * wsp_sredni_przebieg
                * wsp_wartosc_szkody
            )
            trace.append(
                {
                    "krok": "Ubezpieczenie: Szacowana Szkoda Całkowita",
                    "rownanie": f"Baza {average_damage_value_base:.2f} * ({self.total_km}km / {average_damage_mileage}km * Współ.Przebiegu {wsp_sredni_przebieg:.4f} * Współ.Wartości {wsp_wartosc_szkody:.4f})",
                    "wynik": srednia_szkoda_calosc,
                }
            )
        else:
            srednia_szkoda_calosc = 0.0

        for year in range(1, self.LICZBA_LAT + 1):
            v1 = year * 12
            v2 = (year - 1) * 12

            # Znajdź stawkę ubezpieczeniową dla danego roku z tabeli
            rok_rate = next(
                (r for r in self.insurance_rates if r.get("rok") == year), None
            )

            if not rok_rate:
                raise ValueError(
                    f"Brak stawki ubezpieczeniowej w tabeli "
                    f"ltr_admin_ubezpieczenia dla roku {year}. "
                    f"Kalkulacja niemożliwa bez kompletnych danych."
                )

            stawka_ac = float(rok_rate.get("stawka_bazowa_ac", 0))
            skladka_oc = float(rok_rate.get("skladka_oc_zl", 0))

            if stawka_ac <= 0 or skladka_oc <= 0:
                raise ValueError(
                    f"Stawka AC ({stawka_ac}) lub OC ({skladka_oc}) "
                    f"dla roku {year} jest <= 0. Uzupełnij dane w Control Center."
                )

            liczba_miesiecy_przed_rokiem = (year - 1) * 12
            depreciation_factor = 1.0 - (
                liczba_miesiecy_przed_rokiem * self.amortization_pct
            )
            if depreciation_factor < 0:
                depreciation_factor = 0.0

            podstawa_naliczania = base_price * depreciation_factor

            skladka_ac_kwota = round(podstawa_naliczania * stawka_ac, 2)
            skladka_oc_kwota = skladka_oc

            suma_skladki_rok = skladka_ac_kwota + skladka_oc_kwota

            # Pro-rata calculation per year logic from V1 C#
            skladka_roczna = 0.0
            v1 = year * 12
            v2 = (year - 1) * 12

            if year == 1:
                if months >= 12:
                    skladka_roczna = suma_skladki_rok
                else:
                    skladka_roczna = suma_skladki_rok * (months / 12.0)
            else:
                if months < v1 and months > v2:
                    skladka_roczna = suma_skladki_rok * ((months - v2) / 12.0)
                elif months >= v1:
                    skladka_roczna = suma_skladki_rok

            # Szkody logic from V1
            szkoda_rocznie = 0.0
            if months <= v1 and months > v2:
                szkoda_rocznie = (srednia_szkoda_calosc / months) * (months - v2)
            elif months > v1:
                szkoda_rocznie = (srednia_szkoda_calosc / months) * 12.0

            skladka_laczna_rok = skladka_roczna + szkoda_rocznie

            # Add to total cost ONLY if the months span overlaps this year
            if months > v2:
                print(
                    f"[DEBUG_INS] Year {year}: AC={skladka_ac_kwota:.2f}, OC={skladka_oc_kwota:.2f}, Prorata={skladka_roczna:.2f}, Szkoda={szkoda_rocznie:.2f}"
                )
                trace.append(
                    {
                        "krok": f"Ubezpieczenie (Rok {year})",
                        "rownanie": f"DepSkala {depreciation_factor:.4f} -> AC {skladka_ac_kwota:.2f} + OC {skladka_oc_kwota:.2f} (Składka prorata {skladka_roczna:.2f}) + Szkoda prorata {szkoda_rocznie:.2f}",
                        "wynik": skladka_laczna_rok,
                    }
                )
                total_cost_period += skladka_laczna_rok

        total_cost_net = total_cost_period
        monthly_cost_net = total_cost_net / months if months > 0 else 0.0

        trace.append(
            {
                "krok": "Ubezpieczenie: Razem za cały okres",
                "rownanie": f"Suma z loopa rat dla {months} miesięcy",
                "wynik": total_cost_net,
            }
        )

        return {
            "monthly_insurance": monthly_cost_net,
            "total_insurance": total_cost_net,
            "trace": trace,
        }
