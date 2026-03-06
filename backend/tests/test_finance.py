"""Legacy test updated for new FinanseCalculator API."""

from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput


def test_finance_pmt_calculation() -> None:
    """Basic PMT calculation with V1-parity formula."""
    finance_input = FinanseInput(
        WartoscPoczatkowaNetto=100_000.0,
        WrPrzewidywanaCenaSprzedazy=50_000.0,
        CzynszInicjalny=0.0,
        CzynszProcent=0.0,
        RodzajCzynszu="Kwotowo",
        StawkaVAT=1.23,
        Okres=36,
        WIBORProcent=4.82,
        MarzaFinansowaProcent=2.20,
    )

    calc = FinanseCalculator(finance_input)
    result = calc.calculate()

    assert result.monthly_pmt_z_czynszem > 0.0
    assert result.SumaOdsetekZczynszem > 0.0
    # When czynsz=0, both variants should be identical
    assert abs(result.SumaOdsetekZczynszem - result.SumaOdsetekBEZczynszu) < 0.01
