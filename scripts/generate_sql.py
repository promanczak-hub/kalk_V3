import json

with open("import_data.json", "r", encoding="utf-8") as f:
    import_data = json.load(f)

# The keys in the Excel are like APb, AHEV, DsuvON, etc.
# We map DB samar_class_id to the base string:

class_mapping = {
    100: "A",
    112: "Asport",
    101: "B",
    113: "Bsport",
    107: "Bvan",
    119: "Bsuv",
    102: "C",
    114: "Csport",
    108: "Cvan",
    120: "Csuv",
    103: "D",
    115: "Dsport",
    109: "Dvan",
    121: "Dsuv",
    104: "E",
    122: "Esuv",
    105: "F",
    117: "Fsport",
    123: "Fsuv",
    1: "M",
    2: "Mvan",
    4: "R",
    5: "P",
    3: "T PICK-UP",
}

# Mapping fuel_type_id to the suffix in Excel
# 1: PB, 2: ON, 3: PB-mHEV, 4: ON-mHEV, 5: HEV, 6: PHEV, 7: BEV, 8: FCEV, 9: LPG
fuel_mapping = {
    1: "Pb",
    3: "Pb",
    9: "Pb",
    2: "ON",
    4: "ON",
    5: "HEV",
    6: "PHEV",
    7: "EV",
    8: "EV",
}

updates = []

for class_id, class_prefix in class_mapping.items():
    for fuel_id, fuel_suffix in fuel_mapping.items():
        key = f"{class_prefix}{fuel_suffix}"
        if key in import_data:
            val = import_data[key]
            updates.append((class_id, fuel_id, val))

print(f"-- Generated {len(updates)} updates")
sql_statements = []

for class_id, fuel_id, val in updates:
    sql = f"UPDATE samar_class_depreciation_rates SET base_depreciation_percent = {val} WHERE year = 0 AND samar_class_id = {class_id} AND fuel_type_id = {fuel_id};"
    sql_statements.append(sql)

with open("update_rates.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(sql_statements))

print("Wrote update_rates.sql")
