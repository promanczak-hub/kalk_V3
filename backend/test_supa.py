import os
from dotenv import load_dotenv
from supabase import create_client

def main():
    load_dotenv()
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    print(f"Checking URL: {url}")
    
    try:
        client = create_client(url, key)
        # Checking connection to a known table in Kalkulator V3
        res = client.table('samar_classes').select('id').limit(1).execute()
        print("Connection to Kalkulator V3 Supabase OK!")
    except Exception as e:
        print(f"Error connecting: {e}")

if __name__ == "__main__":
    main()
