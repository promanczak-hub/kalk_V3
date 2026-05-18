"""Phase B — tests for POST /extract/hitl/preview and /extract/hitl/apply.

Coverage:
- preview: returns composite + body_type lookup + capex summary WITHOUT persisting
- apply: re-classifies paid_options per bucket, rebuilds composite, updates
  discount, flips verification_status to 'completed', logs to extraction_corrections
- preserves anon JWT contract (no service_role escalation needed for HITL writes)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


_BASE_SYNTHESIS = {
    "card_summary": {
        "body_style": "Podwozie z pojedynczą kabiną",
        "paid_options": [
            {
                "name": "Zabudowa Kontener Izotermiczny",
                "price": "47970 PLN brutto",
                "price_type": "brutto",
                "category": "Serwisowa",
                "confidence": 0.32,
                "field_id": "fid-zab",
            },
            {
                "name": "Agregat Zanotti Z380",
                "price": "37527.30 PLN brutto",
                "price_type": "brutto",
                "category": "Akcesoria",
                "confidence": 0.55,
                "field_id": "fid-agr",
            },
            {
                "name": "Pakiet Conversion 2",
                "price": "738 PLN brutto",
                "price_type": "brutto",
                "category": "Fabryczna",
                "confidence": 1.0,
                "field_id": "fid-pak",
            },
        ],
        "service_equipment": {
            "name": "",
            "components": [],
        },
        "discount": {
            "explicit_rabat_pln": 49928.16,
            "discountable_base_net": 137600.0,
            "non_discountable_total_net": 85497.30,
            "confidence": 0.6,
        },
        "base_price": "167218.50 PLN brutto",
        "total_price": "204817.14 PLN brutto",
    }
}


def _mock_supabase_with_vehicle(vehicle_id: str = "veh-1", synthesis: dict | None = None):
    """Build a Mock that returns the given synthesis dict from .single().execute()."""
    syn = synthesis if synthesis is not None else _BASE_SYNTHESIS

    mock_execute = MagicMock(return_value=MagicMock(data={
        "id": vehicle_id,
        "synthesis_data": syn,
        "brand": "Renault",
        "model": "Master TO",
    }))
    chain_single = MagicMock(execute=mock_execute)
    chain_eq = MagicMock(single=MagicMock(return_value=chain_single), execute=mock_execute)
    chain_select = MagicMock(eq=MagicMock(return_value=chain_eq))

    # update().eq().execute() chain
    update_eq_execute = MagicMock()
    update_eq = MagicMock(execute=update_eq_execute)
    chain_update = MagicMock(eq=MagicMock(return_value=update_eq))

    # insert() for extraction_corrections
    insert_execute = MagicMock()
    chain_insert = MagicMock(execute=insert_execute)

    mock_table = MagicMock(
        select=MagicMock(return_value=chain_select),
        update=MagicMock(return_value=chain_update),
        insert=MagicMock(return_value=chain_insert),
    )

    mock_supabase = MagicMock(table=MagicMock(return_value=mock_table))
    return mock_supabase, mock_table


@pytest.fixture(autouse=True)
def _mock_external_helpers():
    """Stub heavy externals so endpoints don't hit network / DB."""
    with patch("api.extract_routes._direct_update_synthesis") as mock_direct, \
         patch("api.extract_routes.cache_invalidate_pattern") as mock_cache, \
         patch("api.extract_routes._resolve_body_type_for_composite") as mock_resolve:
        mock_resolve.return_value = {
            "body_type_id": 42,
            "matched_name": "Podwozie Chłodnia",
            "vehicle_class": "Dostawczy",
            "match_method": "exact",
            "score": 100,
            "utrata_wartosci": -4.5,
        }
        yield {
            "direct_update": mock_direct,
            "cache_invalidate": mock_cache,
            "resolve_body_type": mock_resolve,
        }


# ── HITL Preview ──

