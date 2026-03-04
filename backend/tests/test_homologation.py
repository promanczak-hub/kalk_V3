import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_verify_homologation_with_effects():
    payload = {
        "vehicle_id": "test-id",
        "base_samar_category": "Osobowy",
        "base_vehicle_type": "M1",
        "base_payload_kg": 1000.0,
        "service_options": [
            {
                "name": "Zabudowa kontenerowa",
                "category": "Opcja Serwisowa",
                "price_net": 15000.0,
                "effects": {
                    "override_samar_class": "Kontener",
                    "override_homologation": "N1",
                    "adds_weight_kg": 350.0,
                    "is_financial_only": False,
                },
            }
        ],
    }
    response = client.post("/api/homologation/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["new_samar_category"] == "Kontener"
    assert data["new_vehicle_type"] == "N1"
    assert data["payload_loss_kg"] == 350.0
    assert data["dynamic_payload_kg"] == 650.0
    assert data["samar_override_applied"] is True
    assert len(data["homologation_alerts"]) > 0


def test_verify_homologation_textual_fallback():
    payload = {
        "vehicle_id": "test-id-2",
        "base_samar_category": "Osobowy",
        "base_vehicle_type": "M1",
        "base_payload_kg": 800.0,
        "service_options": [
            {
                "name": "Izoterma z agregatem",
                "category": "Opcja Serwisowa",
                "price_net": 20000.0,
                # No effects provided
            }
        ],
    }
    response = client.post("/api/homologation/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["new_samar_category"] == "Izoterma"
    assert data["samar_override_applied"] is True


def test_verify_homologation_financial_only():
    payload = {
        "vehicle_id": "test-id-3",
        "base_samar_category": "SUV",
        "base_vehicle_type": "M1",
        "base_payload_kg": 600.0,
        "service_options": [
            {
                "name": "Dywaniki gumowe",
                "category": "Akcesoria",
                "price_net": 200.0,
                "effects": {"is_financial_only": True},
            }
        ],
    }
    response = client.post("/api/homologation/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["new_samar_category"] == "SUV"
    assert data["samar_override_applied"] is False
    assert data["payload_loss_kg"] == 0.0
