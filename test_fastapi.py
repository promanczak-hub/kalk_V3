from fastapi.testclient import TestClient
from backend.main import app
import json

client = TestClient(app)

data = {
    'category': 'cheaper', 
    'duration_months': 36, 
    'annual_mileage': 15000, 
    'limit': 2, 
    'requirements': [
        {'feature_key':'towbar', 'operator':'eq', 'value':True, 'requirement':'MUST_HAVE'}
    ]
}

response = client.post(
    "/api/scoring-search/vehicle/a4e0c4aa-4aa3-4f2b-8a82-127e7af7f7d1/alternatives", 
    json=data
)

print(response.status_code)
print(response.text)
