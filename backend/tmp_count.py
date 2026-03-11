from core.database import supabase


def main():
    try:
        res = (
            supabase.table("ltr_admin_wspolczynniki_szkodowe")
            .select("id", count="exact")
            .execute()
        )
        print(f"COUNT_RESULT: {res.count}")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
