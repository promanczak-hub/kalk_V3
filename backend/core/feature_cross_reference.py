"""Cross-reference vehicle features from multiple catalog sources.

Matches a vehicle's spec (card_summary) against variants extracted
from catalog documents, then creates feature evidence records.

Flow:
1. Load vehicle card_summary
2. Load extracted variants from selected catalog(s)
3. LLM Flash matches spec → best variant
4. Extract features from matched variant
5. body_parameter_calc → m², europallets, volume
6. Upsert evidence → resolve features
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from core.body_parameter_calc import calculate_cargo_params
from core.database import supabase as sb_client
from core.feature_resolver import resolve_vehicle_features
from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

try:
    from google.genai import types  # type: ignore[import-untyped]
except ImportError:
    types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# ── Response schema for LLM ─────────────────────────────────────


class MatchedFeature(BaseModel):
    """Single feature extracted from matched variant."""

    feature_key: str = Field(
        description="Klucz cechy z universal_features (np. 'liczba_miejsc', "
        "'dlugosc_przestrzeni_ladunkowej', 'europalety')"
    )
    mapping_confidence: float = Field(
        description="Ocena w skali 0.0 - 1.0 jak bardzo nazwa cechy producenta odpowiada semantycznie wybranemu kluczowi 'feature_key'."
    )
    value_text: str | None = Field(None, description="Wartość tekstowa cechy")
    value_num: float | None = Field(None, description="Wartość numeryczna cechy")
    value_bool: bool | None = Field(None, description="Wartość boolean cechy")
    unit: str | None = Field(None, description="Jednostka (mm, kg, szt, m², m³)")


class VariantMatchResult(BaseModel):
    """LLM output: matched variant + extracted features."""

    matched_variant_name: str = Field(
        description="Nazwa dopasowanego wariantu z katalogu "
        "(np. 'L3H3 FWD 177KM', 'Ducato 35 MH2 3.0')"
    )
    confidence: float = Field(description="Pewność dopasowania 0.0-1.0")
    reasoning: str = Field(description="Krótkie uzasadnienie dopasowania (1-2 zdania)")
    features: list[MatchedFeature] = Field(
        default_factory=list,
        description="Lista cech wyekstrahowanych z dopasowanego wariantu",
    )


class CatalogRanking(BaseModel):
    """Single catalog ranking."""

    catalog_id: str = Field(description="ID dopasowanego katalogu")
    relevance_score: float = Field(description="Ocena dopasowania 0.0-1.0")
    reasoning: str = Field(
        description="Krótkie uzasadnienie, dlaczego ten dokument pasuje"
    )


class CatalogRankingResult(BaseModel):
    """List of ranked catalogs."""

    rankings: list[CatalogRanking] = Field(
        description="Lista katalogów posortowana od najbardziej do najmniej pasującego",
    )


# ── Feature key catalog (loaded once) ───────────────────────────

_FEATURE_KEY_CACHE: list[str] | None = None


def _load_feature_keys() -> list[str]:
    """Load all feature_keys from universal_features."""
    global _FEATURE_KEY_CACHE  # noqa: PLW0603
    if _FEATURE_KEY_CACHE is not None:
        return _FEATURE_KEY_CACHE

    resp = (
        sb_client.schema("reverse_search")
        .table("universal_features")
        .select("feature_key")
        .eq("is_active", True)
        .execute()
    )
    _FEATURE_KEY_CACHE = [r["feature_key"] for r in (resp.data or [])]
    return _FEATURE_KEY_CACHE


def _load_feature_id_map() -> dict[str, str]:
    """Load feature_key → feature_id mapping."""
    resp = (
        sb_client.schema("reverse_search")
        .table("universal_features")
        .select("id, feature_key")
        .eq("is_active", True)
        .execute()
    )
    return {r["feature_key"]: r["id"] for r in (resp.data or [])}


# ── LLM Variant Matching ────────────────────────────────────────

CROSS_REF_SYSTEM_PROMPT = """\
Jesteś ekspertem ds. pojazdów dostawczych i osobowych. Otrzymujesz:
1. `vehicle_spec` — podsumowanie pojazdu (marka, model, silnik, wymiary, nadwozie)
2. `catalog_variants` — lista wariantów z katalogów/cenników z ich parametrami
3. `available_feature_keys` — lista kluczy cech w systemie

