import requests
import json
import sys

# Constants
PROJECT_REF = "gnpsdiarmwvqhqbyetce"
ACCESS_TOKEN = "sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9"
MIGRATION_FILE = "../supabase/migrations/20260319110000_fix_margin_double_apply.sql"

def apply_migration():
    # Read the SQL file
    try:
        with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
            sql_query = f.read()
    except Exception as e:
        print(f"Error reading migration file: {e}")
        return

    # Supabase Management API endpoint for executing SQL
    # Note: Management API for SQL execution is often privileged or limited.
    # We will try the 'query' endpoint if it's available or use the standard CLI-like approach.
    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/query"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": sql_query
    }

    print(f"Sending migration to Supabase API for project {PROJECT_REF}...")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201 or response.status_code == 200:
            print("Migration applied successfully via Management API!")
            print(response.text)
        else:
            print(f"Failed to apply migration. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            # If 'query' endpoint is 404, the API might have changed or requires a different approach.
            if response.status_code == 404:
                print("Management API 'query' endpoint not found. This feature might be restricted or uses a different URL.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    apply_migration()
