import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("../frontend/.env.local")

supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"), os.getenv("VITE_SUPABASE_ANON_KEY")
)


def check_db():
    print("--- LTRADMINUBEZPIECZENIE_czak ---")
    try:
        res = supabase.table("LTRAdminUbezpieczenie_czak").select("*").execute()
        for r in res.data:
            print(r)
    except Exception as e:
        print("Error:", e)

    print("\n--- LTRAdminParametry_czak ---")
    try:
        res = supabase.table("LTRAdminParametry_czak").select("*").execute()
        if res.data:
            param = res.data[0]
            print(f"NNWKeys: {[k for k in param.keys() if 'NNW' in k.upper()]}")
            print(f"ASSKeys: {[k for k in param.keys() if 'ASS' in k.upper()]}")
            print(
                f"ZielonaKartaKeys: {[k for k in param.keys() if 'ZIELONA' in k.upper()]}"
            )
    except Exception as e:
        print("Error:", e)

    print("\n--- control_center ---")
    try:
        res = supabase.table("control_center").select("*").execute()
        if res.data:
            param = res.data[0]
            for k, v in param.items():
                if (
                    "ins" in k.lower()
                    or "nnw" in k.lower()
                    or "ass" in k.lower()
                    or "ziel" in k.lower()
                ):
                    print(f"{k}: {v}")
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    check_db()
