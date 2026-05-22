"""Tests for the deterministic post-processor that fills card_summary gaps from digital_twin.

Rationale: Gemini 2.5 Flash (`generate_card_summary_from_twin`) historically drops
~80% of optional_equipment / packages / service items from digital_twin → card_summary.
Real-world examples observed 2026-05-19:
- Renault Master izoterma_EX (382fceed): digital_twin has 7 optional_equipment items
  (including "Zabudowa Kontener Izotermiczny" 47970 + "Agregat Zanotti" 37527.30),
  card_summary.paid_options=[], service_equipment=null.
- Toyota Hilux (2b7e9285): digital_twin has 4 optional_equipment items,
  card_summary.paid_options=[].

Deterministic Python beats fuzzy Flash here because the rules ARE deterministic:
- Service-equipment keywords (zabudowa/izoterma/kontener/agregat/...) → service_equipment
- price > 0 and not service → paid_options
- price == 0 → skip (standard)
- vehicle_class derivable from brand+model

IDEMPOTENT: never overwrites a field that Flash already filled — only patches gaps.
"""

from __future__ import annotations

import copy

from core.pipeline_deterministic_normalize import (
    SERVICE_EQUIPMENT_KEYWORDS,
    _km_to_kw,
    _parse_int_from_unit,
    classify_vehicle_class,
    derive_body_style_hint,
    is_service_equipment_name,
    normalize_card_summary_from_digital_twin,
    parse_price_to_float,
    partition_optional_equipment,
)


# ═══════════════════════════════════════════════════════════════════
# parse_price_to_float — robust string→float
# Critical: production digital_twin.optional_equipment[*].price comes as
# STRING ("738.00 zł", "47 970.00 zł"), not float. Bug seen in real DB.
# ═══════════════════════════════════════════════════════════════════


class TestParsePriceToFloat:
    def test_polish_string_with_zl_suffix(self) -> None:
        assert parse_price_to_float("738.00 zł") == 738.0

    def test_polish_string_with_space_thousands(self) -> None:
        assert parse_price_to_float("47 970.00 zł") == 47970.0

    def test_polish_string_with_nbsp_thousands(self) -> None:
        assert parse_price_to_float("47 970,00 zł") == 47970.0

    def test_comma_decimal(self) -> None:
        assert parse_price_to_float("123,50 zł") == 123.5

    def test_polish_thousands_and_comma_decimal(self) -> None:
        # "1.234,56" — dot=thousands, comma=decimal
        assert parse_price_to_float("1.234,56 zł") == 1234.56

    def test_english_thousands_and_decimal(self) -> None:
        # "1,234.56" — comma=thousands, dot=decimal
        assert parse_price_to_float("1,234.56") == 1234.56

    def test_float_passthrough(self) -> None:
        assert parse_price_to_float(738.0) == 738.0

    def test_int_passthrough(self) -> None:
        assert parse_price_to_float(738) == 738.0

    def test_none_returns_zero(self) -> None:
        assert parse_price_to_float(None) == 0.0

    def test_empty_string_returns_zero(self) -> None:
        assert parse_price_to_float("") == 0.0
        assert parse_price_to_float("   ") == 0.0

    def test_unparseable_returns_zero(self) -> None:
        assert parse_price_to_float("brak") == 0.0
        assert parse_price_to_float("abc") == 0.0

    def test_negative_clamped_to_zero(self) -> None:
        # Defensive: negative prices don't make sense in this domain
        assert parse_price_to_float("-100 zł") == 0.0


# ═══════════════════════════════════════════════════════════════════
# is_service_equipment_name
# ═══════════════════════════════════════════════════════════════════


