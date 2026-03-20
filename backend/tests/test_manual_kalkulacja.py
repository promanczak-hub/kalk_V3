"""
Tests for manual kalkulacja endpointy:
- POST /kalkulacje/manual
- POST /kalkulacje/{id}/duplicate (source=clone)
- PATCH /kalkulacje/{id}/pricing (deterministyczne ceny)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def _mock_insert(data: dict):
    """Helper: returns supabase insert mock that yields the input as inserted row."""
    now_str = "2026-01-01T00:00:00+00:00"
    mock_res = MagicMock()
    mock_res.data = [
        {**data, "id": "test-uuid-001", "created_at": now_str, "updated_at": now_str}
    ]
    return mock_res


class TestCreateManualKalkulacja:
    """POST /kalkulacje/manual"""

    def test_creates_with_required_fields(self, client):
        now_str = "2026-01-01T00:00:00+00:00"
        fake_row = {
            "id": "test-uuid-001",
            "numer_kalkulacji": "KALK/2026/01/ABCDEF",
            "status": "szkic_vertex",
            "source": "manual",
            "dane_pojazdu": "BMW 3 Series",
            "cena_netto": 0.0,
            "stan_json": {"source": "manual", "brand": "BMW", "model": "3 Series"},
            "created_at": now_str,
            "updated_at": now_str,
        }
        mock_execute = MagicMock()
        mock_execute.data = [fake_row]

        with patch("api.kalkulacje_routes.supabase") as mock_sb:
            mock_tb = MagicMock()
            mock_sb.table.return_value = mock_tb
            mock_tb.insert.return_value.execute.return_value = mock_execute

            res = client.post(
                "/api/kalkulacje/manual",
                json={"brand": "BMW", "model": "3 Series"},
            )

        assert res.status_code == 200
        body = res.json()
        assert body["source"] == "manual"
        assert "BMW" in body["dane_pojazdu"]

    def test_requires_brand(self, client):
        """Brak pola brand -> walidacja Pydantic 422."""
        res = client.post("/api/kalkulacje/manual", json={"model": "3 Series"})
        assert res.status_code == 422

    def test_requires_model(self, client):
        """Brak pola model -> walidacja Pydantic 422."""
        res = client.post("/api/kalkulacje/manual", json={"brand": "BMW"})
        assert res.status_code == 422


class TestPricingDeterministic:
    """Weryfikacja logiki deterministycznej w _compute_pricing_result."""

    def test_basic_pricing_math(self):
        from api.kalkulacje_routes import _compute_pricing_result
        from api.schemas.pricing import PricingPatch, PricingComponent

        patch_data = PricingPatch(
            components=[
                PricingComponent(
                    label="Cena katalogowa netto",
                    amount_net=100_000.0,
                    no_discount=False,
                ),
                PricingComponent(
                    label="Transport netto", amount_net=1_500.0, no_discount=True
                ),
            ],
            discount_pct=5.0,
        )
        result = _compute_pricing_result(patch_data)

        # Discountable: 100_000, Non-disc: 1_500
        # discount_amount = 100_000 * 5% = 5_000
        # purchase_price_net = 100_000 - 5_000 + 1_500 = 96_500
        # vat = 96_500 * 0.23 = 22_195
        # gross = 96_500 + 22_195 = 118_695
        assert result.discountable_sum == 100_000.0
        assert result.non_discountable_sum == 1_500.0
        assert result.total_sum_net == 101_500.0
        assert result.discount_amount == 5_000.0
        assert result.purchase_price_net == 96_500.0
        assert result.vat_amount == 22_195.0
        assert result.purchase_price_gross == 118_695.0

    def test_zero_discount(self):
        from api.kalkulacje_routes import _compute_pricing_result
        from api.schemas.pricing import PricingPatch, PricingComponent

        patch_data = PricingPatch(
            components=[
                PricingComponent(label="Cena", amount_net=50_000.0, no_discount=False)
            ],
            discount_pct=0.0,
        )
        result = _compute_pricing_result(patch_data)
        assert result.purchase_price_net == 50_000.0
        assert result.discount_amount == 0.0

    def test_full_no_discount(self):
        """Jeśli wszystkie składowe mają no_discount=True, rabat nie wpływa na cenę netto."""
        from api.kalkulacje_routes import _compute_pricing_result
        from api.schemas.pricing import PricingPatch, PricingComponent

        patch_data = PricingPatch(
            components=[
                PricingComponent(
                    label="Transport", amount_net=10_000.0, no_discount=True
                )
            ],
            discount_pct=10.0,
        )
        result = _compute_pricing_result(patch_data)
        assert result.purchase_price_net == 10_000.0
        assert result.discount_amount == 0.0
