import subprocess

with open("logs_ascii.txt", "w", encoding="utf-8") as f:
    subprocess.run(["python", "test_fabia_jobs.py"], stdout=f, stderr=subprocess.STDOUT)
