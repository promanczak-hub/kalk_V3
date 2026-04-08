import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()
key_path = os.environ.get("GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json")
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(key_path, scopes=scopes)
gc = gspread.authorize(creds)
ws = gc.open_by_key("1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q").worksheet("cechy")

data = ws.get_all_values()
headers = [h.strip() for h in data[0]]

# Handle case insensitive headers
col_idx = {h.lower(): i for i, h in enumerate(headers)}
body_idx = col_idx.get("body_context")
tech_idx = col_idx.get("technical_key")

fixes = {
    "TRUCK": "Podwozie, Furgon",
    "CHŁODNIA": "Podwozie, Furgon",
    "IZOTERMA": "Podwozie, Furgon",
    "KONTENER": "Podwozie",
    "WYWROTKA": "Podwozie",
}

updates = []
for i, row in enumerate(data):
    if i == 0:
        continue
    if len(row) > body_idx:
        val = row[body_idx]
        original_val = val
        val_upper = val.strip().upper()

        needs_update = False
        parts = [p.strip() for p in val_upper.replace("/", ",").split(",")]
        new_parts = []
        for p in parts:
            if p in fixes:
                new_parts.append(fixes[p])
                needs_update = True
            elif p:
                # Keep existing valid parts, capitalize the first letter like they normally are (or uppercase)
                new_parts.append(p)

        if needs_update:
            # unique them while preserving order
            unique_parts = []
            for p in new_parts:
                for sub_p in p.split(","):
                    sub_p = sub_p.strip()
                    if (
                        sub_p
                        and sub_p.title() not in unique_parts
                        and sub_p.capitalize() not in unique_parts
                        and sub_p not in unique_parts
                    ):
                        # title case things like 'Furgon', 'Podwozie'
                        unique_parts.append(
                            sub_p.title()
                            if sub_p.lower() in ("furgon", "podwozie", "pickup", "van")
                            else sub_p
                        )

            final_val = ", ".join(unique_parts)
            updates.append(
                {
                    "range": gspread.utils.rowcol_to_a1(i + 1, body_idx + 1),
                    "values": [[final_val]],
                }
            )
            print(f"Zmieniono {row[tech_idx]} z '{original_val}' na '{final_val}'")

if updates:
    ws.batch_update(updates)
    print(f"Zrobione! Zaktualizowano {len(updates)} komórek.")
else:
    print("Brak zmian do wprowadzenia - wygląda na to że arkusz jest już poprawny!")
