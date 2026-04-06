import asyncio
import os
import sys

# add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.database import supabase

try:
    print("Checking constraints...")
    # Just execute a raw sql via supabase if possible, or we can check the migrations
    pass
except Exception as e:
    import traceback
    traceback.print_exc()
