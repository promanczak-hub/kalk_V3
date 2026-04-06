import os
from sqlalchemy import create_engine, text

# Use direct connection string from env if possible, else default to typical local/remote connection
db_url = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)
# The project seems to be using an online supabase db. I will try the connection URL from other files or just print SUPABASE_URL.
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("DATABASE_URL", "")

print(f"Connecting to: {db_url.split('@')[-1] if '@' in db_url else db_url}")

if not db_url:
    print("No DATABASE_URL found.")
else:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM body_types"))
        for r in res.mappings():
            print(dict(r))
