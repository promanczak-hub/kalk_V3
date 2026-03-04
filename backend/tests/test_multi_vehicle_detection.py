"""
Tests for the multi-vehicle detection and splitting pipeline.

Covers:
- detect_vehicle_count: returns 1 for single-vehicle, N for multi-vehicle
- extract_multi_vehicle_twins: returns list of twin dicts
- detect_and_split_vehicles: returns None for single, list for multi
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from core.pipeline_multi_vehicle import (
    detect_and_split_vehicles,
    detect_vehicle_count,
    extract_multi_vehicle_twins,
)


class FakeResponse:
    """Minimal mock for Gemini response."""

    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture()
def _patch_client():
    """Patch the Gemini client builder."""
    with patch("core.pipeline_multi_vehicle._build_gemini_client") as mock_builder:
        mock_client = MagicMock()
        mock_builder.return_value = mock_client
        yield mock_client


class TestDetectVehicleCount:
    """Tests for the lightweight vehicle-count probe."""

    def test_returns_1_for_single_vehicle(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse("1")
        result = detect_vehicle_count(b"fake_pdf_bytes", "application/pdf")
        assert result == 1

    def test_returns_3_for_multi_vehicle(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse("3")
        result = detect_vehicle_count(b"fake_pdf_bytes", "application/pdf")
        assert result == 3

    def test_returns_1_on_parse_error(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse(
            "not a number"
        )
        result = detect_vehicle_count(b"fake_pdf_bytes", "application/pdf")
        assert result == 1

    def test_returns_1_on_empty_response(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse("")
        result = detect_vehicle_count(b"fake_pdf_bytes", "application/pdf")
        assert result == 1

    def test_returns_1_on_exception(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.side_effect = RuntimeError("API down")
        result = detect_vehicle_count(b"fake_pdf_bytes", "application/pdf")
        assert result == 1

    def test_returns_1_for_zero(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse("0")
        result = detect_vehicle_count(b"fake_pdf_bytes", "application/pdf")
        assert result == 1


class TestExtractMultiVehicleTwins:
    """Tests for Gemini Pro multi-twin extraction."""

    def test_returns_vehicles_list(self, _patch_client: MagicMock) -> None:
        payload = {
            "vehicle_count": 2,
            "vehicles": [
                {"brand": "Renault", "model": "Clio", "digital_twin": {"price": 100}},
                {"brand": "Dacia", "model": "Sandero", "digital_twin": {"price": 80}},
            ],
        }
        _patch_client.models.generate_content.return_value = FakeResponse(
            json.dumps(payload)
        )

        result = extract_multi_vehicle_twins(b"bytes", "application/pdf", 2)
        assert len(result) == 2
        assert result[0]["brand"] == "Renault"
        assert result[1]["brand"] == "Dacia"

    def test_returns_empty_on_no_vehicles_key(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse(
            json.dumps({"vehicle_count": 0})
        )
        result = extract_multi_vehicle_twins(b"bytes", "application/pdf", 2)
        assert result == []

    def test_returns_empty_on_json_error(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse(
            "not valid json"
        )
        result = extract_multi_vehicle_twins(b"bytes", "application/pdf", 2)
        assert result == []

    def test_returns_empty_on_exception(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.side_effect = RuntimeError("boom")
        result = extract_multi_vehicle_twins(b"bytes", "application/pdf", 2)
        assert result == []


class TestDetectAndSplitVehicles:
    """Integration tests for the main entry point."""

    def test_returns_none_for_single_vehicle(self, _patch_client: MagicMock) -> None:
        _patch_client.models.generate_content.return_value = FakeResponse("1")
        result = detect_and_split_vehicles(b"bytes", "application/pdf")
        assert result is None

    def test_returns_list_for_multi_vehicle(self, _patch_client: MagicMock) -> None:
        # First call: detect_vehicle_count returns 3
        # Second call: extract_multi_vehicle_twins returns 3 twins
        payload = {
            "vehicle_count": 3,
            "vehicles": [
                {"brand": "A", "model": "1", "digital_twin": {}},
                {"brand": "B", "model": "2", "digital_twin": {}},
                {"brand": "C", "model": "3", "digital_twin": {}},
            ],
        }

        _patch_client.models.generate_content.side_effect = [
            FakeResponse("3"),
            FakeResponse(json.dumps(payload)),
        ]

        result = detect_and_split_vehicles(b"bytes", "application/pdf")
        assert result is not None
        assert len(result) == 3

    def test_falls_back_to_none_when_pro_fails(self, _patch_client: MagicMock) -> None:
        # Flash says 5 vehicles, but Pro fails
        _patch_client.models.generate_content.side_effect = [
            FakeResponse("5"),
            FakeResponse("invalid json"),
        ]

        result = detect_and_split_vehicles(b"bytes", "application/pdf")
        assert result is None