class TestHITLPreview:
    def test_returns_composite_for_chassis_plus_chlodnia(self, _mock_external_helpers):
        mock_supabase, _ = _mock_supabase_with_vehicle()
        with patch("api.extract_routes.supabase_client", mock_supabase):
            response = client.post(
                "/api/extract/hitl/preview/veh-1",
                json={
                    "cabin_kind": "podwozie",
                    "zabudowa_sot_key": "CHLODNIA",
                    "price_corrections": [],
                },
            )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["composite_body_style"] == "Podwozie Chłodnia"
        assert data["body_type"]["body_type_id"] == 42

    def test_capex_aggregated_per_bucket(self, _mock_external_helpers):
        mock_supabase, _ = _mock_supabase_with_vehicle()
        with patch("api.extract_routes.supabase_client", mock_supabase):
            response = client.post(
                "/api/extract/hitl/preview/veh-1",
                json={
                    "cabin_kind": "podwozie",
                    "zabudowa_sot_key": "CHLODNIA",
                    "price_corrections": [
                        {
                            "field_id": "fid-base",
                            "bucket": "base",
                            "price_value": 167218.50,
                            "price_type": "brutto",
                            "vat_rate": 0.23,
                        },
                        {
                            "field_id": "fid-zab",
                            "bucket": "zabudowa",
                            "price_value": 47970.0,
                            "price_type": "brutto",
                            "vat_rate": 0.23,
                        },
                        {
                            "field_id": "fid-skip",
                            "bucket": "skip",
                            "price_value": 39000.0,
                            "price_type": "netto",
                            "vat_rate": 0.23,
                        },
                    ],
                },
            )
        assert response.status_code == 200
        capex = response.json()["capex"]
        assert capex["base"] == pytest.approx(167218.50)
        assert capex["zabudowa"] == pytest.approx(47970.0)
        # skip bucket nie wchodzi do total
        assert capex["total_capex"] == pytest.approx(167218.50 + 47970.0)

    def test_capex_normalizes_netto_to_brutto(self, _mock_external_helpers):
        mock_supabase, _ = _mock_supabase_with_vehicle()
        with patch("api.extract_routes.supabase_client", mock_supabase):
            response = client.post(
                "/api/extract/hitl/preview/veh-1",
                json={
                    "price_corrections": [
                        {
                            "field_id": "fid-1",
                            "bucket": "zabudowa",
                            "price_value": 39000.0,
                            "price_type": "netto",
                            "vat_rate": 0.23,
                        }
                    ],
                },
            )
        assert response.status_code == 200
        # 39000 netto * 1.23 = 47970 brutto
        assert response.json()["capex"]["zabudowa"] == pytest.approx(47970.0)

    def test_404_when_vehicle_not_found(self, _mock_external_helpers):
        mock_supabase = MagicMock()
        mock_single = MagicMock(execute=MagicMock(return_value=MagicMock(data=None)))
        chain_eq = MagicMock(single=MagicMock(return_value=mock_single))
        mock_supabase.table.return_value.select.return_value.eq.return_value = chain_eq

        with patch("api.extract_routes.supabase_client", mock_supabase):
            response = client.post(
                "/api/extract/hitl/preview/missing-id",
                json={"cabin_kind": "podwozie", "zabudowa_sot_key": "CHLODNIA"},
            )
        assert response.status_code == 404

    def test_preview_does_not_persist(self, _mock_external_helpers):
        """Preview MUSI być read-only — żadnych update/insert."""
        mock_supabase, mock_table = _mock_supabase_with_vehicle()
        with patch("api.extract_routes.supabase_client", mock_supabase):
            client.post(
                "/api/extract/hitl/preview/veh-1",
                json={"cabin_kind": "podwozie", "zabudowa_sot_key": "CHLODNIA"},
            )
        # SELECT tak, ale UPDATE/INSERT nie
        mock_table.update.assert_not_called()
        mock_table.insert.assert_not_called()
        _mock_external_helpers["direct_update"].assert_not_called()


# ── HITL Apply ──

