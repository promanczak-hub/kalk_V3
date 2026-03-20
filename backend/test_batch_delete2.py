import os
import sys

# add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.database import supabase

try:
    print("Executing delete...")
    response = (
        supabase.table("vehicle_synthesis")
        .delete()
        .in_("id", ["test1", "test2"])
        .execute()
    )
    print("Success:", response)
except Exception:
    import traceback

    traceback.print_exc()
