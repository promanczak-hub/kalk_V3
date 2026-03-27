import os
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

print(f"URL: {url}")
print(f"KEY: {key}")

if url and url.startswith('"'):
    print("WARNING: URL starts with a quote!")
if key and key.startswith('"'):
    print("WARNING: KEY starts with a quote!")
