from core.LTRSubCalculatorFinanse import FinanceCalculator, FinanceInput


def test_finance_pmt_calculation():
    # Dane ze zrzutu użytkownika: Wibor 4.82%, Marża 2.2%
    # Przykładowe dane dla weryfikacji PMT V1
    capex = 100000.0
    upfront_pct = 0.0  # 0% wpłaty własnej
    rv_net = 50000.0  # Wartość rezydualna z 100k
    months = 36
    wibor_pct = 4.82
    margin_pct = 2.20

    finance_input = FinanceInput(
        total_capex=capex,
        upfront_pct=upfront_pct,
        rv_net=rv_net,
        months=months,
        wibor_pct=wibor_pct,
        margin_pct=margin_pct,
    )

    calculator = FinanceCalculator(finance_input)
    result = calculator.calculate()

    # Matematyka kontrolna dla PMT V1:
    # rate = (4.82 + 2.20) / 100 / 12 = 0.00585
    # pv = 100000
    # fv = 50000
    # PMT = (0.00585 * (100000 - 50000 / ((1 + 0.00585)**36))) / (1 - (1 + 0.00585)**-36)
    # PMT ~ 1930.34

    assert result.monthly_pmt_net > 0.0
    expected = 1930.34
    actual = round(result.monthly_pmt_net, 2)
    assert actual == expected, f"Oczekiwano {expected}, a otrzymano {actual}"
    assert result.total_pmt_cost == round(result.monthly_pmt_net * 36, 2)
