"""Tests for core.price_parser — Polish price string parsing."""

import pytest

from core.price_parser import ParsedPrice, parse_price_string


class TestParseBasicFormats:
    """Typical formats found in Polish vehicle offers."""

    def test_space_separated_with_currency_and_tax(self) -> None:
        result = parse_price_string("295 700 PLN brutto")
        assert result is not None
        assert result.value == 295_700.0
        assert result.currency == "PLN"
        assert result.tax_type == "brutto"

    def test_space_separated_netto(self) -> None:
        result = parse_price_string("120 500 PLN netto")
        assert result is not None
        assert result.value == 120_500.0
        assert result.tax_type == "netto"

    def test_dot_as_thousands_separator(self) -> None:
        """Polish convention: 5.476 = five thousand four hundred seventy six."""
        result = parse_price_string("5.476 PLN")
        assert result is not None
        assert result.value == 5_476.0

    def test_dot_and_comma_polish_format(self) -> None:
        """120.500,00 PLN → 120500.00"""
        result = parse_price_string("120.500,00 PLN netto")
        assert result is not None
        assert result.value == 120_500.0
        assert result.tax_type == "netto"

    def test_plain_integer(self) -> None:
        result = parse_price_string("180000")
        assert result is not None
        assert result.value == 180_000.0

    def test_plain_integer_with_currency(self) -> None:
        result = parse_price_string("180000 PLN")
        assert result is not None
        assert result.value == 180_000.0

    def test_comma_as_decimal_separator(self) -> None:
        result = parse_price_string("1234,50 PLN")
        assert result is not None
        assert result.value == 1234.50

    def test_multiple_dots_as_thousands(self) -> None:
        result = parse_price_string("1.234.567 PLN brutto")
        assert result is not None
        assert result.value == 1_234_567.0

    def test_international_format(self) -> None:
        """120,500.00 → commas are thousands."""
        result = parse_price_string("120,500.00 PLN")
        assert result is not None
        assert result.value == 120_500.0


class TestEmptyAndInvalid:
    """Edge cases for empty, null, and garbage inputs."""

    def test_none_input(self) -> None:
        assert parse_price_string(None) is None

    def test_empty_string(self) -> None:
        assert parse_price_string("") is None

    def test_brak(self) -> None:
        assert parse_price_string("Brak") is None

    def test_brak_lowercase(self) -> None:
        assert parse_price_string("brak") is None

    def test_dash(self) -> None:
        assert parse_price_string("-") is None

    def test_em_dash(self) -> None:
        assert parse_price_string("—") is None

    def test_none_string(self) -> None:
        assert parse_price_string("None") is None

    def test_null_string(self) -> None:
        assert parse_price_string("null") is None

    def test_zero_string(self) -> None:
        assert parse_price_string("0") is None

    def test_garbage_text(self) -> None:
        assert parse_price_string("abcdef xyz") is None


class TestCurrencyDetection:
    """Currency detection from price strings."""

    def test_pln_default(self) -> None:
        result = parse_price_string("100 000")
        assert result is not None
        assert result.currency == "PLN"

    def test_eur(self) -> None:
        result = parse_price_string("50 000 EUR brutto")
        assert result is not None
        assert result.currency == "EUR"

    def test_usd(self) -> None:
        result = parse_price_string("50 000 USD")
        assert result is not None
        assert result.currency == "USD"


class TestParsedPriceConversions:
    """Netto/brutto conversion methods."""

    def test_brutto_to_net(self) -> None:
        price = ParsedPrice(value=123_000.0, currency="PLN", tax_type="brutto")
        assert price.value_net == pytest.approx(100_000.0, abs=1.0)

    def test_netto_to_gross(self) -> None:
        price = ParsedPrice(value=100_000.0, currency="PLN", tax_type="netto")
        assert price.value_gross == pytest.approx(123_000.0, abs=1.0)

    def test_unknown_tax_passthrough(self) -> None:
        price = ParsedPrice(value=100_000.0, currency="PLN", tax_type="unknown")
        assert price.value_net == 100_000.0
        assert price.value_gross == 100_000.0


class TestRealWorldPrices:
    """Prices observed from actual vehicle offers."""

    def test_bmw_base_price(self) -> None:
        result = parse_price_string("218 900 PLN brutto")
        assert result is not None
        assert result.value == 218_900.0

    def test_audi_total_with_dot(self) -> None:
        result = parse_price_string("315.700 PLN brutto")
        assert result is not None
        assert result.value == 315_700.0

    def test_vw_options_price(self) -> None:
        result = parse_price_string("25 300 PLN netto")
        assert result is not None
        assert result.value == 25_300.0

    def test_porsche_high_price(self) -> None:
        result = parse_price_string("1 250 000 PLN brutto")
        assert result is not None
        assert result.value == 1_250_000.0

    def test_paint_price_with_text(self) -> None:
        """Price embedded in description: 'lakier metallic 3500 zł brutto'."""
        result = parse_price_string("3500 zł brutto")
        assert result is not None
        assert result.value == 3500.0
        assert result.tax_type == "brutto"

    def test_unknown_brand_mark_x(self) -> None:
        """Test for unknown future brand — should parse fine."""
        result = parse_price_string("99 000 PLN brutto")
        assert result is not None
        assert result.value == 99_000.0
