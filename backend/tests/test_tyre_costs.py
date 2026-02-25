import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_tyre_costs():
    response = client.get("/api/tyre-costs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_and_delete_tyre_cost():
    # Create
    response = client.post(
        "/api/tyre-costs",
        json={
            "tyre_class": "TestClass_Opony_123",
            "diameter": 17,
            "purchase_price": 999.0,
            "buyback_price": 200.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tyre_class"] == "TestClass_Opony_123"
    cost_id = data["id"]

    # Delete to clean up database
    del_response = client.delete(f"/api/tyre-costs/{cost_id}")
    assert del_response.status_code == 200
    assert del_response.json() == {"status": "success"}
