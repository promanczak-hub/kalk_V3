import gspread
from google.oauth2.service_account import Credentials

SA_KEY_PATH = r"D:\kalk_v3\backend\google_sa_key.json"
SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"


def main():
    gc = gspread.authorize(
        Credentials.from_service_account_file(
            SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    )
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = ss.worksheet("cechy")

    rows = ws.get_all_values()

    new_headers = [
        "Technical_Key (PK)",
        "Functional_Name",
        "Category (FK)",
        "Data_Type (ENUM: int/float/bool/string/enum)",
        "Unit",
        "Transformation (ENUM)",
        "Vehicle_Category (ENUM)",
        "Is_Filterable (bool)",
        "Is_Derived (bool)",
        "Is_Contextual (bool)",
    ]

    # Old indices we want to keep
    # 0, 1, 2, 3, 4, 6, 9, 13, 14, 15
    indices_to_keep = [0, 1, 2, 3, 4, 6, 9, 13, 14, 15]

    new_rows = []
    # Replace the headers
    new_rows.append(new_headers)

    # Process the rest of the rows
    for row in rows[1:]:
        # Extent row with empty strings if it's shorter than the max index
        while len(row) <= max(indices_to_keep):
            row.append("")

        new_row = [row[i] for i in indices_to_keep]
        new_rows.append(new_row)

    print(f"Prepared {len(new_rows)} rows to update.")

    # Clear the worksheet
    ws.clear()

    # Update the worksheet with new data
    ws.update(values=new_rows, range_name=f"A1:J{len(new_rows)}")
    print("Worksheet updated successfully.")


if __name__ == "__main__":
    main()
