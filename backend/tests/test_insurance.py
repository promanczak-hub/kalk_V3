import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator


class MockSettings:
    ins_theft_doub_pct = 0.0
    ins_driving_school_doub_pct = 0.0
    ins_avg_damage_value = 1500.0
    ins_avg_damage_mileage = 30000.0


def test_insurance_basic_one_year():
    settings = MockSettings()
    
    insurance_rates = [
        {"KolejnyRok": 1, "StawkaBazowaAC": 0.015, "SkladkaOC": 1496.0}
    ]
    damage_coefficients = {
        "WspSredniPrzebieg": 1.0,
        "WspWartoscSzkody": 1.0,
    }
    
    # 1 rok wynajmu, 100k netto auto
    # AC = 1.5%, OC = 1496
    # Amortyzacja miesięczna = 0.98% (0.0098)
    
    calc = InsuranceCalculator(
        insurance_rates=insurance_rates,
        damage_coefficients=damage_coefficients,
        settings=settings,
        amortization_pct=0.0098,
        total_km=20000
    )
    result = calc.calculate_cost(months=12, base_price=100000.0)

    # ROK 1 (deprecjacja 0 miesięcy, bo r-1 = 0):
    # Postawa AC = 100 000 * (1 - 0) = 100 000
    # AC roczne = 100 000 * 1.5% = 1500
    # OC roczne = 1496
    # Szkoda roczna dla 20k km = 1500 * (20000 / 30000) = 1000
    # Razem = 1500 + 1496 + 1000 = 3996
    assert result["total_insurance"] == 3996.0
    assert result["monthly_insurance"] == 3996.0 / 12


def test_insurance_loop_years_and_depreciation():
    settings = MockSettings()
    
    insurance_rates = [
        {"KolejnyRok": 1, "StawkaBazowaAC": 0.015, "SkladkaOC": 1496.0},
        {"KolejnyRok": 2, "StawkaBazowaAC": 0.015, "SkladkaOC": 1496.0}
    ]
    damage_coefficients = {
        "WspSredniPrzebieg": 0.0,
        "WspWartoscSzkody": 0.0,
    }
    
    calc = InsuranceCalculator(
        insurance_rates=insurance_rates,
        damage_coefficients=damage_coefficients,
        settings=settings,
        amortization_pct=0.0098,
        total_km=40000
    )
    result = calc.calculate_cost(months=24, base_price=100000.0)

    # ROK 1: AC=1500, OC=1496 => 2996. Szkody=0
    # ROK 2: amortyzacja 12 * 0.0098 = 0.1176 => podstawa 88240 => AC 1323.6 => Razem 2819.6
    # Suma: 5815.6

    assert round(result["total_insurance"], 2) == 5815.60
    assert round(result["monthly_insurance"], 2) == round(5815.60 / 24, 2)
