import os
from supabase import create_client
from dotenv import load_dotenv
import requests

load_dotenv("../frontend/.env.local")

url = os.environ.get("VITE_SUPABASE_URL")
key = os.environ.get("VITE_SUPABASE_ANON_KEY")
supabase = create_client(url, key)

res = (
    supabase.table("vehicle_synthesis")
    .select("synthesis_data")
    .order("created_at", desc=True)
    .limit(10)
    .execute()
)

pdf_url = None
for row in res.data:
    data = row.get("synthesis_data", {})
    if data and data.get("file_id"):
        # Let's try to get public URL
        file_path = f"{data['file_id']}-{data.get('file_name', 'doc.pdf')}"
        info = supabase.storage.from_("raw-vehicle-pdfs").get_public_url(file_path)
        pdf_url = (
            info
            if isinstance(info, str)
            else info.public_url
            if hasattr(info, "public_url")
            else None
        )

        # If it doesn't work, we can check if there's any file in the bucket
        break

if not pdf_url:
    files = supabase.storage.from_("raw-vehicle-pdfs").list()
    if files and len(files) > 0:
        pdf_url = supabase.storage.from_("raw-vehicle-pdfs").get_public_url(
            files[-1]["name"]
        )

if pdf_url:
    print(f"Testing URL: {pdf_url}")
    # Do an OPTIONS request to check CORS
    req = requests.options(
        pdf_url,
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    print("OPTIONS Headers:", req.headers)

    # Do a GET request to check Content-Disposition
    req_get = requests.get(pdf_url)
    print("GET Content-Type:", req_get.headers.get("Content-Type"))
    print("GET Content-Disposition:", req_get.headers.get("Content-Disposition"))
    print(
        "GET Access-Control-Allow-Origin:",
        req_get.headers.get("Access-Control-Allow-Origin"),
    )
else:
    print("Could not find a PDF URL to test.")
