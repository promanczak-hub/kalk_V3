import requests
import uuid

filepath = r"C:\Users\proma\Downloads\MariuszGawareckiCBREF O R D R A N G E R 2 . 3 E C O B O O S T P H E V 2 8 1 K M A 1 0 E - 4 W DOFERTA_nr_3387_2026_04_z_dnia_2026-04-09.pdf"
url = "http://localhost:8000/api/extract/async"

file_id = str(uuid.uuid4())
print(f"Uploading file as ID: {file_id}")

with open(filepath, 'rb') as f:
    files = {'file': f}
    data = {'file_id': file_id}
    response = requests.post(url, files=files, data=data)

print("Status code:", response.status_code)
print("Response:", response.text)
