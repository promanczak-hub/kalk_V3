import os
import requests

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

    for suffix in ["PHEV", "HEV", "EV", "ON", "Pb", "PB"]:
        if val.startswith("T PICK-UP") and val.endswith(suffix):
            return "T PICK-UP", suffix

    return val, ""


def map_old_class_to_new(old_val, samar_classes, engines):
    if not old_val:
        return None, ""
    base_class, suffix = clean_engine_type(old_val)
    if not suffix and "Pb" in old_val:
        suffix = "PB"
    if suffix == "Pb":
        suffix = "PB"
    if suffix == "EV":
        suffix = "BEV"

    mapped_base = None
    if base_class in MAPPING:
        mapped_base = MAPPING[base_class]
    elif old_val in MAPPING:
        mapped_base = MAPPING[old_val]
    else:
        mapped_base = old_val

    # Ensure mapped_base is a valid SAMAR class
    if mapped_base not in samar_classes:
        for sc in samar_classes:
            if mapped_base.startswith(sc):
                mapped_base = sc
                break

    return mapped_base, suffix


def build_engine_mapping(engines):
    # Maps common short suffixes "HEV", "PB" to full engine names
    m = {}
    for e in engines:
        name = e["name"]
        cat = e["category"]
        if "PB" in name.upper() and cat == "spalinowy":
            m["PB"] = name
        elif "ON" in name.upper() and cat == "spalinowy":
            m["ON"] = name
        elif "PHEV" in name.upper():
            m["PHEV"] = name
        elif "BEV" in name.upper():
            m["BEV"] = name
        elif "HEV" in name.upper() and cat == "hybryda":
            m["HEV"] = name
        elif "MHEV" in name.upper() and "PB" in name.upper():
            m["PB-mHEV"] = name
        elif "MHEV" in name.upper() and "ON" in name.upper():
            m["ON-mHEV"] = name
        elif "LPG" in name.upper():
            m["LPG"] = name
    return m


def main():
    try:
        samar_classes_res = requests.get(os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/samar-classes")
        samar_classes = [c["name"] for c in samar_classes_res.json()]
    except Exception as e:
        print(f"Error getting samar classes: {e}")
        return

    try:
        engines_res = requests.get(os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/engines")
        engines = engines_res.json()
        engine_map = build_engine_mapping(engines)
    except Exception as e:
        print(f"Error getting engines: {e}")
        return

    try:
        drafts_res = requests.get(os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/excel-drafts")
        drafts = drafts_res.json()
    except Exception as e:
        print(f"Error getting excel drafts: {e}")
        return

    kor_marka_sheet = None
    for sheet in drafts:
        if sheet["sheet_name"] == "KOR. MARKA":
            kor_marka_sheet = sheet
            break

    if not kor_marka_sheet:
        print("Sheet KOR. MARKA not found")
        return

    # New Columns Def
    new_columns_def = [
        {"field": "col_1", "headerName": "KLASA", "width": 250},
        {"field": "col_2", "headerName": "MARKA", "width": 150},
        {"field": "col_3", "headerName": "MODEL", "width": 150},
        {"field": "col_4", "headerName": "SILNIK", "width": 200},
        {"field": "col_5", "headerName": "KLUCZ (Złączony)", "width": 300},
        {"field": "col_6", "headerName": "KOREKTA", "width": 150},
    ]

    old_rows = kor_marka_sheet.get("data_rows", [])
    new_rows = []

    # Analyze old columns:
    # 'col_1': CLASS
    # 'col_2': BRAND
    # 'col_3': ENGINE
    # 'col_4': OLD KEY
    # 'col_5': CORRECTION (%)

    for i, row in enumerate(old_rows):
        old_class = row.get("col_1", "")
        old_brand = row.get("col_2", "")
        old_engine = row.get("col_3", "")
        old_correction = row.get("col_5", "")

        # Don't process completely empty rows
        if not old_class and not old_brand and not old_correction:
            continue

        new_class, suffix = map_old_class_to_new(old_class, samar_classes, engines)
        if not new_class:
            new_class = old_class  # fallback

        # Determine engine
        new_engine = ""
        # Try using suffix from class if old_engine is empty
        engine_hint = old_engine if old_engine else suffix
        if engine_hint in engine_map:
            new_engine = engine_map[engine_hint]
        elif old_engine:
            # Fallback search
            for e in engines:
                if (
                    old_engine.upper() in e["name"].upper()
                    or e["name"].upper() in old_engine.upper()
                ):
                    new_engine = e["name"]
                    break

        if not new_engine:
            new_engine = engine_hint  # fallback

        # Clean up BRAND (remove extra spaces)
        brand_clean = str(old_brand).strip() if old_brand else ""

        # Model is empty by default
        model_clean = ""

        # Build new row
        klucz = (
            f"{new_class or ''}{brand_clean}{model_clean}{new_engine or ''}".replace(
                " ", ""
            )
        )

        new_row = {
            "id": i + 1,
            "col_1": new_class,
            "col_2": brand_clean,
            "col_3": model_clean,
            "col_4": new_engine,
            "col_5": klucz,
            "col_6": old_correction,
        }
        new_rows.append(new_row)

    payload = {"columns_def": new_columns_def, "data_rows": new_rows}

    try:
        put_res = requests.put(
            os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/excel-drafts/KOR. MARKA", json=payload
        )
        if put_res.status_code == 200:
            print(f"Successfully updated KOR. MARKA with {len(new_rows)} rows.")
        else:
            print(f"Errors updating KOR. MARKA: {put_res.text}")
    except Exception as e:
        print(f"Exception updating KOR. MARKA: {e}")


if __name__ == "__main__":
    main()
