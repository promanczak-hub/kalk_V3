import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import supabase

def main():
    resp = supabase.table('reverse_search.model_document_sources').select('id, original_filename, variant_count, extracted_data').ilike('original_filename', '%Terramar%').execute()
    for row in resp.data:
        features = 0
        if row.get('extracted_data'):
            variants = row['extracted_data'].get('variants', [])
            if variants:
                features = len(variants[0].get('features', []))
        print(f"{row['original_filename']}: {row['variant_count']} variants, {features} features per variant, id: {row['id']}")

if __name__ == '__main__':
    main()
