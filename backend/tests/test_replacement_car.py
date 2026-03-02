import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.replacement_car import ReplacementCarCalculator


def test_replacement_car_disabled():
    """Test that if flag is disabled, the cost is 0."""
    calc = ReplacementCarCalculator(samar_class_id=1)  # Class 1
    res = calc.calculate_cost(months=36, enabled=False)

    assert res["total_replacement_car"] == 0.0
    assert res["monthly_replacement_car"] == 0.0


def test_replacement_car_enabled_no_data(mocker):
    """Test when enabled, but the API returns empty rates."""
    # Mocking fetching rates
    mocker.patch.object(ReplacementCarCalculator, "_fetch_rates", return_value=None)

    calc = ReplacementCarCalculator(samar_class_id=999)  # Unknown
    # By default, initialization sets them to 0.0
    res = calc.calculate_cost(months=36, enabled=True)

    assert res["total_replacement_car"] == 0.0
    assert res["monthly_replacement_car"] == 0.0


def test_replacement_car_enabled_valid_data(mocker):
    """Test when average days and daily rates are mapped."""
    calc = ReplacementCarCalculator(samar_class_id=4)  # D class
    # Manually overwrite the rates (mocking the DB fetch)
    calc.average_days_per_year = 6.5
    calc.daily_rate_net = 100.0

    # Let's say we lease for 36 months (3 years)
    # Total days = 6.5 * 3 = 19.5 days
    # Total cost = 19.5 days * 100.0 PLN = 1950.0 PLN
    # Monthly cost = 1950.0 / 36 = 54.17 PLN
    res = calc.calculate_cost(months=36, enabled=True)

    assert res["total_replacement_car"] == 1950.0
    assert res["monthly_replacement_car"] == 54.17
