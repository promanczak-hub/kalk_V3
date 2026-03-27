import os
from pathlib import Path
from dotenv import load_dotenv

# Define the base directory (where .env should be)
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

print(f"CWD: {os.getcwd()}")
print(f"Looking for .env at: {env_path}")
print(f"Does .env exist? {env_path.exists()}")

load_dotenv(dotenv_path=env_path)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

print(f"URL: {url}")
print(f"KEY: {key}")
