import os
from dotenv import load_dotenv
from supabase import create_client

def main():
    load_dotenv()
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    
    try:
        client = create_client(url, key)
        
        # Zapytanie o rekordy w tabeli koszty_opon dla srednicy 16
        res = client.table('koszty_opon').select('*').eq('srednica', '16').execute()
        print(f"Dane w koszty_opon dla srednica=16:")
        for row in res.data:
            print(row)
            
        # Zobaczmy wszystkie dostępne kategorie/klasy
        res_all = client.table('koszty_opon').select('klasa').execute()
        klasy = set(r['klasa'] for r in res_all.data if 'klasa' in r)
        print(f"\nDostępne klasy w tabeli: {klasy}")

    except Exception as e:
        print(f"Błąd podczas odpytywania bazy: {e}")

if __name__ == "__main__":
    main()
