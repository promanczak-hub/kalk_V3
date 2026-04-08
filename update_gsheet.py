import gspread
from google.oauth2.service_account import Credentials

key_path = "D:/kalk_v3/backend/google_sa_key.json"
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(key_path, scopes=scopes)
gc = gspread.authorize(creds)
ss = gc.open_by_key("1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q")

# 1. Update EDGE features
print("Updating EDGE features in 'cechy' sheet...")
edge_keywords = [
    "masaż",
    "wentylowane",
    "roleta",
    "rolety",
    "paddle_shift",
    "kierownicy",
    "zmiana biegów",
    "wymieniarka",
    "zmieniarka",
    "głośników",
    "indukcyjna",
    "head-up",
    "kąt rampowy",
    "kąt natarcia",
    "kąt zejścia",
    "brodzenia",
    "kąt",
    "podświetlane lusterka",
    "gniazda usb",
    "gniazdo 12v",
    "uchwyty",
]

edge_functional_names = [
    "Roleta szyby tylnej regulowana elektrycznie",
    "Rolety przeciwsłoneczne boczne",
    "Fotele przednie z funkcją masażu",
    "Fotele tylne z funkcją masażu",
    "Fotele tylne wentylowane",
    "ładowarka indukcyjna do smartfonów",
    "Wyświetlacz typu Head-Up",
    "Zmiana biegów w kierownicy",
    "System audio (liczba głośników)",  # Sometimes written with typo
    "zestaw naprawczy",
    "sygnalizacja spadku ciśnienia w oponach",
    "Kąt rampowy",
    "Kąt natarcia",
    "Kąt zejścia",
    "Głębokość brodzenia",
    "podświetlane lusterka",
    "gniazda usb",
    "gniazdo 12v",
]

ws_cechy = ss.worksheet("cechy")
records = ws_cechy.get_all_records()
# find column index for Feature_Tier
headers = ws_cechy.row_values(1)
if "Feature_Tier" in headers:
    tier_col_idx = headers.index("Feature_Tier") + 1
else:
    print("Feature_Tier column not found!")
    tier_col_idx = 0

updates = []
for i, row in enumerate(records, start=2):  # +2 because 1-indexed and header
    fn = row.get("Functional_Name", "").strip().lower()
    tk = row.get("Technical_Key", "").strip().lower()

    is_edge = False
    for kw in edge_keywords:
        if kw in fn.lower() or kw in tk.lower():
            is_edge = True
            break

    if is_edge and tier_col_idx > 0:
        # Avoid overriding CORE
        if row.get("Feature_Tier", "").upper() != "CORE":
            updates.append(
                {
                    "range": f"{gspread.utils.rowcol_to_a1(i, tier_col_idx)}",
                    "values": [["EDGE"]],
                }
            )

# Batch update for EDGE
if updates:
    ws_cechy.batch_update(updates)
    print(f"Updated {len(updates)} features to EDGE tier.")
else:
    print("No features matched for EDGE tier.")


# 2. Update body_types
print("Updating 'body_types' sheet...")
ws_body = ss.worksheet("body_types")
body_headers = ws_body.row_values(1)

# Ensure Subkategoria / Kategoria Nadrzędna exists
if len(body_headers) < 4 or "Podkategoria" not in body_headers:
    # Adding a 4th column header
    ws_body.update_cell(1, 4, "Podkategoria")

# We want to add:
# ID, Nazwa_Nadwozia, Typ_Pojazdu, Podkategoria
new_rows = [
    ["21", "Chłodnia", "Ciężarowy", "Podwozie"],
    ["22", "Izoterma", "Ciężarowy", "Podwozie"],
    ["23", "Skrzyniowa", "Ciężarowy", "Podwozie"],
    ["24", "Kontener", "Ciężarowy", "Podwozie"],
]

# get all rows to determine where to append
all_body_rows = ws_body.get_all_values()
# Instead of appending, just overwrite from the end
start_row = len(all_body_rows) + 1
range_str = f"A{start_row}:D{start_row + len(new_rows) - 1}"
ws_body.update(range_str, new_rows)

print(f"Appended new body types with subcategories to {range_str}.")

print("Done.")
