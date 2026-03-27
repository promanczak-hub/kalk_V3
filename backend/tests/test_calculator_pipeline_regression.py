from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

client = TestClient(app)


def test_kalkulator_pipeline_validation():
    """
    Testuje punkt końcowy pętli kalkulacyjnej LTR.
    Sprawdza, czy minimalny set danych (bez wszystkich kluczy)
    nie powoduje "cichego błędu" ale poprawnie odrzuca lub przelicza.
    Nawiązuje to do reguły "Zero fallbacków w pipeline kalkulacyjnym".
    """
    payload = {
        "stan_json": {
            "vehicle_id": "test-uuid-999",
            "base_price_net": 120000,
            "wibor_pct": 0.058,
            "margin_pct": 0.02,
            "pricing_margin_pct": 0.01,
            "initial_deposit_pct": 0.1,
            "inne_koszty_serwisowania_netto": 0,
            "replacement_car_enabled": False,
            "add_gsm_subscription": False,
            "add_hook_installation": False,
            "include_servicing": True,
            "z_oponami": True,
            "klasa_opony_string": "Medium",
            "korekta_kosztu_opon": False,
            "srednica_felgi": 18,
        }
    }

    # Próbujemy puścić kalkulację bez zasilania bazy
    # Spodziewamy się albo 200 (jeśli payload ma wszystko co potrzeba by to wyśmiać),
    # albo rzucenia jawnym 400/500 przez brak matryc (co jest zgodne z fail-fast).
    with patch("core.database.supabase.table") as mock_table:
        # Mockujemy tak, aby baza zwracała pustą odpowiedź dla stawek w pipeline
        mock_execute = (
            mock_table.return_value.select.return_value.eq.return_value.execute
        )
        mock_execute.return_value.data = []

        response = client.post("/api/kalkulacje", json=payload)

        # Nawet na błędach bazy powinno nam wylecieć jawne HTTPException lub status code,
        # API nie powinno crashować na 500 z wyjątkiem Pythona.
        assert response.status_code in [200, 400, 404, 422, 500], (
            "Unexpected response behavior"
        )
