import requests
import time

print("Creating 2MB dummy file...")
dummy_content = b"0" * (2 * 1024 * 1024)

print("Sending POST request to localhost:8000...")
start = time.time()
try:
    response = requests.post(
        "http://127.0.0.1:8000/api/extract/async",
        data={"file_id": "dummy-test-123"},
        files={"file": ("dummy.pdf", dummy_content, "application/pdf")},
        timeout=10,
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.Timeout:
    print(
        "Request TIMED OUT after 10 seconds! This confirms the Docker MTU/Networking bug."
    )
except Exception as e:
    print(f"Request failed with error: {e}")

print(f"Total time: {time.time() - start:.2f}s")
