"""Check samar_classes full structure."""

import os

os.environ.setdefault("VITE_SUPABASE_URL", "http://127.0.0.1:54321")
os.environ.setdefault(
    "VITE_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9."
    "CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)

from supabase import create_client

sb = create_client(
    os.environ["VITE_SUPABASE_URL"],
    os.environ["VITE_SUPABASE_ANON_KEY"],
)

sc = sb.table("samar_classes").select("*").order("id").execute()
print(f"Total classes: {len(sc.data)}\n")

if sc.data:
    print("COLUMNS:", list(sc.data[0].keys()))
    print()

for r in sc.data:
    name = r.get("name", "")
    models = r.get("example_models", "")
    print(f"ID={r['id']:3} | {name}")
    if models:
        print(f"  example_models: {models[:150]}")
    else:
        print(f"  example_models: (EMPTY)")
    print()
