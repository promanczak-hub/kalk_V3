import os
import sys

# add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))


try:
    print("Checking constraints...")
    # Just execute a raw sql via supabase if possible, or we can check the migrations
    pass
except Exception:
    import traceback

    traceback.print_exc()
