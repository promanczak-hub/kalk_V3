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

        engine = LTRKalkulator(input_data=self.data, settings=self.settings)
        return engine.build_matrix()

    def print_terminal_trace(self, matrix_cells: List[Dict[str, Any]]) -> None:
        """Pociesza debugger konsolowy wydrukami logiki śladowej."""
        print("\n\n" + "=" * 60)
        print(" 🔍 TRYB DEBUGOWANIA: NOWE PRZELICZENIE (TRACE) (VIA SERVICE)")
        print("=" * 60)
        try:
            for cell in matrix_cells:
                if isinstance(cell, dict) and cell.get("code") == "OPONY":
                    opony_trace = cell.get("details", {}).get("trace", [])
                    print("\n[🚜 OPONY] - ŚLAD REWIZYJNY:")
                    for idx, t in enumerate(opony_trace):
                        print(f"  [{idx + 1}] {t.get('krok')}")
                        print(f"      = {t.get('wynik')} PLN")

                if isinstance(cell, dict) and cell.get("code") == "WR":
                    wr_trace = cell.get("details", {}).get("trace", [])
                    print("\n[📉 UTRATA WARTOŚCI] - ŚLAD REWIZYJNY:")
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
