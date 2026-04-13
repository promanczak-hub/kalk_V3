import requests
import uuid
import time
import sys

file_path = r"C:\Users\proma\Downloads\SANTA FE Hybrid.pdf"
url = "http://127.0.0.1:8000/api/extract/async"
file_id = str(uuid.uuid4())

print(f"Starting upload for file ID: {file_id}")
start_time = time.time()

try:
    with open(file_path, "rb") as f:
        files = {"file": ("SANTA FE Hybrid.pdf", f, "application/pdf")}
        data = {"file_id": file_id}

        response = requests.post(url, files=files, data=data, timeout=60)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error occurred: {e}")
    sys.exit(1)

elapsed = time.time() - start_time
print(f"Finished in {elapsed:.2f} seconds.")
