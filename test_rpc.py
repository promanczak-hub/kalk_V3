import asyncio
from backend.core.supabase_client import get_supabase
from dotenv import load_dotenv

load_dotenv("backend/.env")

sb = get_supabase()

def test_rpc():
    print("Testing RPC")
    res = sb.rpc(
        "rpc_get_alternatives_semantic",
        {
            "p_vehicle_id": "a4e0c4aa-4aa3-4f2b-8a82-127e7af7f7d1",
            "p_synthetic_vector": [0.1] * 384,
            "p_limit": 5,
            "p_duration_months": 36,
            "p_annual_mileage": 15000,
            "p_requirements": [{"feature_key":"towbar", "operator":"eq", "value":True, "requirement":"MUST_HAVE"}],
        },
    ).execute()
    print("Response:", res.data)

test_rpc()
