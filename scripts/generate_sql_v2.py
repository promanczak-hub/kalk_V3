import json

# Hardcoded classes from DB (queried via MCP)
db_classes = {
    "Autobusy - AUTOBUSY": 1,
    "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE": 2,
    "Kombivany - H KOMBI-VANY": 3,
    "Lekkie dostawcze - KOMBI VAN": 4,
    "Lekkie dostawcze - VAN": 5,
    "Minibusy - I MINIBUSY": 6,
    "Pick-up - PICK-UP": 7,
    "Podstawowa - A MINI": 8,
    "Podstawowa - B MAŁE": 9,
    "Podstawowa - C NIŻSZA ŚREDNIA": 10,
    "Podstawowa - D ŚREDNIA": 11,
    "Podstawowa - E WYŻSZA": 12,
    "Podstawowa - F LUKSUSOWE": 13,
    "Podstawowa - G SUPER LUKSUSOWE": 14,
    "Sportowo-rekreacyjne - A MINI": 15,
    "Sportowo-rekreacyjne - B MAŁE": 16,
    "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA": 17,
    "Sportowo-rekreacyjne - D ŚREDNIA": 18,
    "Sportowo-rekreacyjne - E WYŻSZA": 19,
    "Sportowo-rekreacyjne - F LUKSUSOWE": 20,
    "Sportowo-rekreacyjne - G SUPER LUKSUSOWE": 21,
    "Średnie dostawcze - ŚREDNIE DOSTAWCZE": 22,
    "Terenowo-rekreacyjne (SUV) - B MAŁE": 23,
    "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA": 24,
    "Terenowo-rekreacyjne (SUV) - D ŚREDNIA": 25,
    "Terenowo-rekreacyjne (SUV) - E WYŻSZA": 26,
    "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE": 27,
    "Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE": 28,
    "Vany - B MICROVANY": 29,
    "Vany - C MINIVANY": 30,
    "Vany - D VANY": 31,
    "Vany - E WYŻSZA": 32,
    "Vany - F LUKSUSOWE": 33,
}

# Name -> Prefix mapping in import_data.json
name_to_prefix = {
    "Podstawowa - A MINI": "A",
    "Sportowo-rekreacyjne - A MINI": "Asport",
    "Podstawowa - B MAŁE": "B",
    "Sportowo-rekreacyjne - B MAŁE": "Bsport",
    "Vany - B MICROVANY": "Bvan",
    "Terenowo-rekreacyjne (SUV) - B MAŁE": "Bsuv",
    "Podstawowa - C NIŻSZA ŚREDNIA": "C",
    "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA": "Csport",
    "Vany - C MINIVANY": "Cvan",
    "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA": "Csuv",
    "Podstawowa - D ŚREDNIA": "D",
    "Sportowo-rekreacyjne - D ŚREDNIA": "Dsport",
    "Vany - D VANY": "Dvan",
    "Terenowo-rekreacyjne (SUV) - D ŚREDNIA": "Dsuv",
    "Podstawowa - E WYŻSZA": "E",
    "Terenowo-rekreacyjne (SUV) - E WYŻSZA": "Esuv",
    "Podstawowa - F LUKSUSOWE": "F",
    "Sportowo-rekreacyjne - F LUKSUSOWE": "Fsport",
    "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE": "Fsuv",
    "Minibusy - I MINIBUSY": "M",
    "Lekkie dostawcze - KOMBI VAN": "Mvan",
    "Pick-up - PICK-UP": "T PICK-UP",
    "Średnie dostawcze - ŚREDNIE DOSTAWCZE": "P",
    "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE": "R",
}

# Fuel Mapping
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

with open("import_data.json", "r", encoding="utf-8") as f:
    import_data = json.load(f)

sql_statements = [
    "-- Migration: Seed samar_class_depreciation_rates (Year 0)",
    "TRUNCATE TABLE samar_class_depreciation_rates;",
    "",
]

count = 0
for db_name, class_id in db_classes.items():
    prefix = name_to_prefix.get(db_name)
    if not prefix:
        continue

    for fuel_id, suffix in fuel_mapping.items():
        key = f"{prefix}{suffix}"
        if key in import_data:
            val = import_data[key]
            sql = f"INSERT INTO samar_class_depreciation_rates (samar_class_id, fuel_type_id, year, base_depreciation_percent) VALUES ({class_id}, {fuel_id}, 0, {val});"
            sql_statements.append(sql)
            count += 1

with open("update_rates_v2.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(sql_statements))

print(f"Generated {count} INSERT statements in update_rates_v2.sql")
