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

    for suffix in ["PHEV", "HEV", "EV", "ON", "Pb"]:
        if val.endswith(suffix) and val != suffix:
            base = val[: -len(suffix)]
            if base in MAPPING:
                return base, suffix

    for suffix in ["PHEV", "HEV", "EV", "ON", "Pb"]:
        if val.startswith("T PICK-UP") and val.endswith(suffix):
            return "T PICK-UP", suffix

    return val, ""


def map_old_class_to_new(old_val, samar_classes):
    base_class, suffix = clean_engine_type(old_val)
    if base_class in MAPPING:
        new_base = MAPPING[base_class]
        if suffix:
            candidate = f"{new_base}{suffix}"
            if candidate in samar_classes:
                return candidate
            else:
                return new_base
        else:
            return new_base

    if old_val in MAPPING:
        return MAPPING[old_val]

    return None


def main():
    try:
        samar_classes_res = requests.get(os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/samar-classes")
        samar_classes = [c["name"] for c in samar_classes_res.json()]
    except Exception as e:
        print(f"Error getting samar classes: {e}")
        return

    try:
        drafts_res = requests.get(os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/excel-drafts")
        drafts = drafts_res.json()
    except Exception as e:
        print(f"Error getting excel drafts: {e}")
        return

    print("Fetching drafts successful.")
    for sheet in drafts:
        print(f"Checking {sheet['sheet_name']}")
        is_class_sheet = False
        class_col_field = None
        for col in sheet.get("columns_def", []):
            if (
                "klasa" in col["headerName"].lower()
                or "klasa" in sheet["sheet_name"].lower()
                or col["field"] == "Col_1"
                or col["field"] == "col_1"
            ):
                is_class_sheet = True
                class_col_field = col["field"]
                break

        if is_class_sheet and class_col_field:
            print(
                f"Processing sheet: {sheet['sheet_name']} using col {class_col_field}"
            )

            old_rows = sheet.get("data_rows", [])

            mapped_values = {}
            for row in old_rows:
                old_val = row.get(class_col_field)
                if old_val and isinstance(old_val, str):
                    new_val = map_old_class_to_new(old_val, samar_classes)
                    if new_val:
                        new_row = dict(row)
                        new_row[class_col_field] = new_val
                        # Keep it if not seen before, or update
                        if new_val not in mapped_values:
                            mapped_values[new_val] = new_row

            print(f"  Mapped {len(mapped_values)} rows")
            new_rows = []
            id_counter = 1
            for sc in samar_classes:
                if sc in mapped_values:
                    row_to_add = mapped_values[sc]
                    row_to_add["id"] = id_counter
                    new_rows.append(row_to_add)
                else:
                    empty_row = {"id": id_counter}
                    for col in sheet.get("columns_def", []):
                        if col["field"] == class_col_field:
                            empty_row[col["field"]] = sc
                        else:
                            empty_row[col["field"]] = ""
                    new_rows.append(empty_row)
                id_counter += 1

            payload = {"columns_def": sheet["columns_def"], "data_rows": new_rows}
            try:
                put_res = requests.put(
                    os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/excel-drafts/{sheet['sheet_name']}",
                    json=payload,
                )
                if put_res.status_code == 200:
                    print(f"  -> Successfully updated sheet {sheet['sheet_name']}")
                else:
                    print(
                        f"  -> Errors updating sheet {sheet['sheet_name']}: {put_res.text}"
                    )
            except Exception as e:
                print(f"  -> Exception updating sheet {sheet['sheet_name']}: {e}")


if __name__ == "__main__":
    main()
