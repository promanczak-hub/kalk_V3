"""Tests for _extract_from_pages() — pages-based digital twin backfill.

Validates that the deterministic extraction function correctly parses
pricing, technical data, equipment, wheels, emissions, color, body_style,
and powertrain from a pages-based digital_twin structure.
"""

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


# ─── VW Crafter Furgon fixture (commercial vehicle format) ───

PAGES_VW_CRAFTER: list[dict] = [
    {
        "page_number": 1,
        "content": [
            {
                "type": "section",
                "title": "SAMOCHÓD Z WYPOSAŻENIEM",
                "content": [
                    {
                        "type": "pricing_summary",
                        "items": [
                            {
                                "label": "Łącznie",
                                "total": "252 520,00 PLN netto",
                                "category": "Cena katalogowa",
                                "details": [
                                    {
                                        "item": "Samochód bazowy",
                                        "price": "204 090,00 PLN netto",
                                    },
                                    {
                                        "item": "Wyposażenie dodatkowe, opcje wykończenia oraz usługi",
                                        "price": "48 430,00 PLN netto",
                                    },
                                ],
                            },
                            {
                                "price": "90 907,20 PLN netto",
                                "category": "Rabat",
                            },
                            {
                                "price": "161 612,80 PLN netto",
                                "category": "Cena samochodu bazowego z wyposażeniem dodatkowym po obniżce",
                            },
                        ],
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
                "title": "WYBRANE ELEMENTY WYPOSAŻENIA STANDARDOWEGO",
                "subsections": [
                    {
                        "title": "Nadwozie",
                        "items": [
                            "Plandeka",
                            "Zamek centralny",
                        ],
                    },
                    {
                        "title": "Podwozie / Koła",
                        "items": [
                            "16-calowe felgi stalowe",
                        ],
                    },
                ],
            },
        ],
    },
    {
        "page_number": 6,
        "content": [
            {
                "type": "section",
                "title": "WYPOSAŻENIE DODATKOWE",
                "content": [
                    {
                        "type": "options_table",
                        "items": [
                            {
                                "name": "Klimatyzacja automatyczna Climatronic",
                                "price": "10 920,00 PLN",
                            },
                            {"name": "Tempomat", "price": "1 150,00 PLN"},
                        ],
                    },
                ],
            },
            {
                "type": "section",
                "title": "OPCJE WYKOŃCZENIA",
                "content": [
                    {
                        "type": "finishes_table",
                        "headers": ["Kolor samochodu", "Wnętrze"],
                        "rows": [
                            [
                                {"name": "Biały Candy White", "price": "0,00"},
                                {"name": "Czarny Titan"},
                            ],
                        ],
                    },
                ],
            },
        ],
    },
    {
        "page_number": 7,
        "content": [
            {
                "type": "section",
                "title": "DANE TECHNICZNE SAMOCHODU",
                "subsections": [
                    {
                        "title": "WLTP Emisja CO2",
                        "data": [{"label": "Cykl mieszany", "value": "263 g/km"}],
                    },
                    {
                        "title": "WLTP Zużycie paliwa",
                        "data": [{"label": "Cykl mieszany", "value": "10 l/100km"}],
                    },
                    {
                        "title": "Silnik",
                        "data": [
                            {
                                "label": "Liczba i układ cylindrów",
                                "value": "4; in Reihe",
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "page_number": 8,
        "content": [
            {
                "type": "section",
                "title": "Siedzenia",
                "data": [{"label": "Liczba siedzeń", "value": "3"}],
            },
        ],
    },
]


class TestExtractFromPagesVWCommercial:
    """Tests for VW commercial vehicle format parsing."""

    def test_pricing_from_items_details(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        assert "204 090,00" in result["base_price"]
        assert "48 430,00" in result["options_price"]

    def test_total_price_from_category(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        assert "252 520,00" in result.get("total_price", "")

    def test_tech_data_from_subsections(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        assert "263" in result.get("emissions", "")

    def test_fuel_consumption_from_subsections(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        assert "10" in result.get("fuel_consumption", "")

    def test_cylinders_from_subsections(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        assert "4" in result.get("cylinders", "")

    def test_seats_from_section_data(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        assert result["number_of_seats"] == "3"

    def test_exterior_color_from_finishes_table(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        assert "Biały Candy White" in result["exterior_color"]

    def test_standard_equipment_from_subsections(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        std = result["standard_equipment"]
        assert isinstance(std, list)
        assert len(std) == 3
        assert "Plandeka" in std
        assert "Zamek centralny" in std
        assert "16-calowe felgi stalowe" in std

    def test_paid_options_from_options_table(self) -> None:
        result = _extract_from_pages(PAGES_VW_CRAFTER)
        opts = result["paid_options"]
        assert isinstance(opts, list)
        assert len(opts) == 2
        assert opts[0]["name"] == "Klimatyzacja automatyczna Climatronic"

    def test_unknown_commercial_brand_no_crash(self) -> None:
        pages = [
            {
                "page_number": 1,
                "content": [
                    {
                        "type": "section",
                        "title": "MARKA_X SPECIAL",
                        "subsections": [
                            {"data": [{"label": "Weight", "value": "3500 kg"}]}
                        ],
                    },
                ],
            },
        ]
        result = _extract_from_pages(pages)
        assert isinstance(result, dict)
