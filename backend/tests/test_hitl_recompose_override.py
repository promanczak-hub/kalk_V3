"""Phase B — tests for composite_body_style.recompose_with_override.

User picks cabin_kind + zabudowa_sot_key from HITL palette. Backend must:
- map all SOT-supported pairs to canonical body_type names
- handle KONTENER → IZOTERMA/CHLODNIA promotion when card_summary hints
- return None for un-mappable combinations (no LLM fallback in unit tests)
"""

from __future__ import annotations

import pytest

from core.composite_body_style import recompose_with_override


class TestRecomposeWithOverride:
    @pytest.mark.parametrize(
        "cabin,zabudowa,expected",
        [
            ("podwozie_brygadowe", "SKRZYNIA", "Podwozie Brygadowe Skrzynia"),
            ("podwozie_brygadowe", "KONTENER", "Podwozie Brygadowe Kontener"),
            ("podwozie_brygadowe", "WYWROTKA", "Podwozie Brygadowe Wywrotka"),
            ("podwozie_brygadowe", "PLANDEKA", "Podwozie Brygadowe Plandeka"),
            ("podwozie_brygadowe", "CHLODNIA", "Podwozie Brygadowe Chłodnia"),
            ("podwozie_brygadowe", "IZOTERMA", "Podwozie Brygadowe Izoterma"),
            ("podwozie", "SKRZYNIA", "Podwozie Skrzynia"),
            ("podwozie", "KONTENER", "Podwozie Kontener"),
            ("podwozie", "WYWROTKA", "Podwozie Wywrotka"),
            ("podwozie", "PLANDEKA", "Podwozie Plandeka"),
            ("podwozie", "CHLODNIA", "Podwozie Chłodnia"),
            ("podwozie", "IZOTERMA", "Podwozie Izoterma"),
            ("furgon", "CHLODNIA", "Furgon Chłodnia"),
            ("furgon", "IZOTERMA", "Furgon Izoterma"),
        ],
    )
    def test_all_sot_pairs_mapped(self, cabin, zabudowa, expected):
        result = recompose_with_override(cabin, zabudowa)
        assert result == expected

    def test_furgon_brygadowy_no_zabudowa_returns_sot_furgon_brygadowy(self):
        assert recompose_with_override("furgon_brygadowy", None) == "Furgon brygadowy"

    def test_furgon_brygadowy_with_zabudowa_uses_furgon_lookup(self):
        # furgon_brygadowy + CHLODNIA → szukaj w mapie furgon
        assert recompose_with_override("furgon_brygadowy", "CHLODNIA") == "Furgon Chłodnia"

    def test_podwozie_alone_returns_none(self):
        # samo "podwozie" bez zabudowy nie ma sensu jako SOT body_style
        assert recompose_with_override("podwozie", None) is None

    def test_zabudowa_only_assumes_podwozie(self):
        # User wybrał tylko CHLODNIA → backend zakłada podwozie
        assert recompose_with_override(None, "CHLODNIA") == "Podwozie Chłodnia"

    def test_both_none_returns_none(self):
        assert recompose_with_override(None, None) is None

    def test_unknown_combination_returns_none_without_llm(self):
        # furgon + SKRZYNIA nie ma w SOT (furgon trzyma izoterm/chłodnia)
        assert recompose_with_override("furgon", "SKRZYNIA") is None

    def test_kontener_promoted_to_izoterma_via_card_summary(self):
        cs = {
            "body_style": "podwozie",
            "service_equipment": {"name": "Kontener Izotermiczny 3700x2010"},
        }
        result = recompose_with_override("podwozie", "KONTENER", card_summary=cs)
        assert result == "Podwozie Izoterma"

    def test_kontener_promoted_to_chlodnia_via_card_summary(self):
        cs = {
            "body_style": "podwozie",
            "service_equipment": {
                "name": "Chłodnia 5m3",
                "components": [{"name": "Agregat Chłodniczy"}],
            },
        }
        result = recompose_with_override("podwozie", "KONTENER", card_summary=cs)
        assert result == "Podwozie Chłodnia"

    def test_explicit_chlodnia_not_overridden_by_promotion_logic(self):
        # User explicitly chose CHLODNIA from palette — even if service_equipment
        # has plain text, we keep user's choice (no demotion to KONTENER)
        cs = {"body_style": "podwozie", "service_equipment": {"name": "Plain Box"}}
        result = recompose_with_override("podwozie", "CHLODNIA", card_summary=cs)
        assert result == "Podwozie Chłodnia"