class TestIsServiceEquipmentName:
    def test_zabudowa_kontener_izotermiczny(self) -> None:
        assert is_service_equipment_name("Zabudowa Kontener Izotermiczny")

    def test_agregat_zanotti(self) -> None:
        assert is_service_equipment_name("Agregat Zanotti Z380 + Funkcja Grzania + Zaś230V")

    def test_pakiet_conversion_not_service(self) -> None:
        # "Pakiet Conversion 2" is a Renault factory option, not a body conversion.
        # Tricky case — let "konwersja" pass but generic "pakiet conversion" not.
        # Convention: word "zabudowa/agregat/izoterma/..." must be present.
        assert not is_service_equipment_name("Pakiet Conversion 2 (REXWI EXEXM WRAN2)")

    def test_swiatla_przeciwmglowe_not_service(self) -> None:
        assert not is_service_equipment_name("światła przeciwmgłowe")

    def test_polish_diacritics_chłodnia(self) -> None:
        assert is_service_equipment_name("Chłodnia kompresorowa Carrier")
        assert is_service_equipment_name("Chlodnia kompresorowa")  # ASCII fold

    def test_skrzynia_wywrotka_plandeka(self) -> None:
        assert is_service_equipment_name("Skrzynia ładunkowa aluminiowa")
        assert is_service_equipment_name("Wywrotka 3-stronna")
        assert is_service_equipment_name("Plandeka stelaż + plandeka")

    def test_przeglądy_serwis(self) -> None:
        # Service packages (przeglądy) are different category — they're maintenance,
        # not body modifications. By convention we route both to service_equipment.
        assert is_service_equipment_name("Pakiet Przeglądów PRO+FLASH")
        assert is_service_equipment_name("Pakiet serwisowy 4 lata / 100 000 km")

    def test_empty_or_none(self) -> None:
        assert not is_service_equipment_name("")
        assert not is_service_equipment_name(None)  # type: ignore[arg-type]

    def test_keywords_catalogue(self) -> None:
        # Sanity: catalogue must include the critical phrases observed in real data
        required = ("zabudowa", "izoterm", "kontener", "agregat", "skrzynia", "wywrotka")
        for kw in required:
            assert kw in " | ".join(SERVICE_EQUIPMENT_KEYWORDS).lower(), (
                f"Missing critical keyword: {kw!r}"
            )


# ═══════════════════════════════════════════════════════════════════
# partition_optional_equipment
# ═══════════════════════════════════════════════════════════════════


def _opt(name: str, price: float, code: str | None = None) -> dict:
    item: dict = {"name": name, "price": price}
    if code:
        item["code"] = code
    return item


class TestPartitionOptionalEquipment:
    def test_renault_master_izoterma_split(self) -> None:
        """Reproduces the actual digital_twin.optional_equipment from 382fceed."""
        items = [
            _opt("Pakiet Conversion 2 (REXWI EXEXM WRAN2)", 738.0),
            _opt("światła przeciwmgłowe", 738.0),
            _opt("asystent świateł drogowych", 553.5),
            _opt('16" stalowe z kołpakami mini', 0.0),
            _opt("zderzak przedni częściowo lakierowany", 0.0),
            _opt("Agregat Zanotti Z380 + Funkcja Grzania + Zaś230V", 37527.3),
            _opt("Zabudowa Kontener Izotermiczny", 47970.0),
        ]
        result = partition_optional_equipment(items)
        # Paid factory options: price > 0 and NOT service
        paid_names = [p["name"] for p in result.paid_options]
        assert "Pakiet Conversion 2 (REXWI EXEXM WRAN2)" in paid_names
        assert "światła przeciwmgłowe" in paid_names
        assert "asystent świateł drogowych" in paid_names
        # Standard/free items: price == 0 → skipped
        assert '16" stalowe z kołpakami mini' not in paid_names
        # Service equipment
        service_names = [c["name"] for c in result.service_components]
        assert "Agregat Zanotti Z380 + Funkcja Grzania + Zaś230V" in service_names
        assert "Zabudowa Kontener Izotermiczny" in service_names
        # Totals
        assert result.paid_options_total_gross == 738.0 + 738.0 + 553.5
        assert result.service_total_gross == 37527.3 + 47970.0

    def test_empty_input(self) -> None:
        result = partition_optional_equipment([])
        assert result.paid_options == []
        assert result.service_components == []
        assert result.paid_options_total_gross == 0.0
        assert result.service_total_gross == 0.0

    def test_zero_priced_items_skipped(self) -> None:
        items = [_opt("Standard wheel", 0.0), _opt("Premium leather", 1500.0)]
        result = partition_optional_equipment(items)
        assert len(result.paid_options) == 1
        assert result.paid_options[0]["name"] == "Premium leather"


# ═══════════════════════════════════════════════════════════════════
# classify_vehicle_class
# ═══════════════════════════════════════════════════════════════════


