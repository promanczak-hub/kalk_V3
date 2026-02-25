from typing import List, Dict, Any


class InsuranceCalculator:
    """Moduł odpowiedzialny za kalkulację ubezpieczenia (Zgodnie z LTR_V1)"""

    def __init__(self, insurance_rates: List[Dict[str, Any]], amortization_pct: float):
        """
        insurance_rates to lista wierszy z ltr_admin_ubezpieczenia dla danej klasy (lub domyślnej)
        """
        # Sortujemy by upewnić się, że pozycje są rosnąco po KolejnyRok
        self.rates = sorted(insurance_rates, key=lambda x: x.get("KolejnyRok", 0))
        self.amortization_pct = amortization_pct  # Zwykle to: (StartPrice - ResidualValue) / Months / StartPrice

    def calculate_cost(self, months: int, capex: float) -> Dict[str, Any]:
        """
        Metoda wyliczająca ubezpieczenie rok po roku (do 7 lat).
        capex: odpowiada CenaZakupu
        months: całkowity okres najmu w miesiącach
        """
        total_insurance_net = 0.0

        # LTR V1 ma pętle do LICZBA_LAT = 7
        LICZBA_LAT = 7

        yearly_details = []

        for r in range(1, LICZBA_LAT + 1):
            # 1. Znajdź rating na ten rok pod klasę, jeśli brak, to ratujemy się NULL z bazy (lub ostatecznie pierwszym/ostatnim)
            rate_for_year = next(
                (rate for rate in self.rates if rate.get("KolejnyRok") == r), None
            )
            if not rate_for_year:
                # Jeśli z jakiegoś powodu nie ma w słowniku, podciągamy z poprzedniego lub pomin
                continue

            # 2. Oblicz podstawę
            liczba_miesiecy_odpisu = (r - 1) * 12
            podstawa_naliczania = capex * (
                1 - liczba_miesiecy_odpisu * self.amortization_pct
            )
            podstawa_naliczania = max(
                0.0, podstawa_naliczania
            )  # Zabezpieczenie na ujemne

            # W V1 robili jakieś doubezpieczenia, pominę to i wezmę tylko główną podstawę AC
            stawka_bazowa_ac = float(rate_for_year.get("StawkaBazowaAC", 0.0))
            skladka_ac = round(stawka_bazowa_ac * podstawa_naliczania, 2)

            # Składka OC to kwota stała ryczałtowa
            skladka_oc = float(rate_for_year.get("SkladkaOC", 0.0))

            suma_roczna = skladka_ac + skladka_oc

            # 3. Dodaj proporcjonalnie do puli na cały okres
            # W V1 było: if (pozycja.Rok == 1) ... if (liczbaMiesiecy < miesiace)
            # Uproszczając: patrzymy czy cały ten rok mieści się w naszym okresie
            miesiace_koniec_roku = r * 12
            miesiace_poczatek_roku = (r - 1) * 12

            skladka_należna_za_rok = 0.0

            if months >= miesiace_koniec_roku:
                # Cały rok wchodzi
                skladka_należna_za_rok = suma_roczna
            elif months > miesiace_poczatek_roku:
                # Weź proporcję z tego roku np. 6 z 12 miesięcy 3. roku
                coeff = (months - miesiace_poczatek_roku) / 12.0
                skladka_należna_za_rok = suma_roczna * coeff
            else:
                # Kontrakt się już skończył, nic z tego roku nie wchodzi
                skladka_należna_za_rok = 0.0

            total_insurance_net += skladka_należna_za_rok

            yearly_details.append(
                {
                    "rok": r,
                    "podstawa": round(podstawa_naliczania, 2),
                    "stawka_ac": stawka_bazowa_ac,
                    "skladka_ac": skladka_ac,
                    "skladka_oc": skladka_oc,
                    "suma_roczna": round(suma_roczna, 2),
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
