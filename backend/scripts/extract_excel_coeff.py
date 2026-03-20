import pandas as pd

EXCEL_PATH = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026_final.xlsx"


def extract_coefficients():
    # Attempt to load the excel file and look at the first few sheets and their structures
    try:
        xls = pd.ExcelFile(EXCEL_PATH)
        print("Available sheets:", xls.sheet_names)

        # Searching for the SAMAR class
        if "TAB.WR KLASA" in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name="TAB.WR KLASA")
            print("--- TAB.WR KLASA ---")
            print(df.head(20).to_string())

        if "TAB. OKRES FINAL" in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name="TAB. OKRES FINAL")
            print("--- TAB. OKRES FINAL ---")
            print(df.head(20).to_string())

            # Additional logic to find specific matrix/coefficients...

    except Exception as e:
        print("Error reading excel:", str(e))


if __name__ == "__main__":
    extract_coefficients()