class TestClassifyVehicleClass:
    def test_renault_master_dostawczy(self) -> None:
        assert classify_vehicle_class("Renault", "Master") == "Dostawczy"

    def test_mercedes_sprinter_dostawczy(self) -> None:
        assert classify_vehicle_class("Mercedes-Benz", "Sprinter") == "Dostawczy"

    def test_vw_crafter_dostawczy(self) -> None:
        assert classify_vehicle_class("Volkswagen", "Crafter") == "Dostawczy"

    def test_ford_transit_dostawczy(self) -> None:
        assert classify_vehicle_class("Ford", "Transit") == "Dostawczy"

    def test_skoda_octavia_osobowy(self) -> None:
        assert classify_vehicle_class("Skoda", "Octavia") == "Osobowy"

    def test_bmw_3_osobowy(self) -> None:
        assert classify_vehicle_class("BMW", "Series 3") == "Osobowy"

    def test_toyota_hilux_dostawczy(self) -> None:
        # Pickup → N1 → Dostawczy in our taxonomy
        assert classify_vehicle_class("Toyota", "Hilux") == "Dostawczy"

    def test_vw_amarok_dostawczy(self) -> None:
        assert classify_vehicle_class("Volkswagen", "Amarok") == "Dostawczy"

    def test_case_insensitive(self) -> None:
        assert classify_vehicle_class("RENAULT", "MASTER") == "Dostawczy"
        assert classify_vehicle_class("renault", "master") == "Dostawczy"

    def test_unknown_brand_returns_none(self) -> None:
        # When we can't decide, return None (HITL fills in)
        assert classify_vehicle_class(None, None) is None
        assert classify_vehicle_class("", "") is None


# ═══════════════════════════════════════════════════════════════════
# derive_body_style_hint
# ═══════════════════════════════════════════════════════════════════


class TestDeriveBodyStyleHint:
    def test_master_with_zabudowa_returns_podwozie(self) -> None:
        # Master + zabudowa kontener → "Podwozie" (chassis + body conversion)
        equipment_names = ["Zabudowa Kontener Izotermiczny", "Agregat Zanotti"]
        result = derive_body_style_hint("Renault", "Master", equipment_names)
        assert result == "Podwozie"

    def test_master_no_zabudowa_returns_furgon(self) -> None:
        # Master without service equipment → likely Furgon (panel van)
        equipment_names = ["światła przeciwmgłowe", "asystent świateł drogowych"]
        result = derive_body_style_hint("Renault", "Master", equipment_names)
        assert result == "Furgon"

    def test_hilux_returns_pickup(self) -> None:
        result = derive_body_style_hint("Toyota", "Hilux", [])
        assert result == "Pickup"

    def test_octavia_returns_none(self) -> None:
        # Passenger sedan — we don't pretend to know. HITL fills it.
        result = derive_body_style_hint("Skoda", "Octavia", [])
        # Either "Kombi" by lookup OR None — we accept either since
        # Octavia ships in multiple body styles. Default: None.
        assert result in (None, "Kombi", "Hatchback")

    def test_unknown_model_returns_none(self) -> None:
        assert derive_body_style_hint("UnknownBrand", "UnknownModel", []) is None


# ═══════════════════════════════════════════════════════════════════
# normalize_card_summary_from_digital_twin — INTEGRATION
# ═══════════════════════════════════════════════════════════════════


def _renault_master_digital_twin() -> dict:
    """Replica of the ACTUAL digital_twin payload for 382fceed (Renault Master izoterma).

    Note: prices come as STRINGS ("738.00 zł", "47 970.00 zł") from Gemini Pro,
    not floats. Also: digital_twin.brand/model are null (top-level fallback
    needed). financials is null. These are real-world quirks from the DB row.
    """
    return {
        "brand": None,  # Pro often leaves this null — fallback to top-level
        "model": None,
        "trim_level": None,
        "optional_equipment": [
            {"name": "Pakiet Conversion 2 (REXWI EXEXM WRAN2)", "price": "738.00 zł"},
            {"name": "światła przeciwmgłowe", "price": "738.00 zł"},
            {"name": "asystent świateł drogowych", "price": "553.50 zł"},
            {"name": '16" stalowe z kołpakami mini', "price": "0.00 zł"},
            {"name": "zderzak przedni częściowo lakierowany", "price": "0.00 zł"},
            {"name": "Agregat Zanotti Z380 + Funkcja Grzania + Zaś230V", "price": "37 527.30 zł"},
            {"name": "Zabudowa Kontener Izotermiczny", "price": "47 970.00 zł"},
        ],
        "packages": [],
        "financials": None,  # Pro often returns null
    }


