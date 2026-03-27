import requests


def test_cors():
    url = "http://127.0.0.1:8000/api/control-center"
    origin = "http://localhost:3000"

    print(f"Testing OPTIONS request to {url} with Origin {origin}...")

    try:
        response = requests.options(
            url,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        print(f"Status Code: {response.status_code}")
        print(
            f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}"
        )

        if response.headers.get("Access-Control-Allow-Origin") == origin:
            print("✅ CORS fix verified: Origin allowed.")
        else:
            print("❌ CORS fix failed: Origin NOT allowed.")
            print(f"Headers: {response.headers}")

    except Exception as e:
        print(f"❌ Error during request: {e}")
        print("Note: Make sure the backend server is running at http://127.0.0.1:8000")


if __name__ == "__main__":
    test_cors()
