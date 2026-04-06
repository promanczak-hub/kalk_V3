import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent))
from core.database import supabase

try:
    res = supabase.table("body_types").select("*").execute()
    data = res.data
    with open("temp_body_types.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Saved to temp_body_types.json")
except Exception as e:
    print(e)