class TestNormalizeCardSummary:
    def test_fills_paid_options_when_empty(self) -> None:
        card: dict = {"paid_options": [], "service_equipment": None}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        # 3 paid options: Pakiet Conversion 2 + 2 świateł items
        assert len(result["paid_options"]) == 3
        names = [p["name"] for p in result["paid_options"]]
        assert "Pakiet Conversion 2 (REXWI EXEXM WRAN2)" in names

    def test_fills_service_equipment_when_null(self) -> None:
        card: dict = {"paid_options": [], "service_equipment": None}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        se = result["service_equipment"]
        assert se is not None
        assert "Zabudowa" in se["name"] or "Agregat" in se["name"] or "Pakiet" in se["name"]
        assert len(se["components"]) == 2  # agregat + zabudowa
        comp_names = [c["name"] for c in se["components"]]
        assert any("Izotermiczny" in n for n in comp_names)
        assert any("Agregat" in n for n in comp_names)

    def test_fills_vehicle_class_when_null(self) -> None:
        card: dict = {"vehicle_class": None}
        twin = _renault_master_digital_twin()
        # Real-world: twin.brand/model are null, but synthesis_data.brand/model
        # exist. Pipeline passes them as fallback.
        result = normalize_card_summary_from_digital_twin(
            card, twin, brand_fallback="RENAULT", model_fallback="Master"
        )
        assert result["vehicle_class"] == "Dostawczy"

    def test_fills_body_style_when_null(self) -> None:
        card: dict = {"body_style": None}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(
            card, twin, brand_fallback="RENAULT", model_fallback="Master"
        )
        # Master + zabudowa → "Podwozie"
        assert result["body_style"] == "Podwozie"

    def test_brand_model_fallback_used_when_twin_null(self) -> None:
        """Real-world: digital_twin.brand=null but synthesis_data.brand='RENAULT'."""
        card: dict = {"vehicle_class": None, "body_style": None}
        twin = _renault_master_digital_twin()
        # WITHOUT fallback — vehicle_class stays None
        no_fallback = normalize_card_summary_from_digital_twin(card, twin)
        assert no_fallback["vehicle_class"] is None
        # WITH fallback — populated
        with_fallback = normalize_card_summary_from_digital_twin(
            card, twin, brand_fallback="RENAULT", model_fallback="Master"
        )
        assert with_fallback["vehicle_class"] == "Dostawczy"

    def test_string_prices_parsed_correctly(self) -> None:
        """Prices come as strings ('47 970.00 zł') in real data — must parse."""
        card: dict = {"paid_options": [], "service_equipment": None}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        # Service equipment total must be > 0 (47970 + 37527.3 = 85497.3)
        se = result["service_equipment"]
        total = se.get("gross_amount") or 0.0
        assert total > 80000, f"service total should be ~85497, got {total}"
        # Paid options total: 738 + 738 + 553.5 = 2029.5
        paid_total = sum(p.get("gross_amount") or 0.0 for p in result["paid_options"])
        assert 2000 < paid_total < 2100, f"paid total should be ~2029, got {paid_total}"

    def test_idempotent_does_not_overwrite_existing_paid_options(self) -> None:
        existing = [{"name": "Flash-provided option", "price": "999 PLN brutto"}]
        card = {"paid_options": existing, "service_equipment": None}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        # paid_options stays as Flash provided
        assert result["paid_options"] == existing

    def test_summary_pair_sets_numeric_total_price_net_gross(self) -> None:
        """When Pro captured the PODSUMOWANIE netto+brutto pair into
        digital_twin.pricing.total_net/.total_gross, normalize surfaces BOTH as
        numeric card_summary.total_price_net/gross so the reconciliation engine
        gets an independent net/gross anchor pair (and can catch a domain flip)."""
        card: dict = {}
        twin = {
            "pricing": {
                "base_price": "167 218,50 zł",
                "total_price": "204 817,14 zł",
                "total_net": "166 518,00",
                "total_gross": "204 817,14",
            }
        }
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["total_price_net"] == 166518.0
        assert result["total_price_gross"] == 204817.14

    def test_summary_pair_idempotent_when_already_set(self) -> None:
        card: dict = {"total_price_net": 99999.0}
        twin = {"pricing": {"total_net": "166 518,00", "total_gross": "204 817,14"}}
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["total_price_net"] == 99999.0  # not overwritten
        assert result["total_price_gross"] == 204817.14  # gross was missing → filled

    def test_idempotent_does_not_overwrite_existing_vehicle_class(self) -> None:
        card = {"vehicle_class": "Osobowy"}  # weird but explicit
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["vehicle_class"] == "Osobowy"  # preserved

    def test_partial_fill_skips_already_present(self) -> None:
        # paid_options already filled, service_equipment empty
        existing_paid = [{"name": "X", "price": "100 PLN brutto"}]
        card = {
            "paid_options": existing_paid,
            "service_equipment": None,
            "vehicle_class": None,
        }
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(
            card, twin, brand_fallback="RENAULT", model_fallback="Master"
        )
        assert result["paid_options"] == existing_paid  # preserved
        assert result["service_equipment"] is not None  # filled
        assert result["vehicle_class"] == "Dostawczy"  # filled

    def test_does_not_mutate_input(self) -> None:
        card = {"paid_options": [], "service_equipment": None}
        card_before = copy.deepcopy(card)
        twin = _renault_master_digital_twin()
        normalize_card_summary_from_digital_twin(card, twin)
        assert card == card_before  # input untouched

    def test_paid_options_have_field_id_and_v3_fields(self) -> None:
        card: dict = {"paid_options": []}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        po = result["paid_options"][0]
        # Backend-side metadata for HITL
        assert po.get("field_id"), "missing field_id"
        # V3 numeric fields
        assert po.get("net_amount") is not None or po.get("gross_amount") is not None
        # Confidence reflects deterministic provenance (lower than 1.0 because Flash dropped it)
        assert po.get("confidence") is not None and po["confidence"] <= 0.85

    def test_service_components_have_field_id(self) -> None:
        card: dict = {"service_equipment": None}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        for comp in result["service_equipment"]["components"]:
            assert comp.get("field_id"), "missing field_id on service component"

    def test_zero_price_items_skipped_from_paid(self) -> None:
        card: dict = {"paid_options": []}
        twin = _renault_master_digital_twin()
        result = normalize_card_summary_from_digital_twin(card, twin)
        # 0-price items ("16 stalowe" / "zderzak") are NOT in paid_options
        names = [p["name"] for p in result["paid_options"]]
        assert '16" stalowe z kołpakami mini' not in names
        assert "zderzak przedni częściowo lakierowany" not in names

    def test_base_price_filled_from_financials_when_present(self) -> None:
        """When financials is populated, fill base_price. Skip when null
        (real-world Renault Master had financials=null)."""
        card: dict = {"base_price": "Brak"}
        twin = _renault_master_digital_twin()
        # Add financials to test the happy path
        twin["financials"] = {
            "base_price_gross": 167218.5,
            "final_price_gross": 204817.14,
        }
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert "167218" in result["base_price"].replace(" ", "")
        assert "brutto" in result["base_price"].lower()

    def test_base_price_skipped_when_financials_null(self) -> None:
        """When financials is null (real-world case), don't touch base_price."""
        card: dict = {"base_price": "Brak"}
        twin = _renault_master_digital_twin()  # has financials=None
        result = normalize_card_summary_from_digital_twin(card, twin)
        # Untouched
        assert result["base_price"] == "Brak"

    def test_handles_missing_digital_twin_gracefully(self) -> None:
        card: dict = {"paid_options": []}
        result = normalize_card_summary_from_digital_twin(card, {})
        assert result == card or result.get("paid_options") == []


