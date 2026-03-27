import sys
import os
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator


def test_replacement_car_disabled():
    """Test that if flag is disabled, the cost is 0."""
    rate_data = {"srednia_l_dni_rok": 6.5, "stawka_dzienna_netto_zl": 100.0}
    calc = ReplacementCarCalculator(rate_data)
    res = calc.calculate_cost(months=36, enabled=False)

    assert res["total_replacement_car"] == 0.0
    assert res["monthly_replacement_car"] == 0.0


def test_replacement_car_enabled_no_data():
    """Kalkulator MUSI rzucić ValueError gdy uaktywniony, ale brak danych stawek."""
    calc = ReplacementCarCalculator({})
    with pytest.raises(ValueError, match="Koszty samochodu zastępczego uaktywnione"):
        calc.calculate_cost(months=36, enabled=True)


def test_replacement_car_enabled_valid_data():
    """Test when average days and daily rates are mapped."""
    rate_data = {"srednia_l_dni_rok": 6.5, "stawka_dzienna_netto_zl": 100.0}
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
    rate_data = {"srednia_l_dni_rok": 4, "stawka_dzienna_netto_zl": 150.0}
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
    rate_data = {"srednia_l_dni_rok": 6.5, "stawka_dzienna_netto_zl": 100.0}
    calc = ReplacementCarCalculator(rate_data)
    res = calc.calculate_cost(months=0, enabled=True)

    assert res["total_replacement_car"] == 0.0
    assert res["monthly_replacement_car"] == 0.0
