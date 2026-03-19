import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from core.database import supabase
from core.feature_enrichment import _load_feature_catalog, _llm_match_utility_features

def test_llm():
    features = _load_feature_catalog()
    
    utility_items = [
        {"name": "Długość", "value": "4 912 mm"},
        {"name": "Maksymalna prędkość", "value": "225 km/h"},
        {"name": "Masa własna min.", "value": "1 640 kg"},
        {"name": "Dopuszczalna masa całkowita", "value": "2 170 kg"},
    ]
    
    print("Running LLM Match...")
    matches = _llm_match_utility_features(utility_items, features)
    
    print(json.dumps(matches, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_llm()
