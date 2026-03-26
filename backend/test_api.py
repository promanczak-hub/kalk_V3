import requests

base_url = "http://localhost:8000/api/excel-drafts/TAB. PRZEBIEG"

payload = {
    "columns_def": [{"field": "col_1", "headerName": "Test", "width": 150}],
    "data_rows": [{"id": 1, "col_1": "abc"}]
}

try:
    r = requests.put(base_url, json=payload)
    print(r.status_code)
    print(r.text)
except Exception as e:
    print("Error:", e)
