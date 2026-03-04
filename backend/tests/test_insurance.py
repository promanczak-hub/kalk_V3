import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator, InsuranceInput


def test_insurance_basic_one_year():
    # 1 rok wynajmu, 100k netto auto
    # OC sztywna kwota 1496 PLN
    # AC = 1.5%
    # Amortyzacja miesięczna = 0.98% (0.0098)
    # Dodatek szkodowy: 100 zł
    # Express płaci: Tak
    # Brak innych dodatków (NNW, ASS, ZK zostały usunięte)
    input_data = InsuranceInput(
        base_price=100000.0,
        months=12,
        ac_rate_pct=1.5,
        oc_rate_annual=1496.0,
        depreciation_rate_pct=0.98,
        add_theft_insurance=False,
        theft_doub_rate_pct=0.0,
        manual_correction_gross=0.0,
        annual_damage_risk=100.0,
        vat_rate=1.23,
        express_pays_insurance=True,
    )

    calc = InsuranceCalculator(input_data)
    result = calc.calculate()

    # ROK 1 (deprecjacja 0 miesięcy, bo r-1 = 0):
    # Postawa AC = 100 000 * (1 - 0) = 100 000
    # AC roczne = 100 000 * 1.5% = 1500
    # OC roczne = 1496
    # Szkoda roczna = 100
    # Razem = 1500 + 1496 + 100 = 3096

    assert result.total_cost_net == 3096.0
    assert result.monthly_cost_net == 3096.0 / 12


def test_insurance_loop_7_years_and_depreciation():
    # Model testowy na udowodnienie pętli 7-letniej, ucinki i spadku wartości.
    # W test-first upewnimy się, że to obsłużone logicznie.
    # Wynajem 24 miesiące. Baza 100k.
    input_data = InsuranceInput(
        base_price=100000.0,
        months=24,
        ac_rate_pct=1.5,
        oc_rate_annual=1496.0,
        depreciation_rate_pct=0.98,
        add_theft_insurance=False,
        theft_doub_rate_pct=0.0,
        manual_correction_gross=0.0,
        annual_damage_risk=0.0,  # ignorujemy na potrzeby wyliczen AC same
        vat_rate=1.23,
        express_pays_insurance=True,
    )

    calc = InsuranceCalculator(input_data)
    result = calc.calculate()

    # ROK 1:
    # Miesięcy minęło: 0. Podstawa AC: 100k.
    # Skladka AC = 1500. Skladka OC = 1496. Razem = 2996

    # ROK 2:
    # Miesięcy minęło: 12.
    # Podstawa naliczania = 100000 * (1 - 12 * 0.0098) = 100000 * (1 - 0.1176) = 100000 * 0.8824 = 88240
    # Skladka AC = 88240 * 1.5% = 1323.6
    # OC = 1496
    # Razem Rok 2 = 1323.6 + 1496 = 2819.6

    # Razem suma za 24 miesiące = 2996 + 2819.6 = 5815.6

    assert round(result.total_cost_net, 2) == 5815.60
    assert round(result.monthly_cost_net, 2) == round(5815.60 / 24, 2)


def test_insurance_when_express_does_not_pay_and_manual_correction():
    # Korekta podawana brutto (np. 1230 PLN), VAT = 1.23 (netto ma być 1000).
    input_data = InsuranceInput(
        base_price=100000.0,
        months=12,
        ac_rate_pct=1.5,
        oc_rate_annual=1496.0,
        depreciation_rate_pct=0.98,
        add_theft_insurance=False,
        theft_doub_rate_pct=0.0,
        manual_correction_gross=1230.0,
        annual_damage_risk=0.0,
        vat_rate=1.23,
        express_pays_insurance=False,
    )

    calc = InsuranceCalculator(input_data)
    result = calc.calculate()

    # Operacyjny zwrot ma wynieść 0, bo express nie placi.
    assert result.total_cost_net == 0.0

    # Ale w tle uncharged powinno pokazac co by było (baza 2996 + korekta 1000 = 3996)
    assert round(result.uncharged_total, 2) == 3996.0
