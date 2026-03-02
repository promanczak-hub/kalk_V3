import sys
import unittest
from unittest.mock import MagicMock, patch

import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.service import ServiceCalculator, ServiceCalculatorInput


class TestServiceCalculator(unittest.TestCase):
    def setUp(self):
        # Default input for testing
        self.default_input = ServiceCalculatorInput(
            z_serwisem=True,
            opcja_serwisowa="ASO",
            pakiet_serwisowy=0.0,
            inne_koszty_serwisowania_netto=0.0,
            samar_class_id=2,
            engine_type_id=1,
            power_kw=110.0,
            przebieg=60000,
            okres=36,
        )

    def test_z_serwisem_false_returns_zero(self):
        self.default_input.z_serwisem = False
        calc = ServiceCalculator(self.default_input)
        result = calc.calculate()
        self.assertEqual(result, 0.0)

    def test_pakiet_serwisowy_override(self):
        self.default_input.pakiet_serwisowy = 3600.0  # Total 3600
        calc = ServiceCalculator(self.default_input)
        # Should return 3600 / 36 = 100 per month
        result = calc.calculate()
        self.assertEqual(result, 100.0)

    def test_pakiet_serwisowy_z_innymi_kosztami(self):
        self.default_input.pakiet_serwisowy = 3600.0
        self.default_input.inne_koszty_serwisowania_netto = 720.0
        calc = ServiceCalculator(self.default_input)
        # Should return (3600 + 720) / 36 = 120 per month
        result = calc.calculate()
        self.assertEqual(result, 120.0)

    @patch("core.service.ServiceCalculator._fetch_rate_from_db")
    def test_standard_mileage_aso(self, mock_fetch):
        # We simulate the _fetch_rate_from_db setting _rate_per_km
        def side_effect():
            calc._rate_per_km = 0.10  # 10 groszy za km

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        # 60,000 km * 0.10 = 6,000 PLN. 6000 / 36 months = 166.666...
        result = calc.calculate()

        # Checking floating point proximity
        self.assertAlmostEqual(result, 6000 / 36, places=2)

    @patch("core.service.ServiceCalculator._fetch_rate_from_db")
    def test_standard_mileage_non_aso(self, mock_fetch):
        self.default_input.opcja_serwisowa = "NON-ASO"

        def side_effect():
            calc._rate_per_km = 0.05  # 5 groszy za km

        mock_fetch.side_effect = side_effect

        calc = ServiceCalculator(self.default_input)
        # 60,000 km * 0.05 = 3,000. 3000 / 36 = 83.333...
        result = calc.calculate()

        self.assertAlmostEqual(result, 3000 / 36, places=2)

    def test_power_band_determination(self):
        calc = ServiceCalculator(self.default_input)

        calc.data.power_kw = 90
        self.assertEqual(calc._determine_power_band(), "LOW")

        calc.data.power_kw = 120
        self.assertEqual(calc._determine_power_band(), "MID")

        calc.data.power_kw = 200
        self.assertEqual(calc._determine_power_band(), "HIGH")


if __name__ == "__main__":
    unittest.main()
