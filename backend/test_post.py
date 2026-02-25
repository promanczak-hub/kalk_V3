import urllib.request
import json
import urllib.error

try:
    req_get = urllib.request.urlopen("http://127.0.0.1:8000/api/control-center")
    d = json.loads(req_get.read())
    req_post = urllib.request.Request(
        "http://127.0.0.1:8000/api/control-center",
        data=json.dumps(d).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    res = urllib.request.urlopen(req_post)
    print("Success:", res.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("Error:", e.code, e.reason)
    print(e.read().decode("utf-8"))
except Exception as e:
    print("Exception:", e)
