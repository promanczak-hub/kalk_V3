import requests
import json

url = "http://127.0.0.1:8000/api/features/extract-text"
data = {"query_text": "suv 4x4 hak diesel"}
response = requests.post(url, json=data)
print(response.status_code)
print(response.text)