ZADANIE:
A) Dopasuj pojazd do NAJLEPSZEGO wariantu z katalogu na podstawie:
   - Marka + model
   - Typ nadwozia (Furgon, Kombi, Podwozie, etc.)
   - Klasa długości/wysokości (L1H1, L2H2, L3H3, etc.)
   - Silnik (moc, pojemność)
   - Napęd (FWD, RWD, AWD)

B) Wyciągnij z dopasowanego wariantu WSZYSTKIE użyteczne cechy i zmapuj je
   na klucze z `available_feature_keys`. Cechy numeryczne podaj w odpowiednich
   jednostkach (mm, kg, l, szt). Dla każdej zmapowanej cechy podaj `mapping_confidence` 
   (w skali 0.0 - 1.0) oceniając, jak precyzyjnie oryginalna nazwa cechy w katalogu producenta 
   odpowiada uniwersalnemu kluczowi.

C) Jeśli wariant zawiera wymiary ładunkowe (długość, szerokość, wysokość cargo),
   KONIECZNIE wyciągnij je jako osobne cechy.

WAŻNE:
- confidence < 0.5 → brak sensownego dopasowania, zwróć pustą listę features
- Zwracaj w features TYLKO te cechy, dla których `mapping_confidence` wynosi >= 0.80. Sprawdzaj rygorystycznie różnice w nazewnictwie!
- Jeśli dane z katalogu uzupełniają dane z konfiguracji (np. wymiary ładunkowe
  których nie ma w specyfikacji), wyciągnij je
- NIE wymyślaj danych — wyciągaj TYLKO to, co jest wprost w katalogu
"""


def _match_variant_with_llm(
    vehicle_spec: dict[str, Any],
    catalog_variants: list[dict[str, Any]],
    feature_keys: list[str],
) -> VariantMatchResult | None:
    """Use LLM Flash to match vehicle spec to catalog variant."""
    if types is None:
        logger.error("google.genai not available")
        return None

    client = get_gemini_client()

    user_content = json.dumps(
        {
            "vehicle_spec": vehicle_spec,
            "catalog_variants": catalog_variants,
            "available_feature_keys": feature_keys,
        },
        ensure_ascii=False,
        indent=2,
    )

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=VariantMatchResult,
        system_instruction=CROSS_REF_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[user_content],
            config=config,
        )
        text = getattr(response, "text", "{}") or "{}"
        data = json.loads(text)
        return VariantMatchResult(**data)
    except Exception as exc:
        logger.error("LLM cross-reference failed: %s", exc)
        return None


RANKING_SYSTEM_PROMPT = """\
Jesteś asystentem pomagającym wybrać najlepszy cennik/katalog dla konkretnego pojazdu.
Otrzymujesz:
1. `vehicle_spec` — dane pojazdu (marka, model, wersja, silnik).
2. `available_catalogs` — listę dostępnych dokumentów w systemie.

ZADANIE:
Oceń każdy dokument pod kątem tego, jak precyzyjnie opisuje podany pojazd. 
1. `relevance_score` = 1.0 oznacza idealne dopasowanie (ta sama marka, model i generacja/rok z tagu wersji).
2. `relevance_score` = 0.0 oznacza brak związku (inna marka/model).
3. Posortuj dokumenty od najbardziej trafnych do namniej trafnych.

