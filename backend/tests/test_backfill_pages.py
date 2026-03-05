"""Tests for _extract_from_pages() — pages-based digital twin backfill.

Validates that the deterministic extraction function correctly parses
pricing, technical data, equipment, wheels, emissions, color, body_style,
and powertrain from a pages-based digital_twin structure.
"""

import pytest
from core.pipeline_card_summary import _extract_from_pages


# ─── Minimal pages fixture modeled after real BMW 320i Touring data ───

PAGES_BMW_320I: list[dict] = [
    {
        "page_number": 1,
        "content": [
            {"type": "offer_header", "title": "OFERTA."},
        ],
    },
    {
        "page_number": 2,
        "content": [
            {
                "type": "section",
                "title": "TWOJA KONFIGURACJA.",
                "vehicle": {
                    "name": "BMW 320i Touring (21FY - 05.03.2026)",
                    "emissions": {
                        "label": "Emisja CO2 (cykl mieszany)",
                        "value": "154 g/km",
                    },
                },
            },
            {
                "type": "pricing_summary",
                "currency": "PLN",
                "price_components": [
                    {"item": "Cena modelu bazowego brutto", "price": "221 500,00"},
                    {"item": "Wyposażenie opcjonalne", "price": "37 200,00"},
                    {"item": "Rabat na model z opcjami", "price": "-77 610,00"},
                    {
                        "item": "Całkowita cena brutto pojazdu",
                        "price": "183 290,00",
                    },
                ],
            },
        ],
    },
    {
        "page_number": 4,
        "content": [
            {
                "type": "section",
                "title": "WYBRANY MODEL.",
                "items": [
                    {
                        "code": "21FY",
                        "name": "BMW 320i Touring",
                        "price": "221 500,00",
                    },
                ],
            },
            {
                "type": "section",
                "title": "STANDARDOWE WYPOSAŻENIE.",
                "items": [
                    {"code": "S02TB", "description": "Sportowa automatyczna skrzynia"},
                    {"code": "S02VB", "description": "System monitorowania ciśnienia"},
                    {"code": "S0302", "description": "System alarmowy"},
                ],
            },
            {
                "type": "section",
                "title": "NADWOZIE.",
                "items": [
                    {"code": "0668", "name": "Szary Skyscraper", "price": "4 800,00"},
                ],
            },
        ],
    },
    {
        "page_number": 5,
        "content": [
            {
                "type": "section",
                "title": "OBRĘCZE",
                "items": [
                    {
                        "code": "S01HX",
                        "name": '18" aluminiowe obręcze M Double-spoke',
                        "price": "0,00",
                    },
                ],
            },
            {
                "type": "section",
                "title": "WYPOSAŻENIE OPCJONALNE.",
                "items": [
                    {"code": "S03AC", "name": "Hak holowniczy", "price": "5 000,00"},
                    {
                        "code": "S0322",
                        "name": "Ogrzewanie kierownicy",
                        "price": "1 500,00",
                    },
                ],
                "total": "37 200,00",
                "currency": "PLN",
            },
        ],
    },
    {
        "page_number": 6,
        "content": [
            {
                "type": "section",
                "title": "INFORMACJE TECHNICZNE.",
                "technical_data_table": [
                    {"label": "Pojemność silnika", "value": "1 998 cm³"},
                    {"label": "Rodzaj paliwa", "value": "Benzyna"},
                    {"label": "Skrzynia biegów", "value": "Automatyczna"},
                    {"label": "Prędkość maksymalna", "value": "230 km/h"},
                ],
                "disclaimers": ["Uwaga 1"],
            },
        ],
    },
]


class TestExtractFromPages:
    """Tests for _extract_from_pages function."""

    def test_pricing_extraction(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        assert "221 500,00" in result["base_price"]
        assert "37 200,00" in result["options_price"]
        assert "183 290,00" in result["total_price"]

    def test_fuel_and_transmission(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        assert result["fuel"] == "Benzyna"
        assert result["transmission"] == "Automatyczna"

    def test_engine_capacity(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        assert result["engine_capacity"] == "1 998 cm³"

    def test_emissions(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        assert "154" in result["emissions"]

    def test_wheels(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        assert result["wheels"] == "18"

    def test_exterior_color(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        assert "Szary Skyscraper" in result["exterior_color"]
        assert "4 800" in result["exterior_color"]

    def test_body_style(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        assert "Touring" in result["body_style"]

    def test_powertrain_constructed(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        powertrain = result["powertrain"]
        assert "1 998 cm³" in powertrain
        assert "Benzyna" in powertrain
        assert "Automatyczna" in powertrain

    def test_standard_equipment(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        std = result["standard_equipment"]
        assert isinstance(std, list)
        assert len(std) == 3
        assert "Sportowa automatyczna skrzynia" in std[0]

    def test_paid_options(self) -> None:
        result = _extract_from_pages(PAGES_BMW_320I)
        opts = result["paid_options"]
        assert isinstance(opts, list)
        assert len(opts) == 2
        assert opts[0]["name"] == "Hak holowniczy"
        assert "5 000,00" in opts[0]["price"]

    def test_empty_pages_returns_empty(self) -> None:
        result = _extract_from_pages([])
        assert result == {}

    def test_unknown_brand_pages_no_crash(self) -> None:
        """Pages with unknown structure should not raise errors."""
        pages = [
            {
                "page_number": 1,
                "content": [
                    {"type": "unknown_type", "data": "something"},
                    {"type": "section", "title": "RANDOM SECTION"},
                ],
            },
        ]
        result = _extract_from_pages(pages)
        assert isinstance(result, dict)

    def test_missing_content_key(self) -> None:
        """Pages without 'content' key should be skipped."""
        pages = [{"page_number": 1}]
        result = _extract_from_pages(pages)
        assert result == {}
