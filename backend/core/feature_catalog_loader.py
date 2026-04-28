"""Catalog loader for Reverse Search.

Source of truth: Google Sheet 'cechy' → synced into Supabase via mdm_sync.py.
This module reads from Supabase (`reverse_search.universal_features`) and
exposes the catalog needed by the LLM extraction prompt and downstream
validators.

The catalog is Redis-cached for 1 hour. Call `invalidate_catalog_cache()`
right after `mdm_sync.import_from_sheet()` to push fresh data immediately.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from core.database import supabase
from core.redis_cache import cache_invalidate_pattern, redis_cache

logger = logging.getLogger(__name__)

CATALOG_CACHE_TTL = 3600  # 1 hour


class CatalogFeatureEntry(BaseModel):
    feature_key: str
    display_name: str
    feature_type: str  # 'boolean' | 'numeric' | 'text' | 'enum'
    category_name: str = "Inne"
    category_sort: int = 999
    sort_order: int = 999
    trigger_keywords: list[str] = Field(default_factory=list)
    allowed_values: list[str] = Field(default_factory=list)
    applies_to_vehicle_categories: list[str] = Field(default_factory=list)
    applies_to_body_subtypes: list[str] = Field(default_factory=list)
    applies_to_powertrains: list[str] = Field(default_factory=list)
    applies_to_drivetrains: list[str] = Field(default_factory=list)
    is_required_for_reverse_search: bool = False
    canonical_unit: str | None = None
    description: str | None = None


@redis_cache(ttl_seconds=CATALOG_CACHE_TTL, prefix="reverse_search_catalog:")
def _load_filterable_features_raw() -> list[dict[str, Any]]:
    """Read active+filterable features and join their categories. Returns plain dicts."""
    feat_result = (
        supabase.schema("reverse_search")
        .table("universal_features")
        .select(
            "feature_key, display_name, feature_type, "
            "trigger_keywords, allowed_values, "
            "applies_to_vehicle_categories, applies_to_body_subtypes, "
            "applies_to_powertrains, applies_to_drivetrains, "
            "is_required_for_reverse_search, canonical_unit, description, "
            "sort_order, category_id"
        )
        .eq("is_active", True)
        .eq("is_filterable", True)
        .execute()
    )
    features: list[dict[str, Any]] = list(feat_result.data or [])

    cat_result = (
        supabase.schema("reverse_search")
        .table("universal_feature_categories")
        .select("id, display_name, sort_order")
        .execute()
    )
    cat_map: dict[str, dict[str, Any]] = {
        c["id"]: c for c in (cat_result.data or [])
    }

    for f in features:
        cat = cat_map.get(f.get("category_id") or "") or {}
        f["category_name"] = cat.get("display_name") or "Inne"
        f["category_sort"] = cat.get("sort_order") if cat.get("sort_order") is not None else 999
        f["sort_order"] = f.get("sort_order") if f.get("sort_order") is not None else 999
        for arr_key in (
            "trigger_keywords",
            "allowed_values",
            "applies_to_vehicle_categories",
            "applies_to_body_subtypes",
            "applies_to_powertrains",
            "applies_to_drivetrains",
        ):
            if f.get(arr_key) is None:
                f[arr_key] = []
        f.pop("category_id", None)

    features.sort(key=lambda f: (f.get("category_sort", 999), f.get("sort_order", 999)))
    return features


def load_filterable_features() -> list[CatalogFeatureEntry]:
    """Return validated catalog entries (Pydantic models)."""
    raw = _load_filterable_features_raw()
    out: list[CatalogFeatureEntry] = []
    for r in raw:
        try:
            out.append(CatalogFeatureEntry(**r))
        except Exception as exc:
            logger.warning("Skipping malformed catalog row %s: %s", r.get("feature_key"), exc)
    return out


def get_feature_lookup() -> dict[str, CatalogFeatureEntry]:
    """Return dict keyed by feature_key for O(1) validation against catalog."""
    return {f.feature_key: f for f in load_filterable_features()}


def invalidate_catalog_cache() -> int:
    """Drop all cached catalog entries. Call after `mdm_sync.import_from_sheet()`."""
    n = cache_invalidate_pattern("reverse_search_catalog:*")
    logger.info("Invalidated %d catalog cache keys", n)
    return n
