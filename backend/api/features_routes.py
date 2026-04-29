"""FastAPI routes for the reverse_search / universal features system.

All endpoints under /api/features/...
Isolated from calculator endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from pydantic import BaseModel

from core.database import supabase

from core.feature_cross_reference import (
    cross_reference_vehicle,
    wipe_vehicle_features,
)
from core.feature_enrichment import enrich_vehicle_features
from core.feature_resolver import resolve_vehicle_features
from core.models_features import (
    FeatureCatalogResponse,
    FeatureExtractionRequest,
    FeatureSearchRequest,
    FeatureSearchResponse,
    FeatureSearchResultItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["features"])


# ── Feature Catalog ────────────────────────────────────────────


@router.get("/features/catalog")
def get_feature_catalog() -> FeatureCatalogResponse:
    """List all universal features grouped by category."""
    sb = supabase

    cats_resp = (
        sb.schema("reverse_search")
        .table("universal_feature_categories")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )

    features_resp = (
        sb.schema("reverse_search")
        .table("universal_features")
        .select("*")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )

    categories: list[dict[str, Any]] = []
    for cat in cats_resp.data:
        cat_features = [f for f in features_resp.data if f["category_id"] == cat["id"]]
        categories.append(
            {
                "id": cat["id"],
                "category_key": cat["category_key"],
                "display_name": cat["display_name"],
                "vehicle_scope": cat["vehicle_scope"],
                "features": cat_features,
            }
        )

    return FeatureCatalogResponse(
        categories=categories,
        total_features=len(features_resp.data),
    )


# ── Vehicle Feature State ─────────────────────────────────────

_TTL_FEATURES_STATE = 180  # 3 minutes — invalidated on resolve/crossref


@router.get("/features/vehicle/{vehicle_id}/state")
def get_vehicle_feature_state(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get resolved features for a vehicle, with Redis cache (TTL 3 min).

    Lazy enrichment: if no feature state exists yet,
    auto-enrich from vehicle_synthesis.card_summary.
    """
    from core.redis_cache import _get_client, _PREFIX
    import json

    client = _get_client()
    cache_key = f"{_PREFIX}features_state:{vehicle_id}"

    if client is not None:
        try:
            cached = client.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: features_state [%s]", vehicle_id)
                return json.loads(cached)
        except Exception as exc:
            logger.debug("Redis GET error [%s]: %s", cache_key, exc)

    sb = supabase
    resp = (
        sb.schema("reverse_search")
        .table("vehicle_features_summary_view")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )
    by_category: dict[str, list[dict]] = {}
    for row in resp.data:
        cat = row.get("category_name", "Inne")
        by_category.setdefault(cat, []).append(row)

    result = {
        "vehicle_id": vehicle_id,
        "categories": by_category,
        "total_features": len(resp.data),
    }

    if client is not None:
        try:
            client.setex(
                cache_key, _TTL_FEATURES_STATE, json.dumps(result, default=str)
            )
        except Exception as exc:
            logger.debug("Redis SET error [%s]: %s", cache_key, exc)

    return result


# ── Vehicle Feature Evidence ──────────────────────────────────


