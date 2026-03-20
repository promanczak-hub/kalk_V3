import os
import re

BACKEND_DIR = r"d:\kalk_v3\backend\api"
FRONTEND_DIR = r"d:\kalk_v3\frontend\src"

# Wyszukiwanie definicji endpointów w backendzie
endpoint_pattern = re.compile(r'@router\.(?:get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]')

endpoints = set()

for root, _, files in os.walk(BACKEND_DIR):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                content = f.read()
                matches = endpoint_pattern.findall(content)
                for match in matches:
                    # Normalizacja, usunięcie parametrów ścieżki i ukośnika na końcu
                    base_path = match.split('/{')[0].rstrip('/')
                    if base_path:
                        endpoints.add(base_path)

print(f"Znaleziono {len(endpoints)} bazowych definicji endpointów w backendzie.")

# Zbierz całą zawartość frontendu
frontend_content = ""
for root, _, files in os.walk(FRONTEND_DIR):
    for file in files:
        if file.endswith((".ts", ".tsx", ".js", ".jsx")):
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                frontend_content += f.read()

# Szukaj osieroconych endpointów
orphaned = []
for ep in endpoints:
    # Upewniamy się, że szukamy ścieżki bez "/" na początku, jako że endpoint może być składany
    ep_to_search = ep.lstrip('/')
    if ep_to_search not in frontend_content:
        orphaned.append(ep)

print(f"\nZnaleziono {len(orphaned)} encji, które potencjalnie NIE SĄ wywoływane na frontendzie:")
for o in sorted(orphaned):
    print(f" - {o}")
