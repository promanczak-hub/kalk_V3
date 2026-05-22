"""Tests for POST /extract/blank — manual-blank CardSummary creation.

Round-trip coverage (per CLAUDE.md §"two-way (round-trip) test"):
- create_blank: INSERT writes correct skeleton + _origin marker
- hitl_apply on manual_blank without `fuel`: 400 with structured error
- hitl_apply on manual_blank WITH fuel: triggers finalize_vehicle_pipeline,
  populates mapped_ai_data, pops _origin (one-shot guard)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _make_insert_chain():
    """Mock for `supabase.table('vehicle_synthesis').insert({...}).execute()`."""
    insert_execute = MagicMock()
    chain_insert = MagicMock(execute=insert_execute)
    return chain_insert, insert_execute


def _make_blank_synthesis_with_fuel(fuel: str | None) -> dict:
    """Replicate the skeleton produced by _build_skeleton, optionally with fuel set
    to simulate state after user has filled some HITL fields."""
    return {
        "_origin": "manual_blank",
        "mapped_ai_data": {},
        "card_summary": {
            "powertrain": "" if fuel is None else "2.0 TDI 150 KM",
            "vehicle_class": "Osobowy",
            "body_style": "" if fuel is None else "Sedan",
            "trim_level": "",
            "base_price": "Brak" if fuel is None else "150000 PLN netto",
            "options_price": "Brak",
            "total_price": "Brak",
            "fuel": fuel or "Brak",
            "transmission": "Brak" if fuel is None else "Automatyczna",
            "wheels": "Brak",
            "exterior_color": "Brak",
            "standard_equipment": [],
            "paid_options": [],
            "service_equipment": None,
            "available_powertrains": [],
            "financial_reasoning": "Manual draft — created via UI without source PDF",
            "price_domain": "netto",
            "_requires_user_input": ["base_price", "powertrain", "body_style", "fuel"],
        },
    }


def _mock_supabase_for_apply(synthesis: dict, vehicle_id: str = "blank-1"):
    """Mock supabase chain that returns the given synthesis for the SELECT
    in hitl_apply, and accepts subsequent UPDATEs / INSERTs."""
    select_execute = MagicMock(return_value=MagicMock(data={
        "id": vehicle_id,
        "synthesis_data": synthesis,
        "brand": "BMW",
        "model": "X3",
    }))
    chain_single = MagicMock(execute=select_execute)
    chain_eq_select = MagicMock(single=MagicMock(return_value=chain_single), execute=select_execute)
    chain_select = MagicMock(eq=MagicMock(return_value=chain_eq_select))

    update_execute = MagicMock()
    chain_eq_update = MagicMock(execute=update_execute)
    chain_update = MagicMock(eq=MagicMock(return_value=chain_eq_update))

    insert_execute = MagicMock()
    chain_insert = MagicMock(execute=insert_execute)

    mock_table = MagicMock(
        select=MagicMock(return_value=chain_select),
        update=MagicMock(return_value=chain_update),
        insert=MagicMock(return_value=chain_insert),
    )
    mock_supabase = MagicMock(table=MagicMock(return_value=mock_table))
    return mock_supabase, mock_table


# ── 1. POST /extract/blank ────────────────────────────────────────────────


class TestCreateBlank:
    def test_create_blank_inserts_skeleton_with_origin_marker(self):
        chain_insert, insert_execute = _make_insert_chain()
        mock_table = MagicMock(insert=MagicMock(return_value=chain_insert))
        mock_supabase = MagicMock(table=MagicMock(return_value=mock_table))

        with patch("api.extract_blank_routes.supabase_client", mock_supabase), \
             patch("api.extract_blank_routes.cache_invalidate_pattern"):
            response = client.post("/api/extract/blank", json={"brand": "BMW", "model": "X3"})

        assert response.status_code == 200, response.text
        body = response.json()
        assert "vehicle_id" in body
        assert body["verification_status"] == "needs_review"

        # Round-trip: what did we send to supabase?
        mock_table.insert.assert_called_once()
        payload = mock_table.insert.call_args[0][0]
        assert payload["verification_status"] == "needs_review"
        assert payload["brand"] == "BMW"
        assert payload["model"] == "X3"
        skel = payload["synthesis_data"]
        assert skel["_origin"] == "manual_blank"
        assert skel["card_summary"]["paid_options"] == []
        assert skel["card_summary"]["service_equipment"] is None
        assert skel["card_summary"]["fuel"] == "Brak"
        assert "fuel" in skel["card_summary"]["_requires_user_input"]

    def test_create_blank_accepts_empty_body(self):
        """Defaults work — no brand/model required."""
        chain_insert, _ = _make_insert_chain()
        mock_table = MagicMock(insert=MagicMock(return_value=chain_insert))
        mock_supabase = MagicMock(table=MagicMock(return_value=mock_table))

        with patch("api.extract_blank_routes.supabase_client", mock_supabase), \
             patch("api.extract_blank_routes.cache_invalidate_pattern"):
            response = client.post("/api/extract/blank", json={})

        assert response.status_code == 200
        payload = mock_table.insert.call_args[0][0]
        assert payload["brand"] is None
        assert payload["model"] is None
        assert payload["synthesis_data"]["card_summary"]["vehicle_class"] == "Osobowy"

    def test_create_blank_returns_500_on_db_error(self):
        chain_insert = MagicMock(execute=MagicMock(side_effect=RuntimeError("db down")))
        mock_table = MagicMock(insert=MagicMock(return_value=chain_insert))
        mock_supabase = MagicMock(table=MagicMock(return_value=mock_table))

        with patch("api.extract_blank_routes.supabase_client", mock_supabase), \
             patch("api.extract_blank_routes.cache_invalidate_pattern"):
            response = client.post("/api/extract/blank", json={})

        assert response.status_code == 500
        assert "Failed to create blank vehicle" in response.json()["detail"]


# ── 2. /extract/hitl/apply guard for manual_blank ────────────────────────


class TestHITLApplyManualBlankGuard:
    @pytest.fixture(autouse=True)
    def _mock_externals(self):
        with patch("api.extract_routes._direct_update_synthesis"), \
             patch("api.extract_routes.cache_invalidate_pattern"), \
             patch("api.extract_routes._resolve_body_type_for_composite") as mock_resolve:
            mock_resolve.return_value = None
            yield

    def test_apply_without_fuel_returns_400_with_requires_user_input(self):
        """manual_blank + fuel='Brak' → 400 with structured error so UI can highlight."""
        synthesis = _make_blank_synthesis_with_fuel(fuel=None)  # fuel='Brak'
        mock_supabase, _ = _mock_supabase_for_apply(synthesis)

        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("api.extract_routes._get_admin_client", return_value=mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s):
            response = client.post(
                "/api/extract/hitl/apply/blank-1",
                json={
                    "cabin_kind": None,
                    "zabudowa_sot_key": None,
                    "price_corrections": [],
                    "discount": None,
                },
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "missing_required_for_sot_mapping"
        assert "fuel" in detail["requires_user_input"]

    def test_apply_with_fuel_triggers_sot_and_clears_origin(self):
        """manual_blank + fuel='Diesel (ON)' → finalize_vehicle_pipeline called, _origin popped."""
        synthesis = _make_blank_synthesis_with_fuel(fuel="Diesel (ON)")
        mock_supabase, _ = _mock_supabase_for_apply(synthesis)

        def _fake_finalize(supabase, vehicle_id, parsed_data, **kwargs):
            # Simulate what real finalize_vehicle_pipeline does to mapped_ai_data
            parsed_data.setdefault("mapped_ai_data", {})["engine_class"] = "Diesel"
            parsed_data["mapped_ai_data"]["samar_category"] = "D ŚREDNIA"

        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("api.extract_routes._get_admin_client", return_value=mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s), \
             patch("core.extraction_pipeline.phase_2_mapping.finalize_vehicle_pipeline",
                   side_effect=_fake_finalize) as mock_finalize:
            response = client.post(
                "/api/extract/hitl/apply/blank-1",
                json={
                    "cabin_kind": None,
                    "zabudowa_sot_key": None,
                    "price_corrections": [],
                    "discount": None,
                },
            )

        assert response.status_code == 200, response.text
        mock_finalize.assert_called_once()
        # The synthesis dict mutated in place — verify _origin was popped after SOT ran
        call_synthesis = mock_finalize.call_args[0][2]
        assert "_origin" not in call_synthesis
        assert call_synthesis["mapped_ai_data"]["engine_class"] == "Diesel"

    def test_apply_on_non_blank_does_not_call_finalize(self):
        """Regression: PDF-origin synthesis (no _origin marker) must NOT trigger SOT re-mapping."""
        synthesis = _make_blank_synthesis_with_fuel(fuel="Diesel (ON)")
        del synthesis["_origin"]  # simulate PDF-extracted row
        mock_supabase, _ = _mock_supabase_for_apply(synthesis)

        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("api.extract_routes._get_admin_client", return_value=mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s), \
             patch("core.extraction_pipeline.phase_2_mapping.finalize_vehicle_pipeline") as mock_finalize:
            response = client.post(
                "/api/extract/hitl/apply/blank-1",
                json={
                    "cabin_kind": None,
                    "zabudowa_sot_key": None,
                    "price_corrections": [],
                    "discount": None,
                },
            )

        assert response.status_code == 200
        mock_finalize.assert_not_called()

    def test_manual_blank_dispatches_matrix_refresh_after_sot(self):
        """After SOT mapping completes, the auto-kalkulacja must be rebuilt with the
        fresh mapped_ai_data (engine_name, samar_category). Otherwise the existing
        AUTO ltr_kalkulacje stays stale with empty fields and matrix calc fails
        validation. Bridge fix per task #13."""
        synthesis = _make_blank_synthesis_with_fuel(fuel="Benzyna (PB)")
        mock_supabase, _ = _mock_supabase_for_apply(synthesis)

        def _fake_finalize(supabase, vehicle_id, parsed_data, **kwargs):
            parsed_data.setdefault("mapped_ai_data", {})["engine_class"] = "spalinowy"
            parsed_data["mapped_ai_data"]["samar_category"] = "Podstawowa - C NIŻSZA ŚREDNIA"
            parsed_data["mapped_ai_data"]["fuel"] = "Benzyna (PB)"

        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("api.extract_routes._get_admin_client", return_value=mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s), \
             patch("core.extraction_pipeline.phase_2_mapping.finalize_vehicle_pipeline",
                   side_effect=_fake_finalize), \
             patch("tasks.matrix_tasks.refresh_matrix_cache_for_vehicles_task") as mock_refresh:
            response = client.post(
                "/api/extract/hitl/apply/blank-1",
                json={
                    "cabin_kind": None,
                    "zabudowa_sot_key": None,
                    "price_corrections": [],
                    "discount": None,
                },
            )

        assert response.status_code == 200, response.text
        mock_refresh.apply_async.assert_called_once_with(args=[["blank-1"]])

    def test_pdf_origin_does_not_dispatch_matrix_refresh(self):
        """Regression: only manual_blank triggers the extra refresh — PDF-origin
        vehicles already had refresh dispatched in their own extract pipeline."""
        synthesis = _make_blank_synthesis_with_fuel(fuel="Diesel (ON)")
        del synthesis["_origin"]
        mock_supabase, _ = _mock_supabase_for_apply(synthesis)

        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("api.extract_routes._get_admin_client", return_value=mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s), \
             patch("tasks.matrix_tasks.refresh_matrix_cache_for_vehicles_task") as mock_refresh:
            response = client.post(
                "/api/extract/hitl/apply/blank-1",
                json={
                    "cabin_kind": None,
                    "zabudowa_sot_key": None,
                    "price_corrections": [],
                    "discount": None,
                },
            )

        assert response.status_code == 200
        mock_refresh.apply_async.assert_not_called()


