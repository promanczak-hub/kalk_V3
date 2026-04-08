import requests
import uuid

file_id = str(uuid.uuid4())

try:
    res = requests.post(
        "http://localhost:8000/api/extract/async",
        files={
            "file": ("t.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", "application/pdf")
        },
        data={"file_id": file_id},
    )
    print(res.status_code, res.text)
except Exception as e:
    print("Error:", e)
