from core.database import supabase


def main():
    res = supabase.table("samar_classes").select("id, name").execute()
    for row in res.data:
        print(f"{row['id']}: {row['name']}")


if __name__ == "__main__":
    main()
