import requests

base_url = "http://localhost:8000/api/excel-drafts/TAB. PRZEBIEG"

r = requests.get(base_url)
data = r.json()

print("Columns:", len(data.get("columns_def", [])))
print("Rows:", len(data.get("data_rows", [])))
if data.get("data_rows"):
    print("Sample row:")
    # print string representation properly
    print(data["data_rows"][1])
