from typing import Any, Dict, List
from core.models import ControlCenterSettings
from api.schemas.calculator import CalculatorInput


class CalculationService:
    """
    Orkiestrator domenowy (UseCase) dla rdzennnego potoku LTRKalkulator.
    Separuje logikę wyodrębniania wskaźników od cienkiej warstwy tras (routerów).
    """

    def __init__(self, data: CalculatorInput, settings: ControlCenterSettings):
        self.data = data
        self.settings = settings

    def calculate_matrix(self) -> List[Dict[str, Any]]:
        from core.LTRKalkulator import LTRKalkulator

        # Pierwszy przebieg (z bazowymi lub defaultowymi ustawieniami)
        engine = LTRKalkulator(input_data=self.data, settings=self.settings)
        matrix = engine.build_matrix()

        # Wariant Precyzyjny (Goal Seek)
        exact_price = getattr(self.data, "pricing_exact_price", None)
        if exact_price is not None and exact_price > 0:
            req_months = int(getattr(self.data, "okres_bazowy", 48) or 48)
            req_total_km = int(getattr(self.data, "przebieg_bazowy", 140000) or 140000)

            target_cell = None
            for cell in matrix:
                if (
                    cell.get("Okres") == req_months
                    and cell.get("PrzebiegKontrakt") == req_total_km
                ):
                    target_cell = cell
                    break

            if target_cell:
                podstawa = target_cell.get("PodstawaMarzy", 0.0)
                koszty = target_cell.get("KosztyLaczneMC", 0.0)

                # Wzór matematyczny: Marza = (DocelowaRata - Koszty) / (DocelowaRata - Koszty + Podstawa) -> gdzie DocelowaRata - Koszty = PożądanyZysk
                # Czyli DocelowaRata = Koszty + Zysk, a Zysk = Marza / (1 - Marza) * Podstawa.
                # W LTRSubCalculatorStawka: ZyskWlasnyMC = podstawa_marzy * wspolczynnik_marzy, gdzie wspolczynnik_marzy = self.margin_pct / 100.0 / (1 - self.margin_pct / 100.0)
                # Oznacza to, że ZyskWlasnyMC = (M / (1-M)) * Podstawa
                # RataDocelowa = Koszty + ZyskWlasnyMC
                # ZyskWlasnyMC = RataDocelowa - Koszty
                # Zatem: (M / (1-M)) * Podstawa = RataDocelowa - Koszty
                # (M / (1-M)) = (RataDocelowa - Koszty) / Podstawa
                # Niech Z = (RataDocelowa - Koszty) / Podstawa
                # M / (1-M) = Z
                # M = Z - Z*M
                # M + Z*M = Z
                # M(1+Z) = Z
                # M = Z / (1+Z)

                if podstawa > 0:
                    zysk_wlasny_mc = exact_price - koszty
                    z = zysk_wlasny_mc / podstawa
                    if 1 + z != 0:
                        marza_wymagana = z / (1 + z)

                        # Ograniczenia bezpieczeństwa
                        marza_wymagana = max(min(marza_wymagana, 0.9999), -0.5)

                        # Nadpisujemy marżę w danych wejściowych
                        self.data.pricing_margin_pct = marza_wymagana * 100

                        # Drugi przebieg - generujemy finałową macierz z nową marżą
                        engine_pass_2 = LTRKalkulator(
                            input_data=self.data, settings=self.settings
                        )
                        return engine_pass_2.build_matrix()

        return matrix

    def print_terminal_trace(self, matrix_cells: List[Dict[str, Any]]) -> None:
        """Pociesza debugger konsolowy wydrukami logiki śladowej."""
        print("\n\n" + "=" * 60)
        print(" [DEBUG] TRYB DEBUGOWANIA: NOWE PRZELICZENIE (TRACE) (VIA SERVICE)")
        print("=" * 60)
        try:
            for cell in matrix_cells:
                if isinstance(cell, dict) and cell.get("code") == "OPONY":
                    opony_trace = cell.get("details", {}).get("trace", [])
                    print("\n[OPONY] - ŚLAD REWIZYJNY:")
                    for idx, t in enumerate(opony_trace):
                        print(f"  [{idx + 1}] {t.get('krok')}")
                        print(f"      = {t.get('wynik')} PLN")

                if isinstance(cell, dict) and cell.get("code") == "WR":
                    wr_trace = cell.get("details", {}).get("trace", [])
                    print("\n[UTRATA WARTOŚCI] - ŚLAD REWIZYJNY:")
                    for idx, t in enumerate(wr_trace):
                        print(f"  [{idx + 1}] {t.get('krok')}")
                        print(f"      (Obliczenia: {t.get('rownanie')})")
                        print(f"      = {t.get('wynik')} PLN")

        except Exception as deb_err:
            print(f"Błąd debuggera trace'ów: {deb_err}")

        print("=" * 60 + "\n\n")

    def generate_single_trace(self) -> tuple[List[Dict[str, Any]], List[Any]]:
        """Zwraca pelna macierz i wyodrebniony docelowy slajd calculation_trace z LTRKalkulatora"""
        matrix_cells = self.calculate_matrix()
        req_months = int(getattr(self.data, "okres_bazowy", 48) or 48)
        req_total_km = int(getattr(self.data, "przebieg_bazowy", 140000) or 140000)

        trace_data = []
        for cell in matrix_cells:
            if (
                cell.get("Okres") == req_months
                and cell.get("PrzebiegKontrakt") == req_total_km
            ):
                trace_data = cell.get("calculation_trace", [])
                break

        if not trace_data:
            for cell in matrix_cells:
                if cell.get("Okres") == req_months:
                    trace_data = cell.get("calculation_trace", [])
                    break

        if not trace_data and matrix_cells:
            trace_data = matrix_cells[-1].get("calculation_trace", [])

        return matrix_cells, trace_data
