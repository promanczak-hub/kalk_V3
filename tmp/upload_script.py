import requests
import uuid
from pathlib import Path

pdf_path = Path(r"C:\Users\proma\Downloads\car-card-CJ6WHFJY.pdf")
url = "http://localhost:8000/api/extract/async"

file_id = str(uuid.uuid4())

if not pdf_path.exists():
    print(f"Error: Plik {pdf_path} nie istnieje!")
    exit(1)

with open(pdf_path, "rb") as f:
    files = {"file": (pdf_path.name, f, "application/pdf")}
    data = {"file_id": file_id}

    print(f"Wysyłanie pliku do {url} z ID: {file_id}...")
    response = requests.post(url, files=files, data=data)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
