from supabase import create_client
import os

# Simplified for quick verification
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)


def verify():
    print("--- Verifying Samar Classes ---")
    res = supabase.table("samar_classes").select("count").execute()
    print(f"DB count: {res.data[0]['count']}")

    print("\n--- Verifying Base RV ---")
    res = supabase.table("samar_class_base_rv").select("count").execute()
    print(f"DB count: {res.data[0]['count']}")

    print("\n--- Verifying Options RV ---")
    res = supabase.table("samar_class_options_rv").select("count").execute()
    print(f"DB count: {res.data[0]['count']}")

    print("\n--- Verifying Insurance ---")
    res = supabase.table("ltr_admin_ubezpieczenia").select("count").execute()
    print(f"DB count: {res.data[0]['count']}")


if __name__ == "__main__":
    verify()
