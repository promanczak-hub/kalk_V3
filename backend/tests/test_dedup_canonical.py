"""Unit tests for core.dedup — canonical_id + duplicate flagging.

Critical: this module DETECTS potential duplicates but does NOT merge/drop them.
The HITL UI gives the user 100% control over what stays where.
"""

from __future__ import annotations

from core.dedup import (
    compute_canonical_id,
    flag_potential_duplicates,
    normalize_name,
)


# ═══════════════════════════════════════════════════════════════════
# Group A: normalize_name
# ═══════════════════════════════════════════════════════════════════


class TestNormalizeName:
    def test_lowercase(self) -> None:
        assert normalize_name("ZABUDOWA IZOTERMA") == "zabudowa izoterma"

    def test_strip_polish_diacritics(self) -> None:
        assert normalize_name("Łuk pneumatyczny") == "luk pneumatyczny"
        assert normalize_name("Żółć") == "zolc"
        assert normalize_name("Ścisła kabina") == "scisla kabina"

    def test_strip_german_umlauts(self) -> None:
        assert normalize_name("Türöffner") == "turoffner"
        assert normalize_name("Sicherheitsschloß") == "sicherheitsschloss"

    def test_collapse_whitespace(self) -> None:
        assert normalize_name("Pakiet   zima  ") == "pakiet zima"
        assert normalize_name("Pakiet\tzima\n") == "pakiet zima"
        assert normalize_name(" Pakiet zima ") == "pakiet zima"

    def test_strip_currency_tokens(self) -> None:
        assert normalize_name("Zabudowa 47970 PLN") == "zabudowa 47970"
        assert normalize_name("Klimatyzacja 1000 zł") == "klimatyzacja 1000"
        assert normalize_name("Pakiet 200 EUR netto") == "pakiet 200"
        assert normalize_name("Pakiet brutto") == "pakiet"

    def test_strip_parentheses(self) -> None:
        assert normalize_name("Pakiet (zima)") == "pakiet zima"
        assert normalize_name("Foo [bar]") == "foo bar"

    def test_strip_vendor_codes(self) -> None:
        # Vendor codes match pattern: 2-3 uppercase letters + digits
        assert normalize_name("Zabudowa izoterma ZAB123") == "zabudowa izoterma"
        assert normalize_name("Pakiet PR456") == "pakiet"
        assert normalize_name("ABC789 Test") == "test"

    def test_does_not_strip_short_alpha_only(self) -> None:
        # Don't accidentally strip legitimate short words
        assert normalize_name("BMW Series 3") == "bmw series 3"
        assert normalize_name("AC unit") == "ac unit"


# ═══════════════════════════════════════════════════════════════════
# Group B: compute_canonical_id
# ═══════════════════════════════════════════════════════════════════


class TestComputeCanonicalId:
    def test_same_name_same_price_same_hash(self) -> None:
        a = compute_canonical_id("Zabudowa izoterma", 47970.0)
        b = compute_canonical_id("Zabudowa izoterma", 47970.0)
        assert a == b

    def test_case_insensitive(self) -> None:
        a = compute_canonical_id("Zabudowa izoterma", 47970.0)
        b = compute_canonical_id("ZABUDOWA IZOTERMA", 47970.0)
        c = compute_canonical_id("zabudowa izoterma", 47970.0)
        assert a == b == c

    def test_diacritics_normalize(self) -> None:
        a = compute_canonical_id("Łuk pneumatyczny", 1000.0)
        b = compute_canonical_id("Luk pneumatyczny", 1000.0)
        assert a == b

    def test_vendor_code_stripped(self) -> None:
        a = compute_canonical_id("Zabudowa izoterma (ZAB123)", 47970.0)
        b = compute_canonical_id("Zabudowa izoterma", 47970.0)
        assert a == b

    def test_different_price_different_hash(self) -> None:
        a = compute_canonical_id("Zabudowa izoterma", 47970.0)
        b = compute_canonical_id("Zabudowa izoterma", 50000.0)
        assert a != b

    def test_different_name_different_hash(self) -> None:
        a = compute_canonical_id("Zabudowa izoterma", 47970.0)
        b = compute_canonical_id("Zabudowa kontener", 47970.0)
        assert a != b

    def test_none_price_consistent(self) -> None:
        a = compute_canonical_id("Pakiet zima", None)
        b = compute_canonical_id("Pakiet zima", None)
        assert a == b

    def test_none_vs_zero_different(self) -> None:
        # None and 0.0 mean different things
        a = compute_canonical_id("Pakiet zima", None)
        b = compute_canonical_id("Pakiet zima", 0.0)
        assert a != b

    def test_short_hash_length(self) -> None:
        h = compute_canonical_id("Test", 100.0)
        assert len(h) == 12
        assert all(c in "0123456789abcdef" for c in h)

    def test_rounding_eliminates_float_noise(self) -> None:
        # 47970.0 vs 47970.001 → same hash (rounded to 2 decimals)
        a = compute_canonical_id("Zabudowa", 47970.0)
        b = compute_canonical_id("Zabudowa", 47970.001)
        assert a == b


# ═══════════════════════════════════════════════════════════════════
# Group C: flag_potential_duplicates
# ═══════════════════════════════════════════════════════════════════