# ── 3. fill_base_price keeps price_domain in sync ────────────────────────


class TestFillBasePriceDomainSync:
    """Task #14: fill-base-price must update card_summary.price_domain alongside
    the price string, otherwise UI / matrix calc misread the netto/brutto split."""

    @pytest.fixture(autouse=True)
    def _mock_externals(self):
        with patch("api.extract_routes._direct_update_synthesis"), \
             patch("api.extract_routes.cache_invalidate_pattern"), \
             patch("core.pipeline_price_validator.validate_and_flag_prices",
                   side_effect=lambda s: s):
            yield

    def _mk_supabase_for_blank(self):
        synthesis = {
            "_origin": "manual_blank",
            "mapped_ai_data": {},
            "card_summary": {
                "price_domain": "netto",  # skeleton default — must get overwritten
                "base_price": "Brak",
                "_requires_user_input": ["base_price"],
            },
        }
        return _mock_supabase_for_apply(synthesis, vehicle_id="fb-1")

    def test_brutto_input_sets_price_domain_brutto(self):
        mock_supabase, mock_table = self._mk_supabase_for_blank()
        with patch("api.extract_routes.supabase_client", mock_supabase):
            response = client.post(
                "/api/extract/fill-base-price/fb-1",
                json={"base_price": 185600, "domain": "brutto"},
            )
        assert response.status_code == 200, response.text
        # Inspect the synthesis sent to _direct_update_synthesis
        from api.extract_routes import _direct_update_synthesis
        synthesis_arg = _direct_update_synthesis.call_args[0][1]
        cs = synthesis_arg["card_summary"]
        assert cs["base_price"] == "185600 PLN brutto"
        assert cs["price_domain"] == "brutto"  # ← the fix

    def test_netto_input_sets_price_domain_netto(self):
        mock_supabase, _ = self._mk_supabase_for_blank()
        with patch("api.extract_routes.supabase_client", mock_supabase):
            response = client.post(
                "/api/extract/fill-base-price/fb-1",
                json={"base_price": 150894, "domain": "netto"},
            )
        assert response.status_code == 200, response.text
        from api.extract_routes import _direct_update_synthesis
        cs = _direct_update_synthesis.call_args[0][1]["card_summary"]
        assert cs["base_price"] == "150894 PLN netto"
        assert cs["price_domain"] == "netto"