# ═══════════════════════════════════════════════════════════════════
# Primitive parsers: _parse_int_from_unit + _km_to_kw
# ═══════════════════════════════════════════════════════════════════


class TestParseIntFromUnit:
    def test_parses_power_with_km_unit(self) -> None:
        assert _parse_int_from_unit("204 KM", unit_hint="KM") == 204

    def test_parses_capacity_without_unit(self) -> None:
        # capacity comes as plain int-string ("2755")
        assert _parse_int_from_unit("2755") == 2755

    def test_rejects_when_unit_hint_does_not_match(self) -> None:
        # "10.1 l/100km" must NOT be parsed as "10 KM"
        assert _parse_int_from_unit("10.1 l/100km", unit_hint="KM") is None

    def test_returns_none_on_empty_or_missing(self) -> None:
        assert _parse_int_from_unit(None) is None
        assert _parse_int_from_unit("") is None
        assert _parse_int_from_unit("   ") is None

    def test_passes_through_int_input(self) -> None:
        assert _parse_int_from_unit(150) == 150
        assert _parse_int_from_unit(150.0) == 150


class TestKmToKw:
    def test_iso_80000_conversion_204_km(self) -> None:
        # 204 KM × 0.7355 = 150.042 → round to 150
        assert _km_to_kw(204) == 150

    def test_iso_80000_conversion_150_km(self) -> None:
        # 150 × 0.7355 = 110.325 → round to 110
        assert _km_to_kw(150) == 110

    def test_none_in_none_out(self) -> None:
        assert _km_to_kw(None) is None


