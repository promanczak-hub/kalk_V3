import sys
import unittest
from unittest.mock import patch

import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput


class TestServiceCalculator(unittest.TestCase):
    def setUp(self) -> None:
        # przebieg=120000 > floor(2916*36=104976) -> effective = 120000
        self.default_input = ServiceCalculatorInput(
            z_serwisem=True,
            opcja_serwisowa="ASO",
            pakiet_serwisowy=0.0,
            inne_koszty_serwisowania_netto=0.0,
            samar_class_id=2,
            brand_normalized="SKODA",
            fuel_type="DIESEL",
            drive_type="2WD",
            gearbox_type="AUTOMATYCZNA",
            przebieg=120000,
            okres=36,
        )

    @staticmethod
    def _monthly(result: dict) -> float:
        return float(result["monthly_service"])

    def test_z_serwisem_false_returns_zero(self) -> None:
        self.default_input.z_serwisem = False
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        self.assertEqual(self._monthly(result), 0.0)

    def test_okres_zero_returns_zero(self) -> None:
        self.default_input.okres = 0
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        self.assertEqual(self._monthly(result), 0.0)

    # --- PakietSerwisowy override ---

    def test_pakiet_serwisowy_override(self) -> None:
        """When PakietSerwisowy > 0, it overrides km-based logic."""
        self.default_input.pakiet_serwisowy = 3600.0  # total for contract
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        # 3600 / 36 months = 100.0 /month
        self.assertEqual(self._monthly(result), 100.0)

    def test_pakiet_serwisowy_z_innymi_kosztami(self) -> None:
        """PakietSerwisowy + InneKoszty are summed."""
        self.default_input.pakiet_serwisowy = 3600.0
        self.default_input.inne_koszty_serwisowania_netto = 20.0  # 20 PLN/month
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        # 3600/36 + 20 = 120.0
        self.assertEqual(self._monthly(result), 120.0)

    # --- Km-based logic ---

    @patch(
        "core.LTRSubCalculatorSerwisNew.ServiceCalculator._calculate_progressive_service_total"
    )
    def test_standard_mileage_aso(self, mock_fetch: unittest.mock.MagicMock) -> None:
        """Standard km-based logic with ASO."""

        def side_effect(effective_km: int, trace: list) -> float:
            return 12000.0  # mock 120k * 0.10

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        # 120,000 km * 0.10 = 12,000 PLN. 12000 / 36 months ~= 333.33
        self.assertAlmostEqual(self._monthly(result), 12000 / 36, places=2)

    @patch(
        "core.LTRSubCalculatorSerwisNew.ServiceCalculator._calculate_progressive_service_total"
    )
    def test_standard_mileage_non_aso(
        self, mock_fetch: unittest.mock.MagicMock
    ) -> None:
        """Standard km-based logic with NON-ASO."""
        self.default_input.opcja_serwisowa = "NON-ASO"

        def side_effect(effective_km: int, trace: list) -> float:
            return 6000.0

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        # 120,000 km * 0.05 = 6,000. 6000 / 36 ~= 166.67
        self.assertAlmostEqual(self._monthly(result), 6000 / 36, places=2)

    # --- Inne Koszty Serwisowania ---

    @patch(
        "core.LTRSubCalculatorSerwisNew.ServiceCalculator._calculate_progressive_service_total"
    )
    def test_inne_koszty_dodane_do_km(
        self, mock_fetch: unittest.mock.MagicMock
    ) -> None:
        """InneKoszty are added on top of km-based result."""

        def side_effect(effective_km: int, trace: list) -> float:
            return 12000.0

        mock_fetch.side_effect = side_effect
        self.default_input.inne_koszty_serwisowania_netto = 50.0  # 50 PLN/month

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        # 12000/36 + 50 = 383.33
        expected = 12000 / 36 + 50.0
        self.assertAlmostEqual(self._monthly(result), expected, places=2)

    def test_fake_brand_multiplier_fail_fast(self) -> None:
        """`get_service_multiplier` musi być fail-fast dla nieznanej marki (no silent 1.0 fallback).

        Historia: poprzedni test oczekiwał `multiplier == 1.0` ("Rule 4 — fake
        marka nie wyrzuca wyjątku"). Production *od dawna* raise'uje ValueError
        gdy w `samar_service_brand_multipliers` brakuje wiersza dla brand_normalized
        i brakuje POZOSTAŁE fallback. To celowe — wykrywa data-quality issues
        zamiast cicho liczyć dalej z mnożnikiem 1.0.

        Memory note `feedback_service_multipliers_neutral` mówi że W PRODUKCJI
        mnożniki są trzymane na 1.0 (różnicowanie w base rate) — ale to o
        wartościach w DB, nie o silent fallback gdy wiersz brakuje.
        """
        from core.LTRSubCalculatorSerwisNew import get_service_multiplier

        with self.assertRaises(ValueError):
            get_service_multiplier(
                "samar_service_brand_multipliers",
                "brand_normalized",
                "MarkaX_Zmyslona",
            )

    # --- Floor normatywny ---

    @patch(
        "core.LTRSubCalculatorSerwisNew.ServiceCalculator._calculate_progressive_service_total"
    )
    def test_floor_normatywny_applied(
        self, mock_fetch: unittest.mock.MagicMock
    ) -> None:
        """When mileage is below normative floor, floor is used."""
        self.default_input.przebieg = 10000
        self.default_input.normatywny_przebieg_mc = 2916  # 2916 * 36 = 104,976 km
        self.default_input.okres = 36

        def side_effect(effective_km: int, trace: list) -> float:
            # 2916 * 36 is ~104976. Returns 104976 * 0.10
            return 104976 * 0.10

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        floor_km = 2916 * 36
        expected = floor_km * 0.10 / 36
        self.assertAlmostEqual(self._monthly(result), expected, places=2)


if __name__ == "__main__":
    unittest.main()