class TestHITLApply:
    def test_full_apply_flow_izoterma_case(self, _mock_external_helpers):
        """End-to-end: użytkownik przesuwa zabudowę do bucketu zabudowa, ustawia
        chłodnia z palety, dodaje rabat kwotowy → status='completed', composite
        zaktualizowany, extraction_corrections wpisane."""
        mock_supabase, mock_table = _mock_supabase_with_vehicle()
        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("api.extract_routes._get_admin_client", return_value=mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s):
            response = client.post(
                "/api/extract/hitl/apply/veh-1",
                json={
                    "cabin_kind": "podwozie",
                    "zabudowa_sot_key": "CHLODNIA",
                    "price_corrections": [
                        {
                            "field_id": "fid-zab",
                            "bucket": "zabudowa",
                            "price_value": 47970.0,
                            "price_type": "brutto",
                            "vat_rate": 0.23,
                        },
                        {
                            "field_id": "fid-agr",
                            "bucket": "agregat",
                            "price_value": 37527.30,
                            "price_type": "brutto",
                            "vat_rate": 0.23,
                        },
                        {
                            "field_id": "fid-pak",
                            "bucket": "factory",
                            "price_value": 738.0,
                            "price_type": "brutto",
                            "vat_rate": 0.23,
                        },
                    ],
                    "discount": {
                        "rabat_type": "kwotowo",
                        "rabat_basis": "brutto",
                        "rabat_value": 49928.16,
                        "discount_scope": ["base", "factory_options"],
                    },
                    "user_notes": "Test HITL apply izoterma",
                },
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ok"
        assert data["verification_status"] == "completed"
        assert data["composite_body_style"] == "Podwozie Chłodnia"

        # Status flipped na completed
        mock_table.update.assert_called_with({"verification_status": "completed"})
        # synthesis_data persisted
        _mock_external_helpers["direct_update"].assert_called_once()
        # extraction_corrections logged
        mock_table.insert.assert_called_once()

    def test_skip_bucket_drops_paid_option(self, _mock_external_helpers):
        """Pozycja zassignowana do bucket 'skip' nie powinna zostać w paid_options."""
        mock_supabase, mock_table = _mock_supabase_with_vehicle()
        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s):
            client.post(
                "/api/extract/hitl/apply/veh-1",
                json={
                    "price_corrections": [
                        {
                            "field_id": "fid-zab",
                            "bucket": "skip",
                            "price_value": 0.0,
                            "price_type": "brutto",
                        },
                        {
                            "field_id": "fid-pak",
                            "bucket": "factory",
                            "price_value": 738.0,
                            "price_type": "brutto",
                        },
                    ],
                },
            )

        # Inspect what was persisted
        call = _mock_external_helpers["direct_update"].call_args
        _, persisted_synthesis = call.args
        persisted_paid = persisted_synthesis["card_summary"]["paid_options"]
        names = [p["name"] for p in persisted_paid]
        assert "Zabudowa Kontener Izotermiczny" not in names  # skipped
        assert "Pakiet Conversion 2" in names

    def test_discount_corrections_persisted(self, _mock_external_helpers):
        mock_supabase, _ = _mock_supabase_with_vehicle()
        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s):
            client.post(
                "/api/extract/hitl/apply/veh-1",
                json={
                    "discount": {
                        "rabat_type": "procentowo",
                        "rabat_basis": "netto",
                        "rabat_value": 29.5,
                        "discount_scope": ["base", "factory_options"],
                    }
                },
            )
        call = _mock_external_helpers["direct_update"].call_args
        _, persisted = call.args
        d = persisted["card_summary"]["discount"]
        assert d["rabat_type"] == "procentowo"
        assert d["rabat_basis"] == "netto"
        assert d["discount_scope"] == ["base", "factory_options"]
        assert d["explicit_rabat_pct"] == 29.5
        assert d["confidence"] == 1.0
        assert d["extraction_method"] == "explicit_percentage"
        assert any("HITL" in n for n in d["audit_notes"])

    def test_404_when_vehicle_missing_on_apply(self, _mock_external_helpers):
        mock_supabase = MagicMock()
        mock_single = MagicMock(execute=MagicMock(return_value=MagicMock(data=None)))
        chain_eq = MagicMock(single=MagicMock(return_value=mock_single))
        mock_supabase.table.return_value.select.return_value.eq.return_value = chain_eq

        with patch("api.extract_routes.supabase_client", mock_supabase):
            response = client.post(
                "/api/extract/hitl/apply/missing",
                json={"cabin_kind": "podwozie", "zabudowa_sot_key": "CHLODNIA"},
            )
        assert response.status_code == 404

    def test_extraction_corrections_insert_failure_does_not_crash(
        self, _mock_external_helpers
    ):
        """Best-effort: log do extraction_corrections nigdy nie blokuje save."""
        mock_supabase, mock_table = _mock_supabase_with_vehicle()
        # Sabotage insert
        mock_table.insert.return_value.execute.side_effect = RuntimeError("db down")
        with patch("api.extract_routes.supabase_client", mock_supabase), \
             patch("api.extract_routes._get_admin_client", return_value=mock_supabase), \
             patch("core.pipeline_price_validator.validate_and_flag_prices", side_effect=lambda s: s):
            response = client.post(
                "/api/extract/hitl/apply/veh-1",
                json={"cabin_kind": "podwozie", "zabudowa_sot_key": "CHLODNIA"},
            )
        # Endpoint zwraca 200 mimo crash logu
        assert response.status_code == 200
        assert response.json()["verification_status"] == "completed"