def _card_with_options(*opts: dict) -> dict:
    return {
        "base_price": "100000 PLN netto",
        "options_price": "0 PLN netto",
        "total_price": "100000 PLN netto",
        "paid_options": list(opts),
    }


def _opt(name: str, net: float, *, field_id: str = "") -> dict:
    return {
        "name": name,
        "price": f"{net} PLN netto",
        "net_amount": net,
        "price_type": "netto",
        "category": "Fabryczna",
        "field_id": field_id or f"id_{name.lower().replace(' ', '_')}",
    }


class TestFlagPotentialDuplicates:
    def test_no_duplicates_no_flags(self) -> None:
        card = _card_with_options(
            _opt("Pakiet zima", 1000.0),
            _opt("Pakiet lato", 1500.0),
        )
        result = flag_potential_duplicates(card)
        for o in result["paid_options"]:
            assert o.get("duplicate_of") is None

    def test_two_paid_options_same_canonical_cross_pointed(self) -> None:
        card = _card_with_options(
            _opt("Pakiet zima", 1000.0, field_id="A"),
            _opt("Pakiet zima", 1000.0, field_id="B"),
        )
        result = flag_potential_duplicates(card)
        a = next(o for o in result["paid_options"] if o["field_id"] == "A")
        b = next(o for o in result["paid_options"] if o["field_id"] == "B")
        assert a["duplicate_of"] == "B"
        assert b["duplicate_of"] == "A"

    def test_canonical_id_populated(self) -> None:
        card = _card_with_options(_opt("Pakiet zima", 1000.0))
        result = flag_potential_duplicates(card)
        cid = result["paid_options"][0].get("canonical_id")
        assert cid is not None
        assert len(cid) == 12

    def test_does_not_drop_or_merge(self) -> None:
        # NIE merge. Both items remain.
        card = _card_with_options(
            _opt("Pakiet zima", 1000.0, field_id="A"),
            _opt("Pakiet zima", 1000.0, field_id="B"),
        )
        result = flag_potential_duplicates(card)
        assert len(result["paid_options"]) == 2

    def test_service_equipment_aggregate_cross_pointed_to_paid_options(self) -> None:
        card = {
            "base_price": "100000 PLN netto",
            "options_price": "0 PLN netto",
            "total_price": "147970 PLN netto",
            "paid_options": [
                _opt("Zabudowa izoterma", 47970.0, field_id="po_1"),
            ],
            "service_equipment": {
                "name": "Zabudowa izoterma",
                "total_price_net": "47970 PLN",
                "total_price_gross": "59003 PLN",
                "components": [],
                "net_amount": 47970.0,
                "field_id": "se_main",
            },
        }
        result = flag_potential_duplicates(card)
        po = result["paid_options"][0]
        se = result["service_equipment"]
        assert po["duplicate_of"] == "se_main"
        assert se["duplicate_of"] == "po_1"

    def test_audit_log_in_card(self) -> None:
        card = _card_with_options(
            _opt("Pakiet zima", 1000.0, field_id="A"),
            _opt("Pakiet zima", 1000.0, field_id="B"),
        )
        result = flag_potential_duplicates(card)
        flags = result.get("_duplicate_flags") or []
        assert len(flags) >= 1
        # Each entry is a dict with at least canonical_id + field_ids
        entry = flags[0]
        assert "canonical_id" in entry
        assert set(entry["field_ids"]) == {"A", "B"}

    def test_components_within_service_equipment_flagged(self) -> None:
        # Two identical components inside service_equipment.components
        card = {
            "service_equipment": {
                "name": "Pakiet zabudowy",
                "total_price_net": "10000 PLN",
                "total_price_gross": "12300 PLN",
                "components": [
                    {
                        "name": "Element A",
                        "price_net": "5000 PLN",
                        "price_gross": "6150 PLN",
                        "net_amount": 5000.0,
                        "field_id": "c1",
                    },
                    {
                        "name": "Element A",
                        "price_net": "5000 PLN",
                        "price_gross": "6150 PLN",
                        "net_amount": 5000.0,
                        "field_id": "c2",
                    },
                ],
            },
            "paid_options": [],
        }
        result = flag_potential_duplicates(card)
        comps = result["service_equipment"]["components"]
        assert comps[0]["duplicate_of"] == "c2"
        assert comps[1]["duplicate_of"] == "c1"

    def test_handles_missing_field_id_gracefully(self) -> None:
        # If LLM forgot field_id, we should still compute canonical_id
        card = _card_with_options(
            {"name": "Pakiet", "price": "100 PLN netto", "net_amount": 100.0,
             "category": "Fabryczna", "price_type": "netto"},
        )
        result = flag_potential_duplicates(card)
        assert result["paid_options"][0].get("canonical_id")

    def test_empty_card_no_crash(self) -> None:
        result = flag_potential_duplicates({})
        assert result == {} or result.get("_duplicate_flags") == []

    def test_input_not_mutated(self) -> None:
        # Defensive: returns new dict, doesn't mutate caller's data
        card = _card_with_options(_opt("Pakiet zima", 1000.0))
        original_keys = set(card["paid_options"][0].keys())
        flag_potential_duplicates(card)
        assert set(card["paid_options"][0].keys()) == original_keys
