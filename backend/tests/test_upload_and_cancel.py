from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)


def test_cancel_processing_endpoint():
    """
    Testuje punkt końcowy anulowania przetwarzania upewniając się, że
    odpowiednio zmienia on status rekordu w bazie danych na 'cancelled'.
    """
    with patch("api.extract_routes.supabase_client") as mock_supabase:
        mock_execute = MagicMock()
        mock_eq = MagicMock()
        mock_eq.execute = mock_execute
        mock_update = MagicMock()
        mock_update.eq = MagicMock(return_value=mock_eq)
        mock_table_instance = MagicMock()
        mock_table_instance.update = MagicMock(return_value=mock_update)
        mock_supabase.table.return_value = mock_table_instance

        response = client.post(
            "/api/cancel-processing", json={"vehicle_id": "test-uuid-123"}
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "cancelled"

        # Check DB Chain correctness
        mock_supabase.table.assert_called_with("vehicle_synthesis")
        mock_table_instance.update.assert_called_with(
            {"verification_status": "cancelled"}
        )
        mock_update.eq.assert_called_with("id", "test-uuid-123")
        mock_eq.execute.assert_called_once()
