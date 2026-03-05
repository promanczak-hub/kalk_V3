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
        total_cost_period = 0.0

        # Optional Flags - assuming False for now unless logic added to UI
        add_theft_insurance = False
        add_driving_school = False

        theft_doub_rate_pct = getattr(self.settings, "ins_theft_doub_pct", 0.0)
        driving_school_rate_pct = getattr(
            self.settings, "ins_driving_school_doub_pct", 0.0
        )

        average_damage_value_base = getattr(
            self.settings, "ins_avg_damage_value", 1500.0
        )
        average_damage_mileage = getattr(
            self.settings, "ins_avg_damage_mileage", 30000.0
        )

        wsp_sredni_przebieg = float(
            self.damage_coefficients.get("WspSredniPrzebieg", 1.0)
        )
        wsp_wartosc_szkody = float(
            self.damage_coefficients.get("WspWartoscSzkody", 1.0)
        )

        if average_damage_mileage > 0:
            srednia_szkoda_calosc = average_damage_value_base * (
                (self.total_km / average_damage_mileage)
                * wsp_sredni_przebieg
                * wsp_wartosc_szkody
            )
        else:
            srednia_szkoda_calosc = 0.0

        # Zapamiętujemy ostatnią znaną stawkę (przydatne jako fallback dla brakujących lat)
        last_known_rate = None
        if self.insurance_rates:
            last_known_rate = self.insurance_rates[0]

        for year in range(1, self.LICZBA_LAT + 1):
            v1 = year * 12
            v2 = (year - 1) * 12

            # Znajdź stawkę ubezpieczeniową dla danego roku z tabeli
            rok_rate = next(
                (r for r in self.insurance_rates if r.get("KolejnyRok") == year), None
            )

            # Zgodnie z wytycznymi z GEMINI.md, system nie powinien crashować - miękkie lądowanie z ostatnio znaną stawką
            if not rok_rate and last_known_rate:
                rok_rate = last_known_rate

            if not rok_rate:
                # Ostateczny fallback, jeżeli baza jest kompletnie pusta
                stawka_ac = 0.025
                skladka_oc = 1200.0
            else:
                stawka_ac = float(rok_rate.get("StawkaBazowaAC", 0.025))
                skladka_oc = float(rok_rate.get("SkladkaOC", 1200.0))
                last_known_rate = rok_rate

            liczba_miesiecy_przed_rokiem = (year - 1) * 12
            depreciation_factor = 1.0 - (
                liczba_miesiecy_przed_rokiem * self.amortization_pct
            )
            if depreciation_factor < 0:
                depreciation_factor = 0.0

            podstawa_naliczania = base_price * depreciation_factor

            skladka_ac_kwota = round(podstawa_naliczania * stawka_ac, 2)
            skladka_oc_kwota = skladka_oc

            doubezpieczenie_kradziez = (
                (skladka_ac_kwota * (theft_doub_rate_pct / 100.0))
                if add_theft_insurance
                else 0.0
            )
            doubezpieczenie_nauka = (
                (skladka_ac_kwota * (driving_school_rate_pct / 100.0))
                if add_driving_school
                else 0.0
            )

            suma_skladki_rok = (
                skladka_ac_kwota
                + skladka_oc_kwota
                + doubezpieczenie_kradziez
                + doubezpieczenie_nauka
            )

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
                total_cost_period += skladka_laczna_rok

        total_cost_net = total_cost_period
        monthly_cost_net = total_cost_net / months if months > 0 else 0.0

        return {
            "monthly_insurance": monthly_cost_net,
            "total_insurance": total_cost_net,
        }
