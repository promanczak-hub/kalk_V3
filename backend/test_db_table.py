from supabase import create_client, Client

url: str = "http://127.0.0.1:54321"
key: str = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"
supabase: Client = create_client(url, key)

try:
    response = supabase.table("control_center").select("*").execute()
    print("Table exists! Data:", response.data)
except Exception as e:
    print("Error:", e)
