"""Unit tests for the dynamic Reverse Search prompt builder."""
from __future__ import annotations

import os

os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")

from unittest.mock import patch  # noqa: E402

from core.feature_catalog_loader import CatalogFeatureEntry  # noqa: E402
from core.reverse_search_prompt import build_reverse_search_prompt  # noqa: E402


def _entry(**kw) -> CatalogFeatureEntry:
    defaults = dict(
        feature_key="abs",
        display_name="ABS",
        feature_type="boolean",
        category_name="Bezpieczeństwo",
        category_sort=1,
        sort_order=1,
    )
    defaults.update(kw)
    return CatalogFeatureEntry(**defaults)


def test_prompt_includes_required_sections() -> None:
    catalog = [
        _entry(feature_key="abs", display_name="ABS"),
        _entry(
            feature_key="cargo_volume",
            display_name="Pojemność ładunkowa",
            feature_type="numeric",
            category_name="Wymiary i Masy",
            category_sort=5,
            canonical_unit="m³",
        ),
        _entry(
            feature_key="drive_type",
            display_name="Napęd",
            feature_type="enum",
            category_name="Silnik i Osiągi",
            category_sort=3,
            allowed_values=["FWD", "RWD", "AWD"],
        ),
    ]
    with patch(
        "core.reverse_search_prompt.load_filterable_features", return_value=catalog
    ):
        prompt = build_reverse_search_prompt()

    assert "ZASADY EKSTRAKCJI" in prompt
    assert "POLA FINANSOWE" in prompt
    assert "WEJŚCIE AUDIO" in prompt
    assert "KATALOG CECH" in prompt
    assert "Liczba aktywnych cech filtrowalnych: 3" in prompt
    assert "`abs`" in prompt
    assert "`cargo_volume`" in prompt
    assert "[typ: numeric]" in prompt
    assert "[jednostka: m³]" in prompt
    assert "[dozwolone: FWD, RWD, AWD]" in prompt


def test_prompt_groups_by_category_in_sort_order() -> None:
    catalog = [
        _entry(feature_key="zzz", display_name="ZZZ feature", category_name="Zzz", category_sort=99, sort_order=1),
        _entry(feature_key="abc", display_name="ABC feature", category_name="Abc", category_sort=1, sort_order=1),
    ]
    with patch(
        "core.reverse_search_prompt.load_filterable_features", return_value=catalog
    ):
        prompt = build_reverse_search_prompt()

    abc_idx = prompt.find("### Abc")
    zzz_idx = prompt.find("### Zzz")
    assert abc_idx > 0 and zzz_idx > abc_idx


def test_prompt_handles_empty_catalog_gracefully() -> None:
    with patch(
        "core.reverse_search_prompt.load_filterable_features", return_value=[]
    ):
        prompt = build_reverse_search_prompt()

    assert "Katalog pusty" in prompt


def test_prompt_includes_synonyms_when_provided() -> None:
    catalog = [
        _entry(
            feature_key="adaptive_cruise_control",
            display_name="Aktywny tempomat (ACC)",
            trigger_keywords=["ACC", "tempomat radarowy", "aktywny tempomat"],
        ),
    ]
    with patch(
        "core.reverse_search_prompt.load_filterable_features", return_value=catalog
    ):
        prompt = build_reverse_search_prompt()

    assert "[synonimy: ACC, tempomat radarowy, aktywny tempomat]" in prompt


def test_prompt_dedupes_duplicate_display_names_preferring_prefixed() -> None:
    """If catalog has `abs` + `eq_abs` (same display name), only the prefixed variant
    should reach the prompt."""
    catalog = [
        _entry(feature_key="abs", display_name="ABS"),
        _entry(feature_key="eq_abs", display_name="ABS"),
        _entry(feature_key="tow_hitch", display_name="Hak"),
    ]
    with patch(
        "core.reverse_search_prompt.load_filterable_features", return_value=catalog
    ):
        prompt = build_reverse_search_prompt()

    assert "`eq_abs`" in prompt
    assert "`abs`" not in prompt.replace("`eq_abs`", "")  # naked variant filtered out
    assert "`tow_hitch`" in prompt
    assert "po deduplikacji z 3 wpisów" in prompt
    assert "Liczba aktywnych cech filtrowalnych: 2" in prompt


def test_prompt_includes_vehicle_category_constraint() -> None:
    catalog = [
        _entry(
            feature_key="ilosc_europalet",
            display_name="Liczba europalet",
            feature_type="numeric",
            applies_to_vehicle_categories=["Ciężarowy"],
        ),
    ]
    with patch(
        "core.reverse_search_prompt.load_filterable_features", return_value=catalog
    ):
        prompt = build_reverse_search_prompt()

    assert "[pojazdy: Ciężarowy]" in prompt