Zwróć wynik jako listę w polu `rankings`.
"""


def rank_catalogs_for_vehicle(
    vehicle_spec: dict[str, Any],
    catalogs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Use LLM Flash to rank catalogs for a specific vehicle.

    Returns the original catalogs list, sorted by relevance score descending,
    with an added `_ranking` dict containing score and reasoning.
    """
    if not catalogs:
        return []

    if types is None:
        logger.error("google.genai not available. Returning unsorted catalogs.")
        return catalogs

    client = get_gemini_client()

    user_content = json.dumps(
        {
            "vehicle_spec": vehicle_spec,
            "available_catalogs": [
                {
                    "id": c["id"],
                    "brand": c["brand"],
                    "model_family": c["model_family"],
                    "display_name": c["display_name"],
                    "version_tag": c["version_tag"],
                    "file_type": c["file_type"],
                }
                for c in catalogs
            ],
        },
        ensure_ascii=False,
        indent=2,
    )

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=4096,
        response_mime_type="application/json",
        response_schema=CatalogRankingResult,
        system_instruction=RANKING_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[user_content],
            config=config,
        )
        text = getattr(response, "text", "{}") or "{}"
        data = json.loads(text)
        ranking_result = CatalogRankingResult(**data)

        # Map back to original catalogs
        score_map = {r.catalog_id: r for r in ranking_result.rankings}

        for cat in catalogs:
            rank_data = score_map.get(cat["id"])
            if rank_data:
                cat["_ranking"] = {
                    "score": rank_data.relevance_score,
                    "reasoning": rank_data.reasoning,
                }
            else:
                cat["_ranking"] = {"score": 0.0, "reasoning": "LLM omitted this item"}

        # Sort by score descending
        catalogs.sort(
            key=lambda x: x.get("_ranking", {}).get("score", 0.0), reverse=True
        )
        return catalogs

    except Exception as exc:
        logger.error("LLM catalog ranking failed: %s", exc)
        return catalogs


# ── Evidence creation ────────────────────────────────────────────


def _create_evidence_batch(
    vehicle_id: str,
    match_result: VariantMatchResult,
    feature_id_map: dict[str, str],
    source_type: str = "catalog",
) -> int:
    """Create feature evidence records from matched variant."""
    created = 0
    sb = sb_client

    for feat in match_result.features:
        if feat.mapping_confidence < 0.8:
            logger.debug(
                "Skipping feature '%s' due to low confidence: %s",
                feat.feature_key,
                feat.mapping_confidence,
            )
            continue

        feat_id = feature_id_map.get(feat.feature_key)
        if not feat_id:
            logger.debug(
                "Feature key '%s' not in catalog, skipping",
                feat.feature_key,
            )
            continue

        evidence: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": source_type,
            "evidence_status": "observed",
            "confidence": feat.mapping_confidence,
            "source_text": (f"Cross-ref: {match_result.matched_variant_name}"),
        }
        if feat.value_bool is not None:
            evidence["value_bool"] = feat.value_bool
        if feat.value_num is not None:
            evidence["value_num"] = feat.value_num
        if feat.value_text is not None:
            evidence["value_text"] = feat.value_text
        if feat.unit:
            evidence["unit"] = feat.unit

        try:
            sb.schema("reverse_search").table("vehicle_feature_evidence").upsert(
                evidence,
                on_conflict="source_vehicle_id,feature_id,source_type",
            ).execute()
            created += 1
        except Exception as exc:
            logger.warning(
                "Evidence upsert error for %s/%s: %s",
                vehicle_id,
                feat.feature_key,
                exc,
            )

    return created


