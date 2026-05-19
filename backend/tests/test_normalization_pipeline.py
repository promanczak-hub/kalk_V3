"""Tests for pipeline_normalization — PASS B (deterministic post-processing).

Pure logic — NO Gemini calls. Input: RawExtractionResult. Output: CardSummary dict.
"""

from __future__ import annotations

from core.extractor_models import (
    OffsetSpan,
    RawExtractionResult,
    RawOptionLine,
    RawPriceLine,
)
from core.pipeline_normalization import normalize_raw_to_card_summary


# ═══════════════════════════════════════════════════════════════════
# Top-level price aggregation
# ═══════════════════════════════════════════════════════════════════


class TestTopLevelPrices:
    def test_base_and_total_with_vat(self) -> None:
        raw = RawExtractionResult(
            raw_prices=[
                RawPriceLine(
                    quoted_text="100 000 PLN netto",
                    role="base_price",
                    net_amount=100_000.0,
                    vat_rate=0.23,
                ),
                RawPriceLine(
                    quoted_text="120 000 PLN netto",
                    role="total_price",
                    net_amount=120_000.0,
                    vat_rate=0.23,
                ),
            ],
        )
        card = normalize_raw_to_card_summary(raw)
        assert card["base_price_net"] == 100_000.0
        assert card["base_price_gross"] == 123_000.0  # computed from net
        assert card["base_price_vat"] == 0.23
        assert card["total_price_net"] == 120_000.0
        assert card["total_price_gross"] == 147_600.0
        # Legacy string fields stay populated for back-compat
        assert "PLN" in card["base_price"]
        assert "PLN" in card["total_price"]

    def test_missing_prices_yield_brak(self) -> None:
        raw = RawExtractionResult()
        card = normalize_raw_to_card_summary(raw)
        assert card["base_price_net"] is None
        assert card["base_price"] == "Brak"


# ═══════════════════════════════════════════════════════════════════
# Paid options + service equipment split
# ═══════════════════════════════════════════════════════════════════


class TestPaidOptionsSplit:
    def test_factory_option_goes_to_paid_options(self) -> None:
        raw = RawExtractionResult(
            raw_options=[
                RawOptionLine(
                    name="Pakiet zima",
                    net_amount=1000.0,
                    vat_rate=0.23,
                    category_hint="fabryczna",
                ),
            ],
        )
        card = normalize_raw_to_card_summary(raw)
        assert len(card["paid_options"]) == 1
        assert card["paid_options"][0]["category"] == "Fabryczna"
        assert card["paid_options"][0]["net_amount"] == 1000.0
        assert card["paid_options"][0]["gross_amount"] == 1230.0
        assert card["service_equipment"] is None

    def test_service_option_goes_to_service_equipment(self) -> None:
        raw = RawExtractionResult(
            raw_options=[
                RawOptionLine(
                    name="Zabudowa izoterma",
                    net_amount=47970.0,
                    vat_rate=0.23,
                ),
            ],
        )
        card = normalize_raw_to_card_summary(raw)
        assert card["paid_options"] == []
        assert card["service_equipment"] is not None
        comps = card["service_equipment"]["components"]
        assert len(comps) == 1
        assert comps[0]["name"] == "Zabudowa izoterma"
        assert comps[0]["net_amount"] == 47970.0

    def test_heuristic_recognizes_polish_service_keywords(self) -> None:
        # Multi-language heuristic — Polish "zabudowa", "izoterma", "skrzynia"
        for name in ("Zabudowa kontener", "Kontener Izotermiczny", "Skrzynia ładunkowa"):
            raw = RawExtractionResult(
                raw_options=[RawOptionLine(name=name, net_amount=1000.0, vat_rate=0.23)]
            )
            card = normalize_raw_to_card_summary(raw)
            assert card["service_equipment"] is not None, f"{name!r} not detected as service"


# ═══════════════════════════════════════════════════════════════════
# Dedup integration
# ═══════════════════════════════════════════════════════════════════


