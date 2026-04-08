import time
import subprocess
import os

duration_seconds = 3600
end_time = time.time() + duration_seconds
runs = 0
successes = 0
failures = 0

print(
    f"Rozpoczynam testy E2E w pętli. Czas trwania: 1 godzina ({duration_seconds} sekund)."
)
print(f"Koniec przewidziany na: {time.strftime('%H:%M:%S', time.localtime(end_time))}.")

# Wymuszenie CI=1 aby playwright nie stawiał serwera HTML z raportem po failu
env = os.environ.copy()
env["CI"] = "1"

while time.time() < end_time:
    runs += 1
    print(
        f"\n--- Uruchomienie {runs} o {time.strftime('%H:%M:%S', time.localtime())} ---"
    )
    start_run = time.time()

    # Wywołanie npx playwright test
    result = subprocess.run(
        "npx playwright test --reporter=list",
        capture_output=True,
        text=True,
        env=env,
        shell=True,
    )

    run_duration = time.time() - start_run

    if result.returncode == 0:
        print(f"Uruchomienie {runs} ZAKOŃCZONE SUKCESEM w czasie {run_duration:.2f}s")
        successes += 1
    else:
        print(f"Uruchomienie {runs} ZAKOŃCZONE BŁĘDEM w czasie {run_duration:.2f}s")
        print("Log błędu:")
        # Displaying only the last lines that might contain the error to avoid flooding stdout
        lines = result.stdout.split("\n")
        for line in lines[-30:]:
            print(f"  {line}")
        if result.stderr:
            print("STDERR:")
            for line in result.stderr.split("\n"):
                print(f"  {line}")
        failures += 1

    time.sleep(1)

print("\n=== Testy E2E zakończone ===")
print(f"Liczba uruchomień: {runs}")
print(f"Sukcesy: {successes}")
print(f"Błędy: {failures}")