# ═══════════════════════════════════════════════════════════════════
# normalize_card_summary_from_digital_twin — digital_twin.{technical,features,dimensions}
# Real-world Hilux payload (id e1e2c459 observed 2026-05-19).
# ═══════════════════════════════════════════════════════════════════


def _hilux_digital_twin_with_nested_specs() -> dict:
    """Replica of the actual Hilux digital_twin (e1e2c459) showing the nested
    technical/features/dimensions shape that current Pro extraction produces."""
    return {
        "brand": None,
        "model": None,
        "optional_equipment": [],
        "technical": {
            "power": "204 KM",
            "transmission": "6-stopniowa automatyczna",
            "co2": "265 g/km",
            "drive": "Mild-Hybrid 48V (MHEV)",
            "capacity": "2755",
            "fuel_consumption": "10.1 l/100km",
        },
        "features": {
            "color": "6X1 Oxide Bronze",
            "wheels": '18" felgi aluminiowe z oponami 265/60 R18',
            "upholstery": "Tapicerka materiałowa w kolorze czarnym",
        },
        "dimensions": {
            "length_mm": 5325,
            "width_mm": 1855,
            "height_mm": 1865,
            "wheelbase_mm": 3085,
            "payload_kg": 1010,
            "curb_weight_kg": 2125,
            "gross_vehicle_weight_kg": 3130,
            "fuel_tank_capacity_l": 80,
            "cargo_length_mm": None,
            "cargo_width_mm": None,
            "cargo_height_mm": None,
            "cargo_volume_m3": None,
        },
    }


