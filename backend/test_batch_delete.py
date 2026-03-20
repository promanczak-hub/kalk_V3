import requests

url = "http://127.0.0.1:8000/api/delete-vehicles-batch"
data = {"vehicle_ids": ["test1", "test2"]}
response = requests.post(url, json=data)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