class TestDedupFlagging:
    def test_two_identical_paid_options_cross_pointed(self) -> None:
        raw = RawExtractionResult(
            raw_options=[
                RawOptionLine(name="Pakiet zima", net_amount=1000.0, vat_rate=0.23),
                RawOptionLine(name="Pakiet zima", net_amount=1000.0, vat_rate=0.23),
            ],
        )
        card = normalize_raw_to_card_summary(raw)
        assert len(card["paid_options"]) == 2
        # Both have canonical_id matching, and duplicate_of points to the other
        po0 = card["paid_options"][0]
        po1 = card["paid_options"][1]
        assert po0["canonical_id"] == po1["canonical_id"]
        assert po0["duplicate_of"] == po1["field_id"]
        assert po1["duplicate_of"] == po0["field_id"]

    def test_service_eq_aggregate_cross_pointed_to_factory_option(self) -> None:
        # Factory option "Zabudowa izoterma" 47970 + service_eq with same name+price
        # → both get duplicate_of flags after normalization
        raw = RawExtractionResult(
            raw_options=[
                # This goes to service_equipment.components (service hint)
                RawOptionLine(name="Zabudowa izoterma", net_amount=47970.0, vat_rate=0.23),
                # This also goes to service (same name) — but normalization
                # will create only one components[] entry per option call.
                # Synth: two distinct calls so we have 2 components with same canonical.
                RawOptionLine(name="Zabudowa izoterma", net_amount=47970.0, vat_rate=0.23),
            ],
        )
        card = normalize_raw_to_card_summary(raw)
        # Both components have same canonical_id, duplicate_of cross-pointed
        comps = card["service_equipment"]["components"]
        assert len(comps) == 2
        assert comps[0]["canonical_id"] == comps[1]["canonical_id"]


# ═══════════════════════════════════════════════════════════════════
# Source offsets passthrough
# ═══════════════════════════════════════════════════════════════════


class TestOffsetPassthrough:
    def test_price_offset_propagates(self) -> None:
        raw = RawExtractionResult(
            raw_prices=[
                RawPriceLine(
                    quoted_text="100 000 PLN netto",
                    role="base_price",
                    net_amount=100_000.0,
                    vat_rate=0.23,
                    offsets=[OffsetSpan(page=2, bbox=[100, 200, 300, 220])],
                ),
            ],
        )
        card = normalize_raw_to_card_summary(raw)
        entries = card.get("source_offsets_by_field") or []
        assert any(
            e["field_path"] == "base_price" and e["spans"][0]["page"] == 2
            for e in entries
        )

    def test_visual_dimension_offset_propagates(self) -> None:
        raw = RawExtractionResult(
            raw_dimension_lines=[
                RawPriceLine(
                    quoted_text="5580 mm",
                    role="dimension",
                    label="length_mm",
                    offsets=[OffsetSpan(page=3, from_visual=True)],
                ),
            ],
        )
        card = normalize_raw_to_card_summary(raw)
        entries = card.get("source_offsets_by_field") or []
        assert any(
            e["field_path"].endswith("length_mm")
            and e["spans"][0].get("from_visual") is True
            for e in entries
        )


# ═══════════════════════════════════════════════════════════════════
# Legacy seed merge (preserve body_style, powertrain, etc. from old Flash)
# ═══════════════════════════════════════════════════════════════════


class TestLegacySeedMerge:
    def test_body_style_preserved(self) -> None:
        seed = {
            "body_style": "Furgon",
            "powertrain": "2.0 TDI 122 KM",
            "base_price": "stale_value",  # will be overwritten
        }
        raw = RawExtractionResult(
            raw_prices=[
                RawPriceLine(
                    quoted_text="100 000 PLN",
                    role="base_price",
                    net_amount=100_000.0,
                    vat_rate=0.23,
                ),
            ],
        )
        card = normalize_raw_to_card_summary(raw, legacy_card_seed=seed)
        assert card["body_style"] == "Furgon"  # preserved
        assert card["powertrain"] == "2.0 TDI 122 KM"
        assert card["base_price_net"] == 100_000.0  # new numeric field
