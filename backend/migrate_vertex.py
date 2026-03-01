from supabase import Client


def main():
    # 1. Import local client BEFORE load_dotenv messes up the environ!
    from core.database import supabase as new_client

    # 2. Connect to old DB
    from dotenv import dotenv_values

    old_env = dotenv_values("D:\\VertexExtractor\\backend\\.env")

    old_url = old_env.get("SUPABASE_URL")
    old_key = old_env.get("SUPABASE_KEY")

    if not old_url or not old_key:
        print("Nie znaleziono kluczy do starej bazy.")
        return

    from supabase import create_client

    old_client: Client = create_client(old_url, old_key)
    print("Połączono ze starą bazą.")

    # 3. Fetch data
    response = old_client.table("vehicle_synthesis").select("*").execute()
    data = response.data

    print(f"Pobrano {len(data)} rekordów ze starej bazy.")

    if not data:
        print("Brak danych do skopiowania.")
        return

    # 4. Insert data
    # Kopiujemy po kolei, dla bezpieczeństwa jako upsert
    res = new_client.table("vehicle_synthesis").upsert(data).execute()
    print(f"Upsert returned data length: {len(res.data) if res.data else 0}")
    print("Skopiowano pomyślnie. Nowe ID dodane do lokalnej bazy.")


if __name__ == "__main__":
    main()
