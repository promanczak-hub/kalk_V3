import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.feature_enrichment import _load_feature_catalog, _llm_match_utility_features
import json


def test():
    features = _load_feature_catalog()
    valid_utility = [
        {"name": "DMC zespołu pojazdów", "value": "6 000 kg"},
        {"name": "Dopuszczalna masa - oś przednia", "value": "1 800 kg"},
        {"name": "Dopuszczalna masa całkowita (DMC)", "value": "3 500 kg"},
        {"name": "Masa własna bez kierowcy", "value": "2234 kg"},
        {"name": "Dopuszczalna ładowność", "value": "1266 kg"},
        {"name": "Rozstaw osi", "value": "3 640 mm"},
        {"name": "Szerokość bez lusterek", "value": "2 040 mm"},
    ]

    matches = _llm_match_utility_features(valid_utility, features)
    with open("matches_output.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)


test()
