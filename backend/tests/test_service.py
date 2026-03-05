import sys
import unittest
from unittest.mock import patch

import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput


class TestServiceCalculator(unittest.TestCase):
    def setUp(self) -> None:
        # przebieg=120000 > floor(2916*36=104976) → effective = 120000
        self.default_input = ServiceCalculatorInput(
            z_serwisem=True,
            opcja_serwisowa="ASO",
            pakiet_serwisowy=0.0,
            inne_koszty_serwisowania_netto=0.0,
            samar_class_id=2,
            engine_type_id=1,
            power_kw=110.0,
            przebieg=120000,
            okres=36,
        )

    def test_z_serwisem_false_returns_zero(self) -> None:
        self.default_input.z_serwisem = False
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        self.assertEqual(result, 0.0)

    def test_okres_zero_returns_zero(self) -> None:
        self.default_input.okres = 0
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        self.assertEqual(result, 0.0)

    # --- PakietSerwisowy override ---

    def test_pakiet_serwisowy_override(self) -> None:
        """Gdy PakietSerwisowy > 0, zastępuje logikę km-ową."""
        self.default_input.pakiet_serwisowy = 3600.0  # Total 3600 na kontrakt
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        # 3600 / 36 mc = 100.0 /mc
        self.assertEqual(result, 100.0)

    def test_pakiet_serwisowy_z_innymi_kosztami(self) -> None:
        """PakietSerwisowy + InneKoszty = oba się sumują."""
        self.default_input.pakiet_serwisowy = 3600.0
        self.default_input.inne_koszty_serwisowania_netto = 20.0  # 20 zł/mc
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        # 3600/36 + 20 = 100 + 20 = 120.0
        self.assertEqual(result, 120.0)

    # --- Logika km-owa ---

    @patch("core.LTRSubCalculatorSerwisNew.ServiceCalculator._fetch_rate_from_db")
    def test_standard_mileage_aso(self, mock_fetch: unittest.mock.MagicMock) -> None:
        """Standardowa logika km-owa z ASO."""

        def side_effect() -> None:
            calc._rate_per_km = 0.10

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        # 120,000 km * 0.10 = 12,000 PLN. 12000 / 36 months ≈ 333.33
        self.assertAlmostEqual(result, 12000 / 36, places=2)

    @patch("core.LTRSubCalculatorSerwisNew.ServiceCalculator._fetch_rate_from_db")
    def test_standard_mileage_non_aso(
        self, mock_fetch: unittest.mock.MagicMock
    ) -> None:
        """Standardowa logika km-owa z NON-ASO."""
        self.default_input.opcja_serwisowa = "NON-ASO"

        def side_effect() -> None:
            calc._rate_per_km = 0.05

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        # 120,000 km * 0.05 = 6,000. 6000 / 36 ≈ 166.67
        self.assertAlmostEqual(result, 6000 / 36, places=2)

    # --- Inne Koszty Serwisowania ---

    @patch("core.LTRSubCalculatorSerwisNew.ServiceCalculator._fetch_rate_from_db")
    def test_inne_koszty_dodane_do_km(
        self, mock_fetch: unittest.mock.MagicMock
    ) -> None:
        """InneKoszty doliczane do wyniku km-owego."""

        def side_effect() -> None:
            calc._rate_per_km = 0.10

        mock_fetch.side_effect = side_effect
        self.default_input.inne_koszty_serwisowania_netto = 50.0  # 50 zł/mc

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        # 12000/36 + 50 = 333.33 + 50 = 383.33
        expected = 12000 / 36 + 50.0
        self.assertAlmostEqual(result, expected, places=2)

    # --- Power band ---

    def test_power_band_determination(self) -> None:
        calc = ServiceCalculator(self.default_input)

        calc.data.power_kw = 90
        self.assertEqual(calc._determine_power_band(), "LOW")

        calc.data.power_kw = 120
        self.assertEqual(calc._determine_power_band(), "MID")

        calc.data.power_kw = 200
        self.assertEqual(calc._determine_power_band(), "HIGH")

    # --- Floor normatywny ---

    @patch("core.LTRSubCalculatorSerwisNew.ServiceCalculator._fetch_rate_from_db")
    def test_floor_normatywny_applied(
        self, mock_fetch: unittest.mock.MagicMock
    ) -> None:
        """Gdy przebieg < floor normatywny, używamy floor."""
        self.default_input.przebieg = 10000  # Bardzo niski przebieg
        self.default_input.normatywny_przebieg_mc = 2916  # = 2916 * 36 = 104 976 km
        self.default_input.okres = 36

        def side_effect() -> None:
            calc._rate_per_km = 0.10

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()

        floor_km = 2916 * 36  # 104976
        expected = floor_km * 0.10 / 36
        self.assertAlmostEqual(result, expected, places=2)


if __name__ == "__main__":
    unittest.main()
