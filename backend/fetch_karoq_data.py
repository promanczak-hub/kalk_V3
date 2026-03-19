import os
import json
from supabase import create_client
from dotenv import load_dotenv

def main():
    # Load from backend/.env if it exists
    load_dotenv('.env')
    
    url = os.environ.get('SUPABASE_URL')
    # The .env file has SUPABASE_KEY, let's try that.
    key = os.environ.get('SUPABASE_KEY')
    
    if not url or not key:
        print(f"Missing SUPABASE_URL ({url}) or SUPABASE_KEY ({key})")
        return

    print(f"Connecting to {url}")
    supabase = create_client(url, key)
    
    try:
        # Fetch by looking for CPYJZ25F in the synthesis_data JSON
        # Since we don't know the exact column, let's fetch all and filter in Python
        res = supabase.table('vehicle_synthesis').select('*').limit(100).execute()
        
        if res.data:
            print(f"Found {len(res.data)} records in vehicle_synthesis.")
            matches = []
            for row in res.data:
                synth = row.get('synthesis_data', {})
                # Check if CPYJZ25F is anywhere in the synthesis_data
                if 'CPYJZ25F' in str(synth):
                    matches.append(row)
            
            if matches:
                print(f"Found {len(matches)} matches for CPYJZ25F.")
                with open('karoq_synthesis.json', 'w', encoding='utf-8') as f:
                    json.dump(matches, f, indent=2, ensure_ascii=False)
                print("Data saved to karoq_synthesis.json")
            else:
                print("No records matched CPYJZ25F in the synthesis_data.")
                # Save first 5 to see structure
                with open('sample_synthesis.json', 'w', encoding='utf-8') as f:
                    json.dump(res.data[:5], f, indent=2, ensure_ascii=False)
                print("Saved first 5 records to sample_synthesis.json to inspect structure.")
        else:
            print("No data returned from vehicle_synthesis.")
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == '__main__':
    main()
