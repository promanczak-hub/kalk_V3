from core.database import supabase


def main():
    fabia_id = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"

    # Test ordinary eq
    res_eq = (
        supabase.table("vehicle_synthesis").select("id").eq("id", fabia_id).execute()
    )
    print(f"Eq fetch: {len(res_eq.data)}")

    # Test in_
    res_in = (
        supabase.table("vehicle_synthesis").select("id").in_("id", [fabia_id]).execute()
    )
    print(f"In fetch: {len(res_in.data)}")


if __name__ == "__main__":
    main()
