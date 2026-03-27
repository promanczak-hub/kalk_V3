import os
import requests
import openpyxl

EXCEL_PATH = r"C:\Users\proma\Downloads\DRAFT KALKULATORA WARTOŚCI REZYDUALNYCH ver aktualna JŁ 02.02 (version 1).xlsx"
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

MAPPING = {
    "A": "Podstawowa - A MINI",
    "Asport": "Sportowo-rekreacyjne - A MINI",
    "B": "Podstawowa - B MAŁE",
    "Bsport": "Sportowo-rekreacyjne - B MAŁE",
    "Bvan": "Vany - B MICROVANY",
    "Bsuv": "Terenowo-rekreacyjne (SUV) - B MAŁE",
    "C": "Podstawowa - C NIŻSZA ŚREDNIA",
    "Csport": "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA",
    "Cvan": "Vany - C MINIVANY",
    "Csuv": "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA",
    "D": "Podstawowa - D ŚREDNIA",
    "Dsport": "Sportowo-rekreacyjne - D ŚREDNIA",
    "Dvan": "Vany - D VANY",
    "Dsuv": "Terenowo-rekreacyjne (SUV) - D ŚREDNIA",
    "E": "Podstawowa - E WYŻSZA",
    "Esuv": "Terenowo-rekreacyjne (SUV) - E WYŻSZA",
    "ESUV": "Terenowo-rekreacyjne (SUV) - E WYŻSZA",
    "F": "Podstawowa - F LUKSUSOWE",
    "Fsport": "Sportowo-rekreacyjne - F LUKSUSOWE",
    "Fsuv": "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE",
    "M": "Podstawowa - G SUPER LUKSUSOWE",
    "Mvan": "Vany - F LUKSUSOWE",
    "T PICK-UP": "Pick-up - PICK-UP",
    "P": "Średnie dostawcze - ŚREDNIE DOSTAWCZE",
    "R": "Minibusy - I MINIBUSY",
}


def clean_engine_type(val: str):
    if val == "T PICK-UP":
        return "T PICK-UP", ""

    for suffix in ["PHEV", "HEV", "EV", "ON", "Pb", "PB"]:
        if val.endswith(suffix) and val != suffix:
            base = val[: -len(suffix)]
            if base in MAPPING:
                return base, suffix

    if val.startswith("T PICK-UP"):
        for suffix in ["PHEV", "HEV", "EV", "ON", "Pb", "PB"]:
            if val.endswith(suffix):
                return "T PICK-UP", suffix

    return val, ""


def map_class_and_engine(val: str, samar_classes: list, engine_names: list):
    base, suffix = clean_engine_type(val)
    if not suffix:
        return val

    s = suffix.upper()
    if s == "PB":
        s = "PB"
    if s == "EV":
        s = "BEV"

    mapped_base = MAPPING.get(base, base)
    mapped_engine = ""
    for en in engine_names:
        en_upper = en.upper()
        if s == "PB" and ("BENZYNA" in en_upper or "PB" in en_upper):
            mapped_engine = en
            break
        if s == "ON" and "DIESEL" in en_upper:
            mapped_engine = en
            break
        if s == "PHEV" and "PHEV" in en_upper:
            mapped_engine = en
            break
        if (
            s == "HEV"
            and "HEV" in en_upper
            and "PHEV" not in en_upper
            and "MHEV" not in en_upper
        ):
            mapped_engine = en
            break
        if (s == "BEV" or s == "EV") and ("EV" in en_upper and "HEV" not in en_upper):
            mapped_engine = en
            break

    if mapped_base and mapped_engine:
        res = f"{mapped_base} {mapped_engine}"
        return res
    return val


def main():
    print(f"Loading data from API {API_URL}...")
    try:
        classes_res = requests.get(f"{API_URL}/api/samar-classes")
        classes_res.raise_for_status()
        samar_classes = [c["name"] for c in classes_res.json()]

        engines_res = requests.get(f"{API_URL}/api/engines")
        engines_res.raise_for_status()
        engines = [e["name"] for e in engines_res.json()]
    except Exception as e:
        print(f"Error fetching dependencies: {e}")
        return

    print("Opening Excel workbook...")
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    if "TAB. OKRES FINAL" not in wb.sheetnames:
        print("Sheet TAB. OKRES FINAL not found.")
        return

    ws = wb["TAB. OKRES FINAL"]

    print("Parsing sheet...")
    # Year headers
    rok_cols = []

    # Expected columns definition for frontend
    columns_def = [
        {
            "field": "klasa_samar",
            "headerName": "KLASA",
            "width": 250,
            "editable": True,
            "type": "singleSelect",
        }
    ]

    # We create the column definitions based on the 8 columns
    period_labels = [
        "0 (35k)",
        "1 (35k)",
        "2 (70k)",
        "3 (105k)",
        "4 (140k)",
        "5 (175k)",
        "6 (210k)",
        "7 (245k)",
    ]
    for i in range(8):
        columns_def.append(
            {
                "field": f"rok_{i}",
                "headerName": period_labels[i],
                "width": 110,
                "editable": True,
                "type": "string",  # keep simple
            }
        )

    data_rows = []
    id_counter = 1

    # In TAB. OKRES FINAL, rows start from 3
    for row in ws.iter_rows(min_row=3, values_only=True):
        cell_val = row[0]
        if not cell_val or not isinstance(cell_val, str):
            continue
        # Skip section headers
        if cell_val in ("BENZYNA", "DIESEL", "EV", "PHEV", "HEV", "KLASY", "KLASA"):
            continue

        mapped_name = map_class_and_engine(cell_val, samar_classes, engines)

        row_dict = {"id": id_counter, "klasa_samar": mapped_name}

        # Read columns B to I (indices 1 to 8)
        for i in range(8):
            val = row[i + 1]
            if val is None:
                row_dict[f"rok_{i}"] = ""
            else:
                # Convert fraction to percentage representation if desirable,
                # or just float as string. Let's format as percentage.
                # (Control center cells are usually strings if not typed specifically)
                # Let's keep decimal format so it's easier to edit and save.
                row_dict[f"rok_{i}"] = str(round(float(val), 4))

        data_rows.append(row_dict)
        id_counter += 1

    print(f"Parsed {len(data_rows)} rows. Updating backend...")

    payload = {"columns_def": columns_def, "data_rows": data_rows}

    try:
        r = requests.put(
            f"{API_URL}/api/excel-drafts/TAB.%20OKRES%20FINAL", json=payload
        )
        r.raise_for_status()
        print("Successfully updated TAB. OKRES FINAL schema and data in database.")
    except Exception as e:
        print(f"Error updating API: {e}")
        if hasattr(e, "response") and e.response:
            print(e.response.text)


if __name__ == "__main__":
    main()
