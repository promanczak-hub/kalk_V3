import requests

PROJECT_REF = "gnpsdiarmwvqhqbyetce"
ACCESS_TOKEN = "sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9"
MIGRATION_FILE = (
    r"d:\kalk_v3\supabase\migrations\20260402214700_add_alternatives_rpcs.sql"
)


def apply_migration():
    try:
        with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
            sql_query = f.read()
    except Exception as e:
        print(f"Error reading migration file: {e}")
        return

    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/query"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {"query": sql_query}

    print(f"Sending migration to Supabase API for project {PROJECT_REF}...")

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code in [200, 201]:
            print("Migration applied successfully via Management API!")
            print(response.text)
        else:
            print(f"Failed to apply migration. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    apply_migration()