@router.get("/features/vehicle/{vehicle_id}/evidence")
def get_vehicle_feature_evidence(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get raw feature evidence for a vehicle."""
    sb = supabase

    resp = (
        sb.schema("reverse_search")
        .table("vehicle_feature_evidence")
        .select("*, universal_features(feature_key, display_name)")
        .eq("source_vehicle_id", vehicle_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "vehicle_id": vehicle_id,
        "evidence": resp.data,
        "total": len(resp.data),
    }


# ── Feature Wipe ──────────────────────────────────────────────


@router.delete("/features/vehicle/{vehicle_id}/evidence")
def wipe_vehicle_evidence(
    vehicle_id: str,
    source_type: str | None = None,
) -> dict[str, Any]:
    """Delete all evidence and state for a vehicle.

    Optionally filter by source_type to delete only evidence
    from a specific source (e.g. 'catalog', 'service_option').
    State is always fully wiped for consistency.
    """
    result = wipe_vehicle_features(vehicle_id, source_type)
    return {
        "vehicle_id": vehicle_id,
        "source_type_filter": source_type,
        "status": "wiped",
        **result,
    }


# ── Feature Cross-Reference ───────────────────────────────────


class CrossRefRequest(BaseModel):
    """Request body for cross-reference endpoint."""

    catalog_ids: list[str]


@router.post("/features/vehicle/{vehicle_id}/cross-reference")
def cross_reference_vehicle_features(
    vehicle_id: str,
    body: CrossRefRequest,
) -> dict[str, Any]:
    """Cross-reference vehicle with selected catalogs.

    Matches vehicle spec against extracted catalog variants via LLM,
    creates evidence records, and resolves feature state.
    """
    if not body.catalog_ids:
        raise HTTPException(
            status_code=400,
            detail="Musisz wybrać przynajmniej jeden katalog",
        )

    result = cross_reference_vehicle(vehicle_id, body.catalog_ids)
    return result


# ── Feature Rebuild ────────────────────────────────────────────


@router.post("/features/vehicle/{vehicle_id}/rebuild")
def rebuild_vehicle_features(
    vehicle_id: str,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """Trigger feature state resolution for a vehicle."""
    result = resolve_vehicle_features(vehicle_id, bundle_id)
    return {
        "vehicle_id": vehicle_id,
        "status": "completed",
        **result,
    }


# ── Catalog Manual Features Selection ──────────────────────────


@router.get("/features/vehicle/{vehicle_id}/catalog-preview")
def preview_catalog_features_endpoint(
    vehicle_id: str,
    catalog_id: str,
) -> dict[str, Any]:
    """Preview features that would be matched from a catalog."""
    from core.feature_cross_reference import preview_catalog_features

    return preview_catalog_features(vehicle_id, catalog_id)


class AddSelectedFeaturesRequest(BaseModel):
    catalog_id: str
    features: list[dict[str, Any]]


@router.post("/features/vehicle/{vehicle_id}/add-selected-catalog-features")
def add_selected_catalog_features(
    vehicle_id: str,
    body: AddSelectedFeaturesRequest,
) -> dict[str, Any]:
    """Add selected features manually from a catalog preview."""
    from core.database import supabase
    from core.feature_resolver import resolve_vehicle_features
    from core.feature_cross_reference import _get_feature_id_map

    feature_id_map = _get_feature_id_map()
    evidence_batch = []

    for feat in body.features:
        feat_key = feat.get("feature_key")
        feat_id = feature_id_map.get(feat_key)
        if not feat_id:
            continue

        evidence: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": "manual_override",
            "evidence_status": "observed",
            "confidence": 1.0,
            "source_text": "Ręczny wybór z zasugerowanego cennika",
        }

        if "value_bool" in feat and feat["value_bool"] is not None:
            evidence["value_bool"] = feat["value_bool"]
        if "value_num" in feat and feat["value_num"] is not None:
            evidence["value_num"] = feat["value_num"]
        if "value_text" in feat and feat["value_text"] is not None:
            evidence["value_text"] = feat["value_text"]
        if "unit" in feat and feat["unit"]:
            evidence["unit"] = feat["unit"]

        evidence_batch.append(evidence)

    if evidence_batch:
        try:
            supabase.schema("reverse_search").table("vehicle_feature_evidence").upsert(
                evidence_batch,
                on_conflict="source_vehicle_id,feature_id,source_type",
            ).execute()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Błąd zapisu cech: {exc}")

    # Zapisz w vehicle_catalog_matches fakt, że dopasowaliśmy ręcznie
    try:
        supabase.schema("reverse_search").table("vehicle_catalog_matches").upsert(
            {
                "source_vehicle_id": vehicle_id,
                "catalog_source_id": body.catalog_id,
                "matched_variant_name": "Wybrane ręcznie z cennika",
                "match_confidence": 1.0,
            },
            on_conflict="source_vehicle_id,catalog_source_id",
        ).execute()
    except Exception:
        pass

    # Usuń suggested_catalog bo już dodaliśmy dane
    try:
        current_synth_resp = (
            supabase.table("vehicle_synthesis")
            .select("synthesis_data")
            .eq("id", vehicle_id)
            .execute()
        )
        if current_synth_resp.data:
            current_synth = current_synth_resp.data[0].get("synthesis_data") or {}
            if "suggested_catalog" in current_synth:
                del current_synth["suggested_catalog"]
                supabase.table("vehicle_synthesis").update(
                    {"synthesis_data": current_synth}
                ).eq("id", vehicle_id).execute()
    except Exception:
        pass

    result = resolve_vehicle_features(vehicle_id)
    return {
        "status": "success",
        "added_features": len(evidence_batch),
        "resolve_result": result,
    }


# ── Reverse Search AI Extraction ───────────────────────────────


_ALLOWED_AUDIO_MIME_TYPES = frozenset({
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/aac",
    "audio/flac",
    "audio/x-m4a",
})
_MAX_AUDIO_BYTES = 25 * 1024 * 1024


_ALLOWED_NUMERIC_OPS = frozenset({"eq", "gte", "lte", "in"})


def _build_extraction_response(json_resp: dict[str, Any]) -> dict[str, Any]:
    """Validate LLM output against the live catalog and build the API response.

    Drops feature_keys absent from the catalog, drops type mismatches, and
    produces both the new multi-type `extracted_features` and a legacy
    boolean-only `extracted_filters` list (for unchanged frontend consumers).
    """
    from core.feature_catalog_loader import get_feature_lookup

    catalog = get_feature_lookup()

    raw_features: Any = json_resp.get("features", [])
    # Backwards-compat: some old responses may still use 'matched_features' (list[str]).
    if not raw_features:
        legacy = json_resp.get("matched_features", [])
        if isinstance(legacy, list):
            raw_features = [
                {"feature_key": k, "op": "eq", "value_bool": True}
                for k in legacy
                if isinstance(k, str) and k.strip()
            ]
    if not isinstance(raw_features, list):
        raw_features = []

    extracted_features: list[dict[str, Any]] = []
    legacy_filters: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for raw in raw_features:
        if not isinstance(raw, dict):
            continue
        key = raw.get("feature_key")
        if not isinstance(key, str) or not key.strip():
            continue
        key = key.strip()

        cat_entry = catalog.get(key)
        if cat_entry is None:
            rejected.append({"feature_key": key, "reason": "not_in_catalog"})
            continue

        ftype = cat_entry.feature_type
        op_raw = raw.get("op", "eq")
        op = op_raw if op_raw in _ALLOWED_NUMERIC_OPS else "eq"
        value_bool = raw.get("value_bool")
        value_num = raw.get("value_num")
        value_text = raw.get("value_text")

        if ftype == "boolean":
            if value_bool is not True:
                rejected.append({"feature_key": key, "reason": "boolean_not_true"})
                continue
            entry = {
                "feature_key": key,
                "feature_type": "boolean",
                "op": "eq",
                "value_bool": True,
                "display_name": cat_entry.display_name,
            }
            extracted_features.append(entry)
            legacy_filters.append({"feature_key": key, "value_bool": True})

        elif ftype == "numeric":
            if value_num is None:
                rejected.append({"feature_key": key, "reason": "numeric_value_missing"})
                continue
            try:
                num = float(value_num)
            except (TypeError, ValueError):
                rejected.append({"feature_key": key, "reason": "numeric_not_a_number"})
                continue
            extracted_features.append({
                "feature_key": key,
                "feature_type": "numeric",
                "op": op,
                "value_num": num,
                "display_name": cat_entry.display_name,
                "canonical_unit": cat_entry.canonical_unit,
            })

        elif ftype in ("text", "enum"):
            if not isinstance(value_text, str) or not value_text.strip():
                rejected.append({"feature_key": key, "reason": "text_value_missing"})
                continue
            text_val = value_text.strip()
            if (
                ftype == "enum"
                and cat_entry.allowed_values
                and text_val not in cat_entry.allowed_values
            ):
                rejected.append({"feature_key": key, "reason": "enum_value_not_allowed"})
                continue
            extracted_features.append({
                "feature_key": key,
                "feature_type": ftype,
                "op": "eq",
                "value_text": text_val,
                "display_name": cat_entry.display_name,
            })

        else:
            rejected.append({"feature_key": key, "reason": f"unknown_type_{ftype}"})

    if rejected:
        logger.info(
            "Reverse Search extraction rejected %d entries: %s",
            len(rejected),
            rejected[:10],
        )

    # Defense in depth: dedupe by display_name (case-insensitive). The DB has
    # historic duplicates (e.g. abs + eq_abs same display_name) and prefer prefixed
    # keys; if the LLM still returns both, keep the prefixed variant once.
    seen_names: set[str] = set()
    deduped_features: list[dict[str, Any]] = []
    deduped_legacy: list[dict[str, Any]] = []
    legacy_keys = {f["feature_key"] for f in legacy_filters}
    duplicate_count = 0

    def _is_prefixed_key(k: str) -> bool:
        return any(k.startswith(p) for p in ("eq_", "spec_", "dim_", "opt_"))

    for feat in sorted(
        extracted_features,
        key=lambda f: (0 if _is_prefixed_key(f["feature_key"]) else 1),
    ):
        name_norm = (feat.get("display_name") or feat["feature_key"]).strip().lower()
        if name_norm in seen_names:
            duplicate_count += 1
            continue
        seen_names.add(name_norm)
        deduped_features.append(feat)
        if feat["feature_key"] in legacy_keys:
            deduped_legacy.append(
                {"feature_key": feat["feature_key"], "value_bool": True}
            )

    if duplicate_count > 0:
        logger.info(
            "Reverse Search extraction de-duplicated %d entries by display_name",
            duplicate_count,
        )

    return {
        "status": "success",
        "extracted_features": deduped_features,
        "extracted_filters": deduped_legacy,
        "extracted_financials": {
            "price_max": json_resp.get("price_max"),
            "duration_months": json_resp.get("duration_months"),
            "annual_mileage": json_resp.get("annual_mileage"),
        },
        "total_extracted": len(deduped_features),
        "transcript": json_resp.get("transcript"),
        "rejected_count": len(rejected),
        "deduplicated_count": duplicate_count,
    }


@router.post("/features/extract-text")
def extract_features_from_text(
    request: FeatureExtractionRequest,
) -> dict[str, Any]:
    """Extract structured feature filters from raw text using LLM."""
    import json
    from google.genai import types
    from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
    from core.reverse_search_llm import ExtractedReverseSearchFeatures
    from core.reverse_search_prompt import build_reverse_search_prompt

    if not request.query_text or not request.query_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Tekst do analizy nie może być pusty.",
        )

    client = get_gemini_client()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=request.query_text,
            config=types.GenerateContentConfig(
                system_instruction=build_reverse_search_prompt(),
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=ExtractedReverseSearchFeatures,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        if not response.text:
            raise ValueError("Pusta odpowiedź od modelu językowego.")

        return _build_extraction_response(json.loads(response.text))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Błąd podczas analizy tekstu przez LLM: %s", getattr(e, "message", str(e))
        )
        raise HTTPException(
            status_code=500,
            detail=f"Analiza tekstu AI nie powiodła się: {e}",
        )


@router.post("/features/extract-audio")
async def extract_features_from_audio(
    audio: UploadFile = File(...),
) -> dict[str, Any]:
    """Extract structured feature filters from a Polish voice recording.

    Audio is processed in-memory only and forwarded directly to Gemini 2.5 Flash,
    which natively transcribes + extracts features in a single inference. Nothing
    is persisted to disk or database.
    """
    import json
    from google.genai import types
    from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
    from core.reverse_search_llm import ExtractedReverseSearchFeatures
    from core.reverse_search_prompt import build_reverse_search_prompt

    mime_type = (audio.content_type or "").split(";")[0].strip().lower()
    if mime_type not in _ALLOWED_AUDIO_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Nieobsługiwany format audio: {audio.content_type or 'brak'}",
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Nagranie audio jest puste.")
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Nagranie zbyt duże (max {_MAX_AUDIO_BYTES // (1024 * 1024)} MB).",
        )

    client = get_gemini_client()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                system_instruction=build_reverse_search_prompt(),
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=ExtractedReverseSearchFeatures,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        if not response.text:
            raise ValueError("Pusta odpowiedź od modelu językowego.")

        return _build_extraction_response(json.loads(response.text))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Błąd podczas analizy audio przez LLM: %s", getattr(e, "message", str(e))
        )
        raise HTTPException(
            status_code=500,
            detail=f"Analiza audio AI nie powiodła się: {e}",
        )


_ALLOWED_EMAIL_EXTENSIONS = {".msg", ".eml"}
_MAX_EMAIL_BYTES = 10 * 1024 * 1024  # 10 MB


def _extract_text_from_msg(file_bytes: bytes) -> tuple[str, str]:
    """Parse Outlook .msg file and return (subject, body)."""
    import io
    import extract_msg  # type: ignore[import-untyped]

    msg = extract_msg.openMsg(io.BytesIO(file_bytes))
    try:
        subject: str = msg.subject or ""
        body: str = msg.body or ""
        return subject.strip(), body.strip()
    finally:
        msg.close()


def _extract_text_from_eml(file_bytes: bytes) -> tuple[str, str]:
    """Parse RFC-2822 .eml file and return (subject, body)."""
    import email as email_lib
    from email.header import decode_header

    msg = email_lib.message_from_bytes(file_bytes)

    # Decode subject
    raw_subject = msg.get("Subject", "")
    decoded_parts = decode_header(raw_subject)
    subject_parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            subject_parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            subject_parts.append(part)
    subject = "".join(subject_parts).strip()

    # Extract plain-text body
    body_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_parts.append(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body_parts.append(payload.decode(charset, errors="replace"))

    body = "\n".join(body_parts).strip()
    return subject, body


@router.post("/features/extract-email-file")
async def extract_features_from_email_file(
    email_file: UploadFile = File(...),
) -> dict[str, Any]:
    """Extract structured car-search features from an Outlook .msg or .eml email file.

    The email is parsed in-memory only. Subject + body are concatenated and forwarded
    to Gemini 2.5 Flash using the same reverse-search prompt as extract-text.
    Nothing is persisted to disk or database.
    """
    import json
    from pathlib import Path
    from google.genai import types
    from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
    from core.reverse_search_llm import ExtractedReverseSearchFeatures
    from core.reverse_search_prompt import build_reverse_search_prompt

    filename = email_file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EMAIL_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Nieobsługiwany format pliku: '{ext}'. Akceptowane: .msg, .eml",
        )

    file_bytes = await email_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Plik e-mail jest pusty.")
    if len(file_bytes) > _MAX_EMAIL_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Plik zbyt duży (max {_MAX_EMAIL_BYTES // (1024 * 1024)} MB).",
        )

    try:
        if ext == ".msg":
            subject, body = _extract_text_from_msg(file_bytes)
        else:
            subject, body = _extract_text_from_eml(file_bytes)
    except Exception as e:
        logger.exception("Błąd parsowania pliku email: %s", e)
        raise HTTPException(
            status_code=422,
            detail=f"Nie udało się odczytać pliku e-mail: {e}",
        )

    email_text = f"Temat: {subject}\n\n{body}" if subject else body
    if not email_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Plik e-mail nie zawiera tekstu do analizy.",
        )

    client = get_gemini_client()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=email_text,
            config=types.GenerateContentConfig(
                system_instruction=build_reverse_search_prompt(),
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=ExtractedReverseSearchFeatures,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        if not response.text:
            raise ValueError("Pusta odpowiedź od modelu językowego.")

        result = _build_extraction_response(json.loads(response.text))
        result["email_subject"] = subject
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Błąd podczas analizy e-mail przez LLM: %s", getattr(e, "message", str(e))
        )
        raise HTTPException(
            status_code=500,
            detail=f"Analiza e-mail AI nie powiodła się: {e}",
        )


# ── Reverse Search ─────────────────────────────────────────────


@router.post("/features/search")
def reverse_search_vehicles(
    request: FeatureSearchRequest,
) -> FeatureSearchResponse:
    """Search vehicles by feature criteria.

    Filters on vehicle_specs_normalized joined with vehicle_synthesis.
    """
    sb = supabase

    if (
        not request.search_query
        and not request.filters
        and not request.body_types
        and request.vehicle_scope == "all"
    ):
        raise HTTPException(
            status_code=400,
            detail="Przynajmniej jeden filtr cechy, wyszukiwanie tekstowe, typ zabudowy lub kategoria pojazdu jest wymagana",
        )

    # 1. Base Scope and Body Type Filtering (STRICT) -> returns valid_vehicle_ids
    # Text search is now pushed entirely to the database via p_search_query
    valid_vehicle_ids: list[str] | None = None

    if request.body_types or (request.vehicle_scope and request.vehicle_scope != "all"):
        all_synthesis_data = []
        page_size = 900
        offset = 0
        while True:
            bt_resp = (
                sb.table("vehicle_synthesis")
                .select("id, synthesis_data")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            data = bt_resp.data or []
            all_synthesis_data.extend(data)
            if len(data) < page_size:
                break
            offset += page_size

        filtered_ids = set()

        for r in all_synthesis_data:
            sd = r.get("synthesis_data") or {}
            cs = sd.get("card_summary") or {}
            mapped = sd.get("mapped_ai_data") or {}

            # Scope Check
            scope_matches = True
            if request.vehicle_scope and request.vehicle_scope != "all":
                v_type = str(
                    cs.get("vehicle_type", "")
                    or cs.get("vehicle_class", "")
                    or mapped.get("vehicle_type", "")
                    or mapped.get("vehicle_class", "")
                    or ""
                ).upper()

                if request.vehicle_scope == "commercial":
                    scope_matches = (
                        "DOSTAWCZ" in v_type
                        or "CIĘŻAROW" in v_type
                        or "CIEZAROW" in v_type
                    )
                elif request.vehicle_scope == "passenger":
                    scope_matches = "OSOBOW" in v_type

            # Body Type Check
            body_matches = True
            if request.body_types:
                vals = [
                    str(x).upper()
                    for x in [
                        cs.get("body_style", ""),
                        mapped.get("body_style", ""),
                        sd.get("nadwozie", ""),
                        sd.get("samar_body_type", ""),
                        sd.get("samar_body_style", ""),
                        sd.get("rodzaj_zabudowy", ""),
                    ]
                    if x
                ]

                if not vals:
                    body_matches = False
                else:
                    body_matches = any(
                        any(req_bt.upper() in v for v in vals)
                        for req_bt in request.body_types
                    )

            if scope_matches and body_matches:
                filtered_ids.add(r["id"])

        valid_vehicle_ids = list(filtered_ids)
        if not valid_vehicle_ids:
            return FeatureSearchResponse(results=[], total_count=0, facets={})

    # 2. Map frontend filters to p_requirements JSON
    p_reqs: list[dict[str, Any]] = []

    if request.filters:
        for flt in request.filters:
            # By default eq constraint
            op = "eq"
            val: Any = None
            if flt.value_bool is not None:
                op = "eq"
                val = str(flt.value_bool).lower()  # true/false string
            elif flt.value_text is not None:
                op = "ilike"  # use ilike for text if possible, or eq
                val = flt.value_text
            elif flt.value_num_min is not None and flt.value_num_max is not None:
                # the RPC handles min/max separately by operator if mapped as two items
                p_reqs.append(
                    {
                        "feature_key": flt.feature_key,
                        "operator": "gte",
                        "value": str(flt.value_num_min),
                        "weight": 1.0,
                        "requirement": "NICE_TO_HAVE",
                    }
                )
                p_reqs.append(
                    {
                        "feature_key": flt.feature_key,
                        "operator": "lte",
                        "value": str(flt.value_num_max),
                        "weight": 1.0,
                        "requirement": "NICE_TO_HAVE",
                    }
                )
                continue
            elif flt.value_num_min is not None:
                op = "gte"
                val = str(flt.value_num_min)
            elif flt.value_num_max is not None:
                op = "lte"
                val = str(flt.value_num_max)

            if val is not None:
                p_reqs.append(
                    {
                        "feature_key": flt.feature_key,
                        "operator": op,
                        "value": val,
                        "weight": 1.0,
                        "requirement": "NICE_TO_HAVE",
                    }
                )

    # 3. Add Pricing / Margin requirements
    if request.price_months is not None:
        p_reqs.append(
            {
                "feature_key": "duration_months",
                "operator": "eq",
                "value": str(request.price_months),
                "weight": 0,
            }
        )
    if request.price_mileage is not None:
        p_reqs.append(
            {
                "feature_key": "annual_mileage",
                "operator": "eq",
                "value": str(request.price_mileage),
                "weight": 0,
            }
        )
    if request.price_margin_pct is not None and request.price_margin_pct != "":
        p_reqs.append(
            {
                "feature_key": "margin_pct",
                "operator": "eq",
                "value": str(request.price_margin_pct),
                "weight": 0,
            }
        )

    # Ensure price limits are passed to filter in RPC
    if request.price_min is not None and request.price_min != "":
        p_reqs.append(
            {
                "feature_key": "monthly_price_net",
                "operator": "gte",
                "value": str(request.price_min),
                "weight": 1.0,
            }
        )
    if request.price_max is not None and request.price_max != "":
        p_reqs.append(
            {
                "feature_key": "monthly_price_net",
                "operator": "lte",
                "value": str(request.price_max),
                "weight": 1.0,
            }
        )

    # 4. Call rpc_reverse_search via HTTP to specify the schema
    rpc_payload = {
        "p_requirements": p_reqs,
    }
    if request.search_query:
        rpc_payload["p_search_query"] = request.search_query

        # Generation of semantic vector for Hybrid Search
        try:
            from core.embeddings import generate_embedding

            query_vector = generate_embedding(request.search_query)
            if query_vector:
                rpc_payload["p_semantic_query_vector"] = (
                    f"[{','.join(str(v) for v in query_vector)}]"
                )
        except Exception as e:
            logger.warning(
                f"Semantic Search Error: Failed to generate query vector: {e}"
            )

    if valid_vehicle_ids is not None:
        rpc_payload["p_vehicle_ids"] = valid_vehicle_ids

    import httpx

    # We must call the reverse_search schema explicitly because supabase-py defaults to public for RPCs
    response = httpx.post(
        f"{sb.supabase_url}/rest/v1/rpc/rpc_reverse_search",
        headers={
            "apikey": sb.supabase_key,
            "Authorization": f"Bearer {sb.supabase_key}",
            "Accept-Profile": "reverse_search",
            "Content-Profile": "reverse_search",
        },
        json=rpc_payload,
        timeout=30.0,
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"RPC Error: {response.text}")

    rpc_data = response.json() or []

    total_requested_features = len(request.filters) if request.filters else 0

    results: list[FeatureSearchResultItem] = []

    # Map RPC output to FeatureSearchResultItem
    # rpc_reverse_search returns top 200, we apply pagination limit/offset here
    paginated_data = rpc_data[request.offset : request.offset + request.limit]

    for row in paginated_data:
        matched_raw = row.get("matched_features") or []
        missing_raw = row.get("missing_features") or []
        matched_keys = [k for k in matched_raw if isinstance(k, str)] if isinstance(matched_raw, list) else []
        missing_keys = [k for k in missing_raw if isinstance(k, str)] if isinstance(missing_raw, list) else []

        score = (
            row.get("match_score_pct", 0) / 100.0 if row.get("match_score_pct") else 0
        )

        score_features_pct = row.get("score_features_pct")
        score_semantic = row.get("score_semantic")

        results.append(
            FeatureSearchResultItem(
                source_vehicle_id=row["vehicle_id"],
                brand=row["brand"],
                model=row["model"],
                matched_features=len(matched_keys),
                total_filters=total_requested_features,
                match_score=score,
                price_netto=row.get("best_monthly_price"),
                matched_feature_keys=matched_keys,
                missing_feature_keys=missing_keys,
                score_features_pct=float(score_features_pct) if score_features_pct is not None else None,
                score_semantic=float(score_semantic) if score_semantic is not None else None,
            )
        )

    # 5. Calculate Facets from the first 150 IDs for speed
    facets: dict[str, int] = {}
    result_ids_list = [r["vehicle_id"] for r in rpc_data]

    if result_ids_list:
        chunk = result_ids_list[:150]
        facet_resp = (
            sb.schema("reverse_search")
            .table("vehicle_specs_normalized")
            .select("feature_id, universal_features!inner(feature_key)")
            .in_("vehicle_id", chunk)
            .eq("value_bool", True)
            .in_(
                "resolved_status",
                [
                    "present_confirmed_primary",
                    "present_confirmed_secondary",
                    "present_inferred",
                ],
            )
            .execute()
        )

        for r in facet_resp.data:
            uf = r.get("universal_features")
            if uf and isinstance(uf, dict):
                f_key = uf.get("feature_key")
                if f_key:
                    facets[f_key] = facets.get(f_key, 0) + 1

    return FeatureSearchResponse(
        results=results,
        total_count=len(rpc_data),
        facets=facets,
    )


# ── Saved Filter Sets ─────────────────────────────────────────


class SavedFilterUpsert(BaseModel):
    name: str
    description: str | None = None
    filter_state: dict[str, Any]
    user_email: str | None = None


class SavedFilterItem(BaseModel):
    id: str
    user_email: str | None = None
    name: str
    description: str | None = None
    filter_state: dict[str, Any]
    created_at: str
    updated_at: str


@router.get("/reverse-search/saved-filters")
def list_saved_filters(user_email: str | None = None) -> list[SavedFilterItem]:
    """List saved filter sets, optionally scoped to a user."""
    query = (
        supabase
        .table("reverse_search_saved_filters")
        .select("*")
        .order("updated_at", desc=True)
    )
    if user_email:
        query = query.eq("user_email", user_email)
    resp = query.execute()
    return [SavedFilterItem(**row) for row in (resp.data or [])]


@router.post("/reverse-search/saved-filters")
def upsert_saved_filter(payload: SavedFilterUpsert) -> SavedFilterItem:
    """Create or update a saved filter set keyed by (user_email, name)."""
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Nazwa nie może być pusta.")
    if not isinstance(payload.filter_state, dict):
        raise HTTPException(status_code=400, detail="filter_state musi być obiektem.")

    name = payload.name.strip()
    user_email = payload.user_email.strip() if payload.user_email else None

    existing_q = (
        supabase
        .table("reverse_search_saved_filters")
        .select("id")
        .eq("name", name)
    )
    if user_email:
        existing_q = existing_q.eq("user_email", user_email)
    else:
        existing_q = existing_q.is_("user_email", "null")
    existing = existing_q.execute()

    row_payload = {
        "name": name,
        "description": payload.description,
        "filter_state": payload.filter_state,
        "user_email": user_email,
    }

    if existing.data:
        existing_id = existing.data[0]["id"]
        upd = (
            supabase
            .table("reverse_search_saved_filters")
            .update(row_payload)
            .eq("id", existing_id)
            .execute()
        )
        if not upd.data:
            raise HTTPException(status_code=500, detail="Nie udało się zapisać filtra.")
        return SavedFilterItem(**upd.data[0])

    ins = (
        supabase
        .table("reverse_search_saved_filters")
        .insert(row_payload)
        .execute()
    )
    if not ins.data:
        raise HTTPException(status_code=500, detail="Nie udało się utworzyć filtra.")
    return SavedFilterItem(**ins.data[0])


@router.delete("/reverse-search/saved-filters/{filter_id}")
def delete_saved_filter(filter_id: str) -> dict[str, Any]:
    """Delete a saved filter set by id."""
    resp = (
        supabase
        .table("reverse_search_saved_filters")
        .delete()
        .eq("id", filter_id)
        .execute()
    )
    deleted = len(resp.data or [])
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Nie znaleziono zapisanego filtra.")
    return {"status": "deleted", "id": filter_id}


# ── Brochure Features ─────────────────────────────────────────


@router.get("/features/brochure/{vehicle_id}")
def get_features_brochure(
    vehicle_id: str,
) -> dict[str, Any]:
    """Get features formatted for brochure."""
    sb = supabase

    resp = (
        sb.schema("reverse_search")
        .table("universal_features_brochure_view")
        .select("*")
        .eq("source_vehicle_id", vehicle_id)
        .execute()
    )

    return {
        "vehicle_id": vehicle_id,
        "categories": resp.data,
    }


# ── Feature Enrichment ────────────────────────────────────────


@router.post("/features/vehicle/{vehicle_id}/enrich")
async def enrich_single_vehicle(
    vehicle_id: str,
) -> dict[str, Any]:
    """Enrich a single vehicle with features from card_summary."""
    sb = supabase

    resp = (
        sb.table("vehicle_synthesis")
        .select("id, synthesis_data")
        .eq("id", vehicle_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicle {vehicle_id} not found",
        )

    synthesis = resp.data[0].get("synthesis_data")
    if not isinstance(synthesis, dict):
        raise HTTPException(
            status_code=400,
            detail="Vehicle has no synthesis_data",
        )

    result = await enrich_vehicle_features(vehicle_id, synthesis)
    return result


@router.post("/features/vehicle/{vehicle_id}/enrich-background")
def enrich_vehicle_background(
    vehicle_id: str,
) -> dict[str, Any]:
    """Trigger background CELERY task to enrich vehicle features from documents."""
    from tasks.enrichment_tasks import enrich_vehicle_features_from_catalog

    task = enrich_vehicle_features_from_catalog.delay(vehicle_id)

    return {"status": "queued", "vehicle_id": vehicle_id, "task_id": task.id}
