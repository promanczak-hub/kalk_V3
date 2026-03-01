from typing import List, Dict, Any


class InsuranceCalculator:
    """Moduł odpowiedzialny za kalkulację ubezpieczenia (Zgodnie z LTR_V1)"""

    def __init__(
        self,
        insurance_rates: List[Dict[str, Any]],
        damage_coefficients: Dict[str, Any],
        settings: Any,
        amortization_pct: float,
        total_km: int,
    ):
        """
        insurance_rates to lista wierszy z ltr_admin_ubezpieczenia dla danej klasy (lub domyślnej)
        """
        self.rates = sorted(insurance_rates, key=lambda x: x.get("KolejnyRok", 0))
        self.damage_coefficients = damage_coefficients
        self.settings = settings
        self.amortization_pct = amortization_pct
        self.total_km = total_km

    def calculate_cost(self, months: int, capex: float) -> Dict[str, Any]:
        """
        Metoda wyliczająca ubezpieczenie rok po roku (do 7 lat).
        """
        total_insurance_net = 0.0
        LICZBA_LAT = 7
        yearly_details = []

        # 1. Średnia Wartość Szkody dla całego kontraktu (Fundusz Szkodowy)
        avg_damage_value = float(self.settings.ins_avg_damage_value)
        avg_damage_mileage = (
            float(self.settings.ins_avg_damage_mileage)
            if self.settings.ins_avg_damage_mileage > 0
            else 1.0
        )

        wsp_sredni_przebieg = float(
            self.damage_coefficients.get("wsp_sredni_przebieg", 1.0)
        )
        wsp_wartosc_szkody = float(
            self.damage_coefficients.get("wsp_wartosc_szkody", 1.0)
        )

        total_damage_fund = avg_damage_value * (
            (self.total_km / avg_damage_mileage)
            * wsp_sredni_przebieg
            * wsp_wartosc_szkody
        )

        for r in range(1, LICZBA_LAT + 1):
            rate_for_year = next(
                (rate for rate in self.rates if rate.get("KolejnyRok") == r), None
            )
            if not rate_for_year:
                continue

            # a. Podstawa
            liczba_miesiecy_odpisu = (r - 1) * 12
            podstawa_naliczania = capex * (
                1 - liczba_miesiecy_odpisu * self.amortization_pct
            )
            podstawa_naliczania = max(0.0, podstawa_naliczania)

            # b. Składki bazowe
            stawka_bazowa_ac = float(rate_for_year.get("StawkaBazowaAC", 0.0))
            skladka_ac = round(stawka_bazowa_ac * podstawa_naliczania, 2)
            skladka_oc = float(rate_for_year.get("SkladkaOC", 0.0))

            # c. Doubezpieczenie kradzieży / nauka jazdy (V1)
            doub_kradzez = skladka_ac * float(self.settings.ins_theft_doub_pct)
            doub_nauka = skladka_ac * float(self.settings.ins_driving_school_doub_pct)

            suma_roczna = skladka_ac + skladka_oc + doub_kradzez + doub_nauka

            # d. Fundusz szkodowy na ten rok
            miesiace_koniec_roku = r * 12
            miesiace_poczatek_roku = (r - 1) * 12

            srednia_rocznie_szkoda = 0.0
            if months <= miesiace_koniec_roku and months > miesiace_poczatek_roku:
                srednia_rocznie_szkoda = (
                    (total_damage_fund / months) * (months - miesiace_poczatek_roku)
                    if months > 0
                    else 0.0
                )
            elif months > miesiace_koniec_roku:
                srednia_rocznie_szkoda = (
                    (total_damage_fund / months) * 12 if months > 0 else 0.0
                )

            suma_rocznie_i_szkody = suma_roczna + srednia_rocznie_szkoda

            # e. Proporcja jeśli kontrakt kończy się w trakcie tego roku
            skladka_należna_za_rok = 0.0
            if r == 1:
                # V1 logik: for year 1, proportional if < 12 months
                if months >= 12:
                    skladka_należna_za_rok = suma_roczna
                else:
                    skladka_należna_za_rok = (
                        suma_roczna * (months / 12.0) if months > 0 else 0.0
                    )
                skladka_należna_za_rok += srednia_rocznie_szkoda
            else:
                if months > miesiace_poczatek_roku and months < miesiace_koniec_roku:
                    coeff = (months - miesiace_poczatek_roku) / 12.0
                    skladka_należna_za_rok = (
                        suma_roczna * coeff
                    ) + srednia_rocznie_szkoda
                elif months >= miesiace_koniec_roku:
                    skladka_należna_za_rok = suma_rocznie_i_szkody
                else:
                    skladka_należna_za_rok = 0.0

            total_insurance_net += skladka_należna_za_rok

            yearly_details.append(
                {
                    "rok": r,
                    "podstawa": round(podstawa_naliczania, 2),
                    "stawka_ac": stawka_bazowa_ac,
                    "skladka_ac": skladka_ac,
                    "skladka_oc": skladka_oc,
                    "doub_kradzez": round(doub_kradzez, 2),
                    "doub_nauka": round(doub_nauka, 2),
                    "suma_roczna": round(suma_roczna, 2),
                    "szkoda_roczna": round(srednia_rocznie_szkoda, 2),
                    "suma_rocznie_i_szkody": round(suma_rocznie_i_szkody, 2),
                    "przypisana_do_kosztu": round(skladka_należna_za_rok, 2),
                }
            )

        return {
            "total_insurance": round(total_insurance_net, 2),
            "monthly_insurance": round(total_insurance_net / months, 2)
            if months > 0
            else 0.0,
            "years_details": yearly_details,
        }
