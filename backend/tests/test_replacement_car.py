import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator


def test_replacement_car_disabled():
    """Test that if flag is disabled, the cost is 0."""
    rate_data = {"average_days_per_year": 6.5, "daily_rate_net": 100.0}
    calc = ReplacementCarCalculator(rate_data)
    res = calc.calculate_cost(months=36, enabled=False)

    assert res["total_replacement_car"] == 0.0
    assert res["monthly_replacement_car"] == 0.0


def test_replacement_car_enabled_no_data():
    """Test when enabled, but no rate data available."""
    calc = ReplacementCarCalculator({})
    res = calc.calculate_cost(months=36, enabled=True)

    assert res["total_replacement_car"] == 0.0
    assert res["monthly_replacement_car"] == 0.0


def test_replacement_car_enabled_valid_data():
    """Test when average days and daily rates are mapped."""
    rate_data = {"average_days_per_year": 6.5, "daily_rate_net": 100.0}
    calc = ReplacementCarCalculator(rate_data)

    # 36 months = 3 years
    # Total days = 6.5 * 3 = 19.5 days
    # Total cost = 19.5 days * 100.0 PLN = 1950.0 PLN
    # Monthly cost = 1950.0 / 36 = 54.17 PLN
    res = calc.calculate_cost(months=36, enabled=True)

    assert res["total_replacement_car"] == 1950.0
    assert res["monthly_replacement_car"] == 54.17


def test_replacement_car_legacy_keys():
    """Test with legacy ltr_admin_stawka_zastepczy key names."""
    rate_data = {"SredniaIloscDobWRoku": 4, "DobaNetto": 150.0}
    calc = ReplacementCarCalculator(rate_data)

    # 48 months = 4 years
    # Total days = 4 * 4 = 16 days
    # Total cost = 16 * 150 = 2400 PLN
    # Monthly cost = 2400 / 48 = 50.0 PLN
    res = calc.calculate_cost(months=48, enabled=True)

    assert res["total_replacement_car"] == 2400.0
    assert res["monthly_replacement_car"] == 50.0


def test_replacement_car_zero_months():
    """Test edge case with 0 months."""
    rate_data = {"average_days_per_year": 6.5, "daily_rate_net": 100.0}
    calc = ReplacementCarCalculator(rate_data)
    res = calc.calculate_cost(months=0, enabled=True)

    assert res["total_replacement_car"] == 0.0
    assert res["monthly_replacement_car"] == 0.0
