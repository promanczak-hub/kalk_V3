"""Tests for V3 HITL endpoints: /move_item, /update_item, /split_item.

Mocks supabase + _direct_update_synthesis like test_hitl_endpoints.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


def _base_synthesis() -> dict:
    return {
        "card_summary": {
            "base_price": "100000 PLN netto",
            "base_price_net": 100000.0,
            "base_price_gross": 123000.0,
            "base_price_vat": 0.23,
            # Non-zero options_price to avoid divide-by-zero in legacy validator
            "options_price": "47970 PLN netto",
            "total_price": "147970 PLN netto",
            "paid_options": [
                {
                    "name": "Zabudowa izoterma",
                    "price": "47970 PLN netto",
                    "price_type": "netto",
                    "category": "Serwisowa/Akcesoria",
                    "confidence": 0.5,
                    "field_id": "po-zab",
                    "net_amount": 47970.0,
                    "gross_amount": 59003.1,
                    "vat_rate": 0.23,
                    "canonical_id": "",
                    "duplicate_of": None,
                },
            ],
            "service_equipment": None,
        },
        "brand": "Renault",
        "model": "Master",
    }


def _mock_supabase(synthesis: dict):
    """Mock that returns a FRESH deepcopy per execute() call.

    Critical for rerunfailures retries — endpoints mutate the synthesis
    dict, so each invocation must see the original baseline.
    """
    import copy as _copy

    def _fresh_data(*_args, **_kwargs):
        return MagicMock(data={
            "id": "veh-1",
            "synthesis_data": _copy.deepcopy(synthesis),
        })

    mock_execute = MagicMock(side_effect=_fresh_data)
    chain_single = MagicMock(execute=mock_execute)
    chain_eq = MagicMock(single=MagicMock(return_value=chain_single))
    chain_select = MagicMock(eq=MagicMock(return_value=chain_eq))
    mock_table = MagicMock(select=MagicMock(return_value=chain_select))
    return MagicMock(table=MagicMock(return_value=mock_table))


@pytest.fixture(autouse=True)
def _mock_externals():
    with patch("api.extract_hitl_v3_routes._persist") as mock_persist, \
         patch("core.pipeline_price_validator.generate_price_summary", return_value={"text": "ok"}):
        yield {"persist": mock_persist}


# ─────────────────────────────────────────────────────────────────────
# /move_item
# ─────────────────────────────────────────────────────────────────────


class TestMoveItem:
    def test_move_paid_option_to_service_equipment(self) -> None:
        synth = _base_synthesis()
        with patch("api.extract_routes.supabase_client", _mock_supabase(synth)):
            r = client.post(
                "/api/extract/hitl/move_item/veh-1",
                json={
                    "src_path": "paid_options[0]",
                    "dst_path": "service_equipment.components",
                },
            )
        assert r.status_code == 200, r.text
        card = r.json()["card_summary"]
        # paid_options is now empty
        assert card["paid_options"] == []
        # service_equipment got the component
        comps = card["service_equipment"]["components"]
        assert len(comps) == 1
        assert comps[0]["name"] == "Zabudowa izoterma"
        assert comps[0]["net_amount"] == 47970.0

    def test_move_with_new_category(self) -> None:
        synth = _base_synthesis()
        with patch("api.extract_routes.supabase_client", _mock_supabase(synth)):
            r = client.post(
                "/api/extract/hitl/move_item/veh-1",
                json={
                    "src_path": "paid_options[0]",
                    "dst_path": "paid_options",
                    "new_category": "Fabryczna",
                },
            )
        assert r.status_code == 200
        card = r.json()["card_summary"]
        assert card["paid_options"][0]["category"] == "Fabryczna"

    def test_move_invalid_path_404(self) -> None:
        synth = _base_synthesis()
        with patch("api.extract_routes.supabase_client", _mock_supabase(synth)):
            r = client.post(
                "/api/extract/hitl/move_item/veh-1",
                json={"src_path": "paid_options[99]", "dst_path": "paid_options"},
            )
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────
# /update_item
# ─────────────────────────────────────────────────────────────────────


class TestUpdateItem:
    def test_update_net_amount_recomputes_gross(self) -> None:
        synth = _base_synthesis()
        with patch("api.extract_routes.supabase_client", _mock_supabase(synth)):
            r = client.post(
                "/api/extract/hitl/update_item/veh-1",
                json={
                    "path": "paid_options[0]",
                    "patch": {"net_amount": 50000.0, "gross_amount": None, "vat_rate": 0.23},
                },
            )
        assert r.status_code == 200
        po = r.json()["card_summary"]["paid_options"][0]
        assert po["net_amount"] == 50000.0
        assert po["gross_amount"] == 61500.0  # 50000 × 1.23

    def test_update_name_recomputes_canonical_id(self) -> None:
        synth = _base_synthesis()
        original_canonical = synth["card_summary"]["paid_options"][0].get("canonical_id", "")
        with patch("api.extract_routes.supabase_client", _mock_supabase(synth)):
            r = client.post(
                "/api/extract/hitl/update_item/veh-1",
                json={
                    "path": "paid_options[0]",
                    "patch": {"name": "Zupełnie inna pozycja"},
                },
            )
        assert r.status_code == 200
        po = r.json()["card_summary"]["paid_options"][0]
        assert po["canonical_id"] != original_canonical
        assert po["canonical_id"] != ""


# ─────────────────────────────────────────────────────────────────────
# /split_item
# ─────────────────────────────────────────────────────────────────────


class TestSplitItem:
    def test_split_paid_option_into_two(self) -> None:
        synth = _base_synthesis()
        with patch("api.extract_routes.supabase_client", _mock_supabase(synth)):
            r = client.post(
                "/api/extract/hitl/split_item/veh-1",
                json={
                    "path": "paid_options[0]",
                    "into": [
                        {"name": "Komponent A", "net_amount": 30000.0},
                        {"name": "Komponent B", "net_amount": 17970.0},
                    ],
                },
            )
        assert r.status_code == 200, r.text
        body = r.json()
        # Original paid_options[0] gone, 2 new items added
        card = body["card_summary"]
        names = [o["name"] for o in card.get("paid_options") or []]
        assert "Zabudowa izoterma" not in names
        assert "Komponent A" in names
        assert "Komponent B" in names
        # split_into echoed
        assert len(body["split_into"]) == 2