def _create_body_param_evidence(
    vehicle_id: str,
    match_result: VariantMatchResult,
    feature_id_map: dict[str, str],
) -> int:
    """Create body parameter evidence from dimensions."""
    dims: dict[str, float] = {}
    for feat in match_result.features:
        if "cargo" in feat.feature_key and feat.value_num:
            if "dlugosc" in feat.feature_key or "length" in feat.feature_key:
                dims["length_mm"] = feat.value_num
            elif "szerokosc" in feat.feature_key or "width" in feat.feature_key:
                dims["width_mm"] = feat.value_num
            elif "wysokosc" in feat.feature_key or "height" in feat.feature_key:
                dims["height_mm"] = feat.value_num

    if not dims:
        return 0

    params = calculate_cargo_params(
        cargo_length_mm=dims.get("length_mm"),
        cargo_width_mm=dims.get("width_mm"),
        cargo_height_mm=dims.get("height_mm"),
    )

    created = 0
    sb = sb_client

    calc_features = {
        "powierzchnia_ladunkowa": (
            params.area_m2,
            "m²",
        ),
        "europalety": (
            params.europallets,
            "szt",
        ),
        "kubatura_ladunkowa": (
            params.volume_m3,
            "m³",
        ),
    }

    for feat_key, (value, unit) in calc_features.items():
        if value is None:
            continue
        feat_id = feature_id_map.get(feat_key)
        if not feat_id:
            continue

        evidence: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": "body_parameters",
            "evidence_status": "observed",
            "value_num": float(value),
            "unit": unit,
            "confidence": 0.99,
            "source_text": "Calculated from catalog dimensions",
        }

        try:
            sb.schema("reverse_search").table("vehicle_feature_evidence").upsert(
                evidence,
                on_conflict="source_vehicle_id,feature_id,source_type",
            ).execute()
            created += 1
        except Exception as exc:
            logger.warning(
                "Body param evidence error for %s: %s",
                feat_key,
                exc,
            )

    return created


# ── Audit: save match ────────────────────────────────────────────


def _save_catalog_match(
    vehicle_id: str,
    catalog_id: str,
    match_result: VariantMatchResult,
) -> None:
    """Save cross-reference match to audit table."""
    try:
        sb_client.schema("reverse_search").table("vehicle_catalog_matches").upsert(
            {
                "source_vehicle_id": vehicle_id,
                "catalog_source_id": catalog_id,
                "matched_variant_name": (match_result.matched_variant_name),
                "match_confidence": match_result.confidence,
            },
            on_conflict="source_vehicle_id,catalog_source_id",
        ).execute()
    except Exception as exc:
        logger.warning("Catalog match save error: %s", exc)


# ── Wipe features ───────────────────────────────────────────────


def wipe_vehicle_features(
    vehicle_id: str,
    source_type: str | None = None,
) -> dict[str, int]:
    """Delete all evidence and state for a vehicle.

    Args:
        vehicle_id: UUID of the vehicle.
        source_type: If set, only delete evidence from this source.
            State is still fully rebuilt after deletion.

    Returns:
        Counts of deleted evidence and state records.
    """
    sb = sb_client
    evidence_deleted = 0
    state_deleted = 0

    # Delete evidence
    ev_query = (
        sb.schema("reverse_search")
        .table("vehicle_feature_evidence")
        .delete()
        .eq("source_vehicle_id", vehicle_id)
    )
    if source_type:
        ev_query = ev_query.eq("source_type", source_type)

    try:
        resp = ev_query.execute()
        evidence_deleted = len(resp.data or [])
    except Exception as exc:
        logger.error("Evidence delete error: %s", exc)

    # Delete state (always full wipe for consistency)
    try:
        resp = (
            sb.schema("reverse_search")
            .table("vehicle_feature_state")
            .delete()
            .eq("source_vehicle_id", vehicle_id)
            .execute()
        )
        state_deleted = len(resp.data or [])
    except Exception as exc:
        logger.error("State delete error: %s", exc)

    # Delete catalog matches if full wipe
    if not source_type:
        try:
            sb.schema("reverse_search").table("vehicle_catalog_matches").delete().eq(
                "source_vehicle_id", vehicle_id
            ).execute()
        except Exception as exc:
            logger.warning("Catalog match delete error: %s", exc)

    logger.info(
        "Wiped features for %s: %d evidence, %d state",
        vehicle_id,
        evidence_deleted,
        state_deleted,
    )

    return {
        "evidence_deleted": evidence_deleted,
        "state_deleted": state_deleted,
    }


