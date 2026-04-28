"""Tests for POST /api/features/extract-audio.

Mocks the Gemini call and the live catalog loader; exercises validation paths.
"""
from __future__ import annotations

import os

# Ensure required env vars exist before main.py is imported (worktree has no .env).
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import json  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def _mock_gemini_text_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.text = json.dumps(payload)
    return response


def _make_catalog_entry(**kwargs):
    from core.feature_catalog_loader import CatalogFeatureEntry

    defaults = dict(
        feature_key="abs",
        display_name="ABS",
        feature_type="boolean",
        category_name="Bezpieczeństwo i ADAS",
    )
    defaults.update(kwargs)
    return CatalogFeatureEntry(**defaults)


CATALOG_LOOKUP = {
    "abs": _make_catalog_entry(feature_key="abs", display_name="ABS", feature_type="boolean"),
    "tow_hitch": _make_catalog_entry(feature_key="tow_hitch", display_name="Hak", feature_type="boolean"),
    "klimatyzacja": _make_catalog_entry(
        feature_key="klimatyzacja", display_name="Klimatyzacja", feature_type="boolean"
    ),
    "cargo_volume": _make_catalog_entry(
        feature_key="cargo_volume",
        display_name="Pojemność ładunkowa",
        feature_type="numeric",
        canonical_unit="m³",
    ),
    "exterior_color": _make_catalog_entry(
        feature_key="exterior_color",
        display_name="Kolor zewnętrzny",
        feature_type="text",
    ),
    "drive_type": _make_catalog_entry(
        feature_key="drive_type",
        display_name="Napęd",
        feature_type="enum",
        allowed_values=["FWD", "RWD", "AWD"],
    ),
}


GEMINI_PAYLOAD_OK = {
    "features": [
        {"feature_key": "abs", "op": "eq", "value_bool": True},
        {"feature_key": "tow_hitch", "op": "eq", "value_bool": True},
        {"feature_key": "klimatyzacja", "op": "eq", "value_bool": True},
        {"feature_key": "cargo_volume", "op": "gte", "value_num": 5.0},
        {"feature_key": "exterior_color", "op": "eq", "value_text": "biały"},
    ],
    "price_max": 2500,
    "duration_months": 48,
    "annual_mileage": 30000,
    "transcript": "Potrzebuję dostawczaka z hakiem, klimatyzacja, ładowność min 5 m³, biały, rata do 2500.",
}


