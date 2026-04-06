import os
import sys
import json
sys.path.append(r"d:\kalk_v3\backend")
from core.database import supabase

# paint types
pt = supabase.table("paint_types").select("*").execute()
print("Paint types:", json.dumps(pt.data, indent=2))

# body type corrections
bc = supabase.table("body_type_wr_corrections").select("*").execute()
print("Body type corr:", json.dumps(bc.data, indent=2))

