import requests
import json

def test_api():
    url = "http://127.0.0.1:8000/api/offers/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "client_name": "Test Client",
        "client_nip": "1234567890",
        "items": [
            {
                "brand": "VW",
                "model": "Golf",
                "powertrain": "1.5 TSI",
                "term": 48,
                "mileage": 15000,
                "net_installment": 1200.0,
                "system_recommendation": "Polecany"
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
