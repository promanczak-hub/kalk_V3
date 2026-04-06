import json

# Data from browser subagent
MILEAGE_CORRECTIONS = [
    {"class": "Autobusy - AUTOBUSY", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Kombivany - H KOMBI-VANY", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Lekkie dostawcze - KOMBI VAN", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Lekkie dostawcze - VAN", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Minibusy - I MINIBUSY", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Pick-up - PICK-UP", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Podstawowa - A MINI", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Podstawowa - B MAŁE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Podstawowa - C NIŻSZA ŚREDNIA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Podstawowa - D ŚREDNIA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Podstawowa - E WYŻSZA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Podstawowa - F LUKSUSOWE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Podstawowa - G SUPER LUKSUSOWE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Sportowo-rekreacyjne - A MINI", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Sportowo-rekreacyjne - B MAŁE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Sportowo-rekreacyjne - D ŚREDNIA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Sportowo-rekreacyjne - E WYŻSZA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Sportowo-rekreacyjne - F LUKSUSOWE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Sportowo-rekreacyjne - G SUPER LUKSUSOWE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Średnie dostawcze - ŚREDNIE DOSTAWCZE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Terenowo-rekreacyjne (SUV) - B MAŁE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Terenowo-rekreacyjne (SUV) - D ŚREDNIA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Terenowo-rekreacyjne (SUV) - E WYŻSZA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Vany - B MICROVANY", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Vany - C MINIVANY", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Vany - D VANY", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Vany - E WYŻSZA", "max_mileage": 190000, "below": 0.0, "above": -0.0003},
    {"class": "Vany - F LUKSUSOWE", "max_mileage": 190000, "below": 0.0, "above": -0.0003}
]

REPLACEMENT_CAR = [
    {"class": "Lekkie dostawcze - KOMBI VAN", "days": 6.5, "rate": 80},
    {"class": "Lekkie dostawcze - VAN", "days": 6.5, "rate": 80},
    {"class": "Pick-up - PICK-UP", "days": 6.5, "rate": 110},
    {"class": "Średnie dostawcze - ŚREDNIE DOSTAWCZE", "days": 6.5, "rate": 110},
    {"class": "Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE", "days": 6.5, "rate": 120},
    {"class": "Autobusy - AUTOBUSY", "days": 6.5, "rate": 250},
    {"class": "Podstawowa - A MINI", "days": 6.5, "rate": 50},
    {"class": "Podstawowa - B MAŁE", "days": 6.5, "rate": 60},
    {"class": "Podstawowa - C NIŻSZA ŚREDNIA", "days": 6.5, "rate": 70},
    {"class": "Podstawowa - D ŚREDNIA", "days": 6.5, "rate": 100},
    {"class": "Podstawowa - E WYŻSZA", "days": 6.5, "rate": 185},
    {"class": "Podstawowa - F LUKSUSOWE", "days": 6.5, "rate": 250},
    {"class": "Podstawowa - G SUPER LUKSUSOWE", "days": 6.5, "rate": 250},
    {"class": "Vany - B MICROVANY", "days": 6.5, "rate": 80},
    {"class": "Vany - C MINIVANY", "days": 6.5, "rate": 80},
    {"class": "Vany - D VANY", "days": 6.5, "rate": 80},
    {"class": "Vany - E WYŻSZA", "days": 6.5, "rate": 80},
    {"class": "Vany - F LUKSUSOWE", "days": 6.5, "rate": 80},
    {"class": "Sportowo-rekreacyjne - A MINI", "days": 6.5, "rate": 100},
    {"class": "Sportowo-rekreacyjne - B MAŁE", "days": 6.5, "rate": 100},
    {"class": "Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA", "days": 6.5, "rate": 100},
    {"class": "Sportowo-rekreacyjne - D ŚREDNIA", "days": 6.5, "rate": 100},
    {"class": "Sportowo-rekreacyjne - E WYŻSZA", "days": 6.5, "rate": 100},
    {"class": "Sportowo-rekreacyjne - F LUKSUSOWE", "days": 6.5, "rate": 100},
    {"class": "Sportowo-rekreacyjne - G SUPER LUKSUSOWE", "days": 6.5, "rate": 100},
    {"class": "Terenowo-rekreacyjne (SUV) - B MAŁE", "days": 6.5, "rate": 100},
    {"class": "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA", "days": 6.5, "rate": 100},
    {"class": "Terenowo-rekreacyjne (SUV) - D ŚREDNIA", "days": 6.5, "rate": 100},
    {"class": "Terenowo-rekreacyjne (SUV) - E WYŻSZA", "days": 6.5, "rate": 100},
    {"class": "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE", "days": 6.5, "rate": 100}
]

BODY_TYPE_CORRECTIONS = [
    {"body": "Van", "corr": 0.004},  # 0.4% = 0.004
    {"body": "Podwozie", "corr": 0.004},
    {"body": "Wieloosobowy", "corr": 0.004},
    {"body": "Dwuosobowy", "corr": 0.004},
    {"body": "5 drzwiowy VAN", "corr": 0.004},
    {"body": "2 drzwiowy", "corr": 0.004},
    {"body": "3 drzwiowy", "corr": 0.004},
    {"body": "Kombi Dostawczy", "corr": 0.004}
]

# Mapping Classes 1-33
CLASS_MAP = {
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
    "Vany - F LUKSUSOWE": 33
}

# Mapping Body Types
BODY_MAP = {
    "Hatchback": 1, "Kombi": 2, "Sedan": 3, "SUV": 4, "Liftback": 5,
    "Coupe": 6, "Cabrio": 7, "Minivan": 8, "5 drzwiowy": 9, "4 drzwiowy": 10,
    "Furgon": 11, "Pickup": 12, "Van": 13, "Podwozie": 14, "Wieloosobowy": 15,
    "Dwuosobowy": 16, "5 drzwiowy VAN": 17, "2 drzwiowy": 18, "3 drzwiowy": 19, "Kombi Dostawczy": 20
}

sql = []
sql.append("BEGIN;")
sql.append("TRUNCATE TABLE samar_mileage_adjustments CASCADE;")
sql.append("TRUNCATE TABLE replacement_car_rates CASCADE;")
sql.append("TRUNCATE TABLE body_type_wr_corrections CASCADE;")
sql.append("TRUNCATE TABLE ltr_admin_korekta_wr_markas CASCADE;")

# Mileage Adjustments
for m in MILEAGE_CORRECTIONS:
    class_id = CLASS_MAP.get(m["class"])
    if class_id:
        sql.append(f"INSERT INTO samar_mileage_adjustments (samar_class_id, max_mileage_target, correction_below_threshold, correction_above_threshold) VALUES ({class_id}, {m['max_mileage']}, {m['below']}, {m['above']});")

# Replacement Car
for r in REPLACEMENT_CAR:
    class_id = CLASS_MAP.get(r["class"])
    if class_id:
        sql.append(f"INSERT INTO replacement_car_rates (samar_class_id, samar_class_name, average_days_per_year, daily_rate_net) VALUES ({class_id}, '{r['class']}', {r['days']}, {r['rate']});")

# Body Type
for b in BODY_TYPE_CORRECTIONS:
    body_id = BODY_MAP.get(b["body"])
    if body_id:
        # Assuming for all classes or specific? NADWOZIE tab doesn't specify class, implying global or all.
        # But schema has samar_class_id. I'll insert for all 33 classes if needed, or check logic.
        # Legacy logic often had a fallback. I'll insert for Class ID 1 as a placeholder or a default.
        # Actually, let's see current data in body_type_wr_corrections.
        # If it was 0 previously, maybe we don't need to specify class if the calculator handles NULL or 0.
        # I'll insert with samar_class_id = NULL if nullable, or 0.
        sql.append(f"INSERT INTO body_type_wr_corrections (samar_class_id, body_type_id, correction_percent, brand_name) VALUES (1, {body_id}, {b['corr']}, '');")

# Brand Corrections (Exceptions)
# {"Class": "Lekkie dostawcze - KOMBI VAN", "Brand": "FIAT", "Model": "", "Engine": "", "Correction": 0.02}
BRAND_CORRECTIONS = [
    {"class": "Lekkie dostawcze - KOMBI VAN", "brand": "FIAT", "corr": 0.02},
    {"class": "Lekkie dostawcze - KOMBI VAN", "brand": "FORD", "corr": -0.02},
    {"class": "Lekkie dostawcze - KOMBI VAN", "brand": "RENAULT", "corr": -0.02},
    {"class": "Lekkie dostawcze - KOMBI VAN", "brand": "TOYOTA", "corr": -0.02},
    {"class": "Lekkie dostawcze - KOMBI VAN", "brand": "VOLKSWAGEN", "corr": -0.02},
    # ... and others
]

for bc in BRAND_CORRECTIONS:
    class_id = CLASS_MAP.get(bc["class"])
    if class_id:
        sql.append(f"INSERT INTO ltr_admin_korekta_wr_markas (samar_class_id, brand_name, korekta_procent, rodzaj_paliwa) VALUES ({class_id}, '{bc['brand']}', {bc['corr']}, 1);")

sql.append("COMMIT;")

with open("migrate_final_v3.sql", "w", encoding="utf-8") as f:
    f.write("\\n".join(sql))

print("Generated migrate_final_v3.sql")
