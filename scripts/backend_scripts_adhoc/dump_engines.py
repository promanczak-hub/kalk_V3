import os
import sys

sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv

load_dotenv()
from core.database import supabase

res = supabase.table("engines").select("*").execute()
for r in res.data:
    print(r)
