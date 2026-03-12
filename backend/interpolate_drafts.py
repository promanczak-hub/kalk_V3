import os
import requests
import statistics

# Mapowanie z poprzedniego kroku
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
    """
    To function is used to figure out what the old value means in terms of NEW SAMAR CLASS and ENGINE
    """
    base_class, suffix = clean_engine_type(old_val)
    if not suffix and "Pb" in old_val:
        suffix = "PB"
    if suffix == "Pb":
        suffix = "PB"
    if suffix == "EV":
        suffix = "BEV"

    # Try finding mapped base
    mapped_base = None
    if base_class in MAPPING:
        mapped_base = MAPPING[base_class]
    elif old_val in MAPPING:
        mapped_base = MAPPING[old_val]

    return mapped_base, suffix


def is_float(value):
    try:
        float(value)
        return True
    except:
        return False


def interpolate_values(
    sheet_name, old_rows, class_col_field, samar_classes, engines, columns_def
):
    print(f"\n--- Interpolating {sheet_name} ---")

    # Extract numerical data columns
    num_cols = [
        col["field"]
        for col in columns_def
        if col["field"] != class_col_field and col["field"] != "id"
    ]

    # 1. Parse old rows to understand the current knowledge base
    # Dictionary structure: knowledge[samar_class][engine_name/suffix] = {col_1: val, col_2: val}
    knowledge = {}
    for sc in samar_classes:
        knowledge[sc] = {}
        # initialize base "spalinowy" with empty or from old map

    # We might have rows from the first migration that already look like "Podstawowa - A MINI" inside old_rows
    # Let's extract values
    for row in old_rows:
        val = row.get(class_col_field)
        if not val or not isinstance(val, str):
            continue

        # Is it an old format (e.g. AsportPHEV) or already migrated (eg. Podstawowa - A MINI)?
        mapped_base, suffix = map_old_class_to_new(val, samar_classes, engines)
        if not mapped_base:
            # Maybe it's already a samar class?
            if val in samar_classes:
                mapped_base = val
                suffix = ""
            else:
                for sc in samar_classes:
                    if val.startswith(sc):
                        mapped_base = sc
                        suffix = val[len(sc) :].strip()
                        break

        if mapped_base and mapped_base in knowledge:
            norm_suffix = suffix.upper().strip()
            # If we don't know the exact engine match from the new engines list, we'll try to map it later

            extracted_vals = {}
            for col in num_cols:
                if (
                    row.get(col) != ""
                    and row.get(col) is not None
                    and is_float(row.get(col))
                ):
                    extracted_vals[col] = float(row.get(col))

            if extracted_vals:
                knowledge[mapped_base][norm_suffix] = extracted_vals

    # 2. Generate all combinations: 35 SAMAR classes * X engines
    new_rows = []
    engine_names = [e["name"] for e in engines]

    # We'll map suffix to engine category to help with fallback (e.g. "PB" -> "Benzyna (PB)")
    def match_engine_to_suffix(engine_name, suffix):
        if not suffix:
            return True  # empty suffix can be anything base
        s = suffix.upper()
        en = engine_name.upper()
        if s == "PB" and ("BENZYNA" in en or "PB" in en):
            return True
        if s == "ON" and "DIESEL" in en:
            return True
        if s == "PHEV" and "PHEV" in en:
            return True
        if s == "HEV" and "HEV" in en and "PHEV" not in en and "MHEV" not in en:
            return True
        if (s == "EV" or s == "BEV") and ("EV" in en and "HEV" not in en):
            return True
        return False

    id_counter = 1

    # Store all values globally to compute global averages later
    global_values = {col: [] for col in num_cols}
    group_values = {}  # e.g. "Podstawowa": {col: []}

    for sc in samar_classes:
        group = sc.split(" - ")[0]
        if group not in group_values:
            group_values[group] = {col: [] for col in num_cols}

        for engine in engines:
            eng_name = engine["name"]

            row_data = {"id": id_counter, class_col_field: f"{sc} {eng_name}"}
            id_counter += 1

            # Find the best matching knowledge
            best_vals = {}

            # Priority A: Exact match in knowledge base (class + mapped suffix)
            for known_suffix, vals in knowledge[sc].items():
                if match_engine_to_suffix(eng_name, known_suffix):
                    best_vals = vals
                    break

            # Priority B: If no exact engine match, use base class values (where suffix is empty or standard like PB)
            if not best_vals:
                for known_suffix, vals in knowledge[sc].items():
                    if (
                        known_suffix == ""
                        or known_suffix == "PB"
                        or known_suffix == "ON"
                    ):
                        best_vals = vals
                        break

            # Priority C: Just use any value from this class if available
            if not best_vals and knowledge[sc]:
                best_vals = list(knowledge[sc].values())[0]

            for col in num_cols:
                if col in best_vals:
                    val = best_vals[col]
                    row_data[col] = val
                    global_values[col].append(val)
                    group_values[group][col].append(val)
                else:
                    row_data[col] = None  # Mark as missing for now

            new_rows.append(row_data)

    # 3. Second pass: Fill in missing values using Group Average or Global Average
    for row in new_rows:
        class_str = row[class_col_field]
        sc = next(c for c in samar_classes if class_str.startswith(c))
        group = sc.split(" - ")[0]

        for col in num_cols:
            if row[col] is None:
                # Need to interpolate
                # Try group average
                if len(group_values[group][col]) > 0:
                    avg = statistics.mean(group_values[group][col])
                    row[col] = round(avg, 4)
                # Try global average
                elif len(global_values[col]) > 0:
                    avg = statistics.mean(global_values[col])
                    row[col] = round(avg, 4)
                else:
                    row[col] = ""  # completely empty

    return new_rows


def main():
    try:
        samar_classes_res = requests.get(
            os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/samar-classes"
        )
        samar_classes = [c["name"] for c in samar_classes_res.json()]
    except Exception as e:
        print(f"Error getting samar classes: {e}")
        return

    try:
        engines_res = requests.get(
            os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/engines"
        )
        engines = engines_res.json()
    except Exception as e:
        print(f"Error getting engines: {e}")
        return

    try:
        drafts_res = requests.get(
            os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/excel-drafts"
        )
        drafts = drafts_res.json()
    except Exception as e:
        print(f"Error getting excel drafts: {e}")
        return

    target_sheets = [
        "TAB. PRZEBIEG",
        "TAB. DOPOSAŻENIA",
        "TAB. OKRES FINAL",
        "TAB.WR KLASA",
    ]

    for sheet in drafts:
        if sheet["sheet_name"] not in target_sheets:
            continue

        class_col_field = None
        for col in sheet.get("columns_def", []):
            if (
                "klasa" in col["headerName"].lower()
                or col["field"] == "Col_1"
                or col["field"] == "col_1"
            ):
                class_col_field = col["field"]
                break

        if class_col_field:
            old_rows = sheet.get("data_rows", [])
            new_rows = interpolate_values(
                sheet["sheet_name"],
                old_rows,
                class_col_field,
                samar_classes,
                engines,
                sheet["columns_def"],
            )

            print(f"Generated {len(new_rows)} rows for {sheet['sheet_name']}")

            payload = {"columns_def": sheet["columns_def"], "data_rows": new_rows}
            try:
                put_res = requests.put(
                    os.environ.get("API_URL", "http://127.0.0.1:8000")
                    + "/api/excel-drafts/{sheet['sheet_name']}",
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