def test_extract_audio_success_multi_type() -> None:
    fake_audio = b"\x1aE\xdf\xa3" + b"\x00" * 1024
    with patch("core.gemini_client.get_gemini_client") as mock_client_factory, patch(
        "core.feature_catalog_loader.get_feature_lookup", return_value=CATALOG_LOOKUP) as _, patch("core.reverse_search_prompt.build_reverse_search_prompt", return_value="STUB_PROMPT"
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _mock_gemini_text_response(
            GEMINI_PAYLOAD_OK
        )
        mock_client_factory.return_value = mock_client

        response = client.post(
            "/api/features/extract-audio",
            files={"audio": ("clip.webm", fake_audio, "audio/webm")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["total_extracted"] == 5
    assert body["rejected_count"] == 0

    by_key = {f["feature_key"]: f for f in body["extracted_features"]}
    assert by_key["abs"]["feature_type"] == "boolean"
    assert by_key["abs"]["value_bool"] is True

    assert by_key["cargo_volume"]["feature_type"] == "numeric"
    assert by_key["cargo_volume"]["op"] == "gte"
    assert by_key["cargo_volume"]["value_num"] == 5.0
    assert by_key["cargo_volume"]["canonical_unit"] == "m³"

    assert by_key["exterior_color"]["feature_type"] == "text"
    assert by_key["exterior_color"]["value_text"] == "biały"

    legacy = {f["feature_key"]: f for f in body["extracted_filters"]}
    assert "abs" in legacy and legacy["abs"]["value_bool"] is True
    assert "cargo_volume" not in legacy

    assert body["extracted_financials"]["price_max"] == 2500
    assert body["extracted_financials"]["annual_mileage"] == 30000
    assert "5 m" in body["transcript"]


def test_extract_audio_drops_unknown_feature_keys() -> None:
    fake_audio = b"\x00" * 256
    payload = {
        "features": [
            {"feature_key": "abs", "op": "eq", "value_bool": True},
            {"feature_key": "rocznik_2021", "op": "eq", "value_bool": True},
            {"feature_key": "production_year", "op": "gte", "value_num": 2021},
        ],
        "transcript": "rocznik 2021 z ABS",
    }
    with patch("core.gemini_client.get_gemini_client") as mock_client_factory, patch(
        "core.feature_catalog_loader.get_feature_lookup", return_value=CATALOG_LOOKUP) as _, patch("core.reverse_search_prompt.build_reverse_search_prompt", return_value="STUB_PROMPT"
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _mock_gemini_text_response(payload)
        mock_client_factory.return_value = mock_client

        response = client.post(
            "/api/features/extract-audio",
            files={"audio": ("clip.webm", fake_audio, "audio/webm")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_extracted"] == 1
    assert body["rejected_count"] == 2
    assert body["extracted_features"][0]["feature_key"] == "abs"


def test_extract_audio_drops_type_mismatch() -> None:
    fake_audio = b"\x00" * 256
    payload = {
        "features": [
            {"feature_key": "abs", "op": "gte", "value_num": 1.0},
            {"feature_key": "cargo_volume", "op": "eq", "value_bool": True},
            {"feature_key": "exterior_color", "op": "eq", "value_text": "   "},
        ],
    }
    with patch("core.gemini_client.get_gemini_client") as mock_client_factory, patch(
        "core.feature_catalog_loader.get_feature_lookup", return_value=CATALOG_LOOKUP) as _, patch("core.reverse_search_prompt.build_reverse_search_prompt", return_value="STUB_PROMPT"
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _mock_gemini_text_response(payload)
        mock_client_factory.return_value = mock_client

        response = client.post(
            "/api/features/extract-audio",
            files={"audio": ("clip.webm", fake_audio, "audio/webm")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_extracted"] == 0
    assert body["rejected_count"] == 3


def test_extract_audio_enum_value_validated() -> None:
    fake_audio = b"\x00" * 256
    payload = {
        "features": [
            {"feature_key": "drive_type", "op": "eq", "value_text": "AWD"},
            {"feature_key": "drive_type", "op": "eq", "value_text": "fioletowy"},
        ],
    }
    with patch("core.gemini_client.get_gemini_client") as mock_client_factory, patch(
        "core.feature_catalog_loader.get_feature_lookup", return_value=CATALOG_LOOKUP) as _, patch("core.reverse_search_prompt.build_reverse_search_prompt", return_value="STUB_PROMPT"
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _mock_gemini_text_response(payload)
        mock_client_factory.return_value = mock_client

        response = client.post(
            "/api/features/extract-audio",
            files={"audio": ("clip.webm", fake_audio, "audio/webm")},
        )

    body = response.json()
    assert body["total_extracted"] == 1
    assert body["extracted_features"][0]["value_text"] == "AWD"
    assert body["rejected_count"] == 1


def test_extract_audio_dedupes_duplicate_display_names() -> None:
    """LLM may return both `abs` and `eq_abs` (same ABS concept). Backend dedupes
    keeping the prefixed variant."""
    catalog_with_dups = {
        **CATALOG_LOOKUP,
        "abs": _make_catalog_entry(
            feature_key="abs", display_name="ABS", feature_type="boolean"
        ),
        "eq_abs": _make_catalog_entry(
            feature_key="eq_abs", display_name="ABS", feature_type="boolean"
        ),
    }
    payload = {
        "features": [
            {"feature_key": "abs", "op": "eq", "value_bool": True},
            {"feature_key": "eq_abs", "op": "eq", "value_bool": True},
            {"feature_key": "tow_hitch", "op": "eq", "value_bool": True},
        ],
    }
    fake_audio = b"\x00" * 256
    with patch("core.gemini_client.get_gemini_client") as mock_client_factory, patch(
        "core.feature_catalog_loader.get_feature_lookup", return_value=catalog_with_dups) as _, patch("core.reverse_search_prompt.build_reverse_search_prompt", return_value="STUB_PROMPT"
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _mock_gemini_text_response(payload)
        mock_client_factory.return_value = mock_client

        response = client.post(
            "/api/features/extract-audio",
            files={"audio": ("clip.webm", fake_audio, "audio/webm")},
        )

    body = response.json()
    assert body["total_extracted"] == 2
    assert body["deduplicated_count"] == 1
    keys = [f["feature_key"] for f in body["extracted_features"]]
    assert "eq_abs" in keys, "Prefixed variant should win over naked"
    assert "abs" not in keys
    assert "tow_hitch" in keys


def test_extract_audio_legacy_matched_features_still_works() -> None:
    fake_audio = b"\x00" * 256
    payload = {
        "matched_features": ["abs", "tow_hitch", "rocznik_xx"],
        "price_max": 2000,
    }
    with patch("core.gemini_client.get_gemini_client") as mock_client_factory, patch(
        "core.feature_catalog_loader.get_feature_lookup", return_value=CATALOG_LOOKUP) as _, patch("core.reverse_search_prompt.build_reverse_search_prompt", return_value="STUB_PROMPT"
    ):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _mock_gemini_text_response(payload)
        mock_client_factory.return_value = mock_client

        response = client.post(
            "/api/features/extract-audio",
            files={"audio": ("clip.webm", fake_audio, "audio/webm")},
        )

    body = response.json()
    assert body["total_extracted"] == 2
    assert body["rejected_count"] == 1
    assert body["extracted_financials"]["price_max"] == 2000


def test_extract_audio_rejects_unsupported_mime() -> None:
    response = client.post(
        "/api/features/extract-audio",
        files={"audio": ("clip.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_extract_audio_rejects_empty_body() -> None:
    response = client.post(
        "/api/features/extract-audio",
        files={"audio": ("clip.webm", b"", "audio/webm")},
    )
    assert response.status_code == 400


def test_extract_audio_rejects_oversized_payload() -> None:
    huge = b"\x00" * (25 * 1024 * 1024 + 1)
    response = client.post(
        "/api/features/extract-audio",
        files={"audio": ("clip.webm", huge, "audio/webm")},
    )
    assert response.status_code == 413


def test_extract_audio_500_when_gemini_returns_empty() -> None:
    fake_audio = b"\x00" * 256
    with patch("core.gemini_client.get_gemini_client") as mock_client_factory:
        mock_client = MagicMock()
        empty = MagicMock()
        empty.text = ""
        mock_client.models.generate_content.return_value = empty
        mock_client_factory.return_value = mock_client

        response = client.post(
            "/api/features/extract-audio",
            files={"audio": ("clip.webm", fake_audio, "audio/webm")},
        )

    assert response.status_code == 500
