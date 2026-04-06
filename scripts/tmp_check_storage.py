import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load dotenv from current directory
load_dotenv(".env")

from core.database import supabase

def check_storage():
    try:
        # List buckets
        buckets = supabase.storage.list_buckets()
        print("Buckets found:", [b.name for b in buckets])
        
        # Check if 'offers_excel' exists
        if any(b.name == "offers_excel" for b in buckets):
            print("'offers_excel' bucket exists.")
        else:
            print("'offers_excel' bucket missing! We need to create it.")
            
    except Exception as e:
        print("Error checking storage:", str(e))

if __name__ == "__main__":
    check_storage()