class TestNestedTechnicalFeaturesDimensions:
    def test_fills_power_hp_from_technical_power(self) -> None:
        card: dict = {"power_hp": None}
        twin = _hilux_digital_twin_with_nested_specs()
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["power_hp"] == 204

    def test_derives_power_kw_from_power_hp_when_missing(self) -> None:
        # No explicit power_kw in twin → derive from KM via ISO 80000 (0.7355)
        card: dict = {"power_hp": None, "power_kw": None}
        twin = _hilux_digital_twin_with_nested_specs()
        result = normalize_card_summary_from_digital_twin(card, twin)
        # 204 × 0.7355 = 150.042 → 150
        assert result["power_kw"] == 150

    def test_fills_transmission_and_emissions_and_capacity(self) -> None:
        card: dict = {"transmission": None, "emissions": None, "engine_capacity": None}
        twin = _hilux_digital_twin_with_nested_specs()
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["transmission"] == "6-stopniowa automatyczna"
        assert result["emissions"] == "265 g/km"
        assert result["engine_capacity"] == 2755

    def test_fills_exterior_color_and_wheels_from_features(self) -> None:
        card: dict = {"exterior_color": None, "wheels": None}
        twin = _hilux_digital_twin_with_nested_specs()
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["exterior_color"] == "6X1 Oxide Bronze"
        assert result["wheels"] == '18" felgi aluminiowe z oponami 265/60 R18'

    def test_passes_through_dimensions_unchanged(self) -> None:
        card: dict = {"dimensions": None}
        twin = _hilux_digital_twin_with_nested_specs()
        result = normalize_card_summary_from_digital_twin(card, twin)
        # 1:1 passthrough — keys match CargoAndDimensions Pydantic exactly
        assert result["dimensions"]["length_mm"] == 5325
        assert result["dimensions"]["width_mm"] == 1855
        assert result["dimensions"]["payload_kg"] == 1010
        assert result["dimensions"]["fuel_tank_capacity_l"] == 80
        # None entries from twin are preserved (no silent transform)
        assert result["dimensions"]["cargo_length_mm"] is None

    def test_idempotent_preserves_existing_flash_values(self) -> None:
        # User edited transmission manually — must NOT be overwritten by twin
        card: dict = {
            "power_hp": 250,
            "transmission": "Manualna (user-edited)",
            "engine_capacity": 1968,
        }
        twin = _hilux_digital_twin_with_nested_specs()
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["power_hp"] == 250
        assert result["transmission"] == "Manualna (user-edited)"
        assert result["engine_capacity"] == 1968
        # But empty fields ARE filled
        assert result["emissions"] == "265 g/km"

    def test_handles_missing_nested_dicts(self) -> None:
        # digital_twin with no technical/features/dimensions
        card: dict = {"power_hp": None, "wheels": None, "dimensions": None}
        twin: dict = {"brand": "TOYOTA", "model": "Hilux", "optional_equipment": []}
        result = normalize_card_summary_from_digital_twin(card, twin)
        # No crash, fields stay None
        assert result["power_hp"] is None
        assert result["wheels"] is None
        assert result["dimensions"] is None

    def test_explicit_power_kw_in_twin_wins_over_derived(self) -> None:
        # If Pro ever extracts power_kw separately, prefer it over KM×0.7355
        card: dict = {"power_hp": None, "power_kw": None}
        twin = _hilux_digital_twin_with_nested_specs()
        twin["technical"]["power_kw"] = "151 kW"  # different from 204×0.7355=150
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["power_kw"] == 151  # explicit wins


# ═══════════════════════════════════════════════════════════════════
# standard_equipment passthrough — clarification 2026-05-19:
# "cechy użytkowe" = comprehensive (standard + service + paid + dims)
# ═══════════════════════════════════════════════════════════════════


class TestStandardEquipmentPassthrough:
    def test_fills_standard_equipment_from_digital_twin(self) -> None:
        card: dict = {"standard_equipment": []}
        twin = _hilux_digital_twin_with_nested_specs()
        twin["standard_equipment"] = [
            "Reflektory TOP LED Matrix",
            "Climatronic - automatyczna klimatyzacja dwustrefowa",
            "Virtual Cockpit",
        ]
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["standard_equipment"] == [
            "Reflektory TOP LED Matrix",
            "Climatronic - automatyczna klimatyzacja dwustrefowa",
            "Virtual Cockpit",
        ]

    def test_strips_whitespace_and_filters_blanks(self) -> None:
        card: dict = {"standard_equipment": []}
        twin = _hilux_digital_twin_with_nested_specs()
        twin["standard_equipment"] = [
            "  Reflektory TOP LED Matrix  ",
            "",
            "   ",
            None,  # type: ignore[list-item]
            "Climatronic",
        ]
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["standard_equipment"] == ["Reflektory TOP LED Matrix", "Climatronic"]

    def test_idempotent_preserves_existing_standard_equipment(self) -> None:
        existing = ["Already-set item from Flash"]
        card: dict = {"standard_equipment": existing}
        twin = _hilux_digital_twin_with_nested_specs()
        twin["standard_equipment"] = ["From twin — should NOT overwrite"]
        result = normalize_card_summary_from_digital_twin(card, twin)
        assert result["standard_equipment"] == existing

    def test_no_crash_when_twin_standard_equipment_missing(self) -> None:
        card: dict = {"standard_equipment": []}
        twin = _hilux_digital_twin_with_nested_specs()
        # twin has no standard_equipment key at all
        twin.pop("standard_equipment", None)
        result = normalize_card_summary_from_digital_twin(card, twin)
        # Stays empty, no crash
        assert result.get("standard_equipment") == []
