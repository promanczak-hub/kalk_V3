import json
from dotenv import load_dotenv

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase


def main():
    resp = supabase.table("tab_okres_final").select("*").limit(1).execute()
    print("Row sample:")
    print(json.dumps(resp.data, indent=2))

    # Try to see referenced table for the fkey
    # This requires querying pg_constraint, which isn't accessible via standard REST easily
    # But let's check legacy classes 26


if __name__ == "__main__":
    main()
