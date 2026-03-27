import subprocess

with open("matrix_refresh.log", "w", encoding="utf-8") as f:
    subprocess.run(
        ["python", "test_refresh_fabia.py"], stdout=f, stderr=subprocess.STDOUT
    )
