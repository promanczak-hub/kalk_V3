import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from core.database import supabase

from pydantic import BaseModel
from typing import List, Optional

class BodyTypeSchema(BaseModel):
    id: Optional[int] = None
    nazwa_nadwozia: str
    typ_pojazdu: str
    created_at: Optional[str] = None

try:
    print("Testing body_types fetch and Pydantic validation (NEW SCHEMA)...")
    res = supabase.table("body_types").select("*").order("nazwa_nadwozia").execute()
    data = res.data or []
    validated_data = [BodyTypeSchema(**item) for item in data]
    print(f"Success! Validated {len(validated_data)} items.")
    if len(validated_data) > 0:
        print(f"Sample item: {validated_data[0].model_dump()}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