# ── Main entry point ────────────────────────────────────────────


def cross_reference_vehicle(
    vehicle_id: str,
    catalog_ids: list[str],
) -> dict[str, Any]:
    """Cross-reference vehicle with selected catalogs.

    Args:
        vehicle_id: UUID of the vehicle.
        catalog_ids: List of catalog UUIDs to match against.

    Returns:
        Summary with matched variants and created evidence.
    """
    sb = sb_client

    # 1. Load vehicle card_summary
    v_resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not v_resp.data:
        return {"error": f"Vehicle {vehicle_id} not found"}

    synthesis = v_resp.data[0].get("synthesis_data") or {}
    card_summary = synthesis.get("card_summary", {})
    if not card_summary:
        return {"error": "Vehicle has no card_summary"}

    vehicle_spec = {
        "brand": card_summary.get("brand") or synthesis.get("brand", ""),
        "model": card_summary.get("model") or synthesis.get("model", ""),
        "body_style": card_summary.get("body_style", ""),
        "powertrain": card_summary.get("powertrain", ""),
        "power_hp": card_summary.get("power_hp"),
        "drive_type": card_summary.get("drive_type", ""),
        "transmission": card_summary.get("transmission", ""),
        "vehicle_class": card_summary.get("vehicle_class", ""),
        "trim_level": card_summary.get("trim_level", ""),
    }

    # 2. Load catalog variants
    all_variants: list[dict[str, Any]] = []
    catalog_map: dict[str, str] = {}  # variant_name → catalog_id

    for cat_id in catalog_ids:
        cat_resp = (
            sb.schema("reverse_search")
            .table("model_document_sources")
            .select("id, extracted_data, display_name")
            .eq("id", cat_id)
            .eq("extraction_status", "ready")
            .limit(1)
            .execute()
        )
        if not cat_resp.data:
            logger.warning("Catalog %s not found or not ready", cat_id)
            continue

        extracted = cat_resp.data[0].get("extracted_data") or {}
        variants = extracted.get("variants", [])
        cat_name = cat_resp.data[0].get("display_name", cat_id)

        for v in variants:
            v["_source_catalog"] = cat_name
            v["_source_catalog_id"] = cat_id
            vname = v.get("variant_name", "")
            if vname:
                catalog_map[vname] = cat_id
            all_variants.append(v)

    if not all_variants:
        return {"error": "No ready variants found in selected catalogs"}

    # 3. Load feature keys + ID map
    feature_keys = _load_feature_keys()
    feature_id_map = _load_feature_id_map()

    # 4. LLM variant matching
    match_result = _match_variant_with_llm(vehicle_spec, all_variants, feature_keys)

    if not match_result or match_result.confidence < 0.3:
        return {
            "status": "no_match",
            "message": "LLM nie znalazł pasującego wariantu",
            "confidence": match_result.confidence if match_result else 0,
        }

    # 5. Create evidence from matched features
    evidence_count = _create_evidence_batch(
        vehicle_id, match_result, feature_id_map, "catalog"
    )

    # 6. Body parameter calculations
    body_count = _create_body_param_evidence(vehicle_id, match_result, feature_id_map)

    # 7. Save audit trail
    matched_cat_id = catalog_map.get(
        match_result.matched_variant_name,
        catalog_ids[0] if catalog_ids else "",
    )
    if matched_cat_id:
        _save_catalog_match(vehicle_id, matched_cat_id, match_result)

    # 8. Resolve features (merge all evidence)
    resolve_result = resolve_vehicle_features(vehicle_id)

    return {
        "status": "matched",
        "matched_variant": match_result.matched_variant_name,
        "confidence": match_result.confidence,
        "reasoning": match_result.reasoning,
        "evidence_created": evidence_count,
        "body_params_created": body_count,
        "features_extracted": len(match_result.features),
        "resolve_result": resolve_result,
    }
