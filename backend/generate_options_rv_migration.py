"""
Monolit 2: Utrata Wartości Opcji Fabrycznych
Parse TAB. DOPOSAŻENIA -> map to 28 SAMAR classes + engines -> generate SQL migration
"""

import json
import datetime
from core.database import supabase


# ── Acronym-to-SAMAR-class mapping (same as Monolith 1) ──
ACRONYM_TO_SAMAR_NAME = {
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
    "M": "Minibusy - I MINIBUSY",
    "Mvan": "Kombivany - H KOMBI-VANY",
    "R": "Kempingowe - K KEMPINGOWE",
    "P": "Dostawcza - 1 OSOB.-DOST. (LAV)",
    "T PICK-UP": "Dostawcza - 2 PICK-UP",
}

# ── Fuel suffix -> engine name pattern matching ──
FUEL_SUFFIXES = ["PHEV", "HEV", "EV", "ON", "Pb"]


def extract_class_fuel(acronym: str) -> tuple[str | None, str | None]:
    """Extract class letter and fuel suffix from acronym like 'BsuvPb' or 'T PICK-UPHEV'."""
    for suffix in FUEL_SUFFIXES:
        if acronym.endswith(suffix):
            class_part = acronym[: -len(suffix)]
            return class_part, suffix
    return None, None


def main():
    # 1. Load DB lookups
    classes_resp = (
        supabase.table("samar_classes").select("id, name").order("id").execute()
    )
    engines_resp = supabase.table("engines").select("id, name").order("id").execute()

    name_to_class_id = {c["name"]: c["id"] for c in classes_resp.data}
    engine_id_map: dict[str, int] = {}
    for e in engines_resp.data:
        name_lower = e["name"].lower()
        if "benzyna" in name_lower or "pb" in name_lower:
            engine_id_map["Pb"] = e["id"]
        elif "diesel" in name_lower or "on" in name_lower:
            engine_id_map["ON"] = e["id"]
        elif "phev" in name_lower:
            engine_id_map["PHEV"] = e["id"]
        elif "hev" in name_lower and "phev" not in name_lower:
            engine_id_map["HEV"] = e["id"]
        elif (
            "ev" in name_lower and "hev" not in name_lower and "phev" not in name_lower
        ):
            engine_id_map["EV"] = e["id"]

    print("Engine ID map:", engine_id_map)
    print(f"SAMAR classes loaded: {len(name_to_class_id)}")

    # 2. Load extracted options data
    with open("tmp_options_rv.json", "r", encoding="utf-8") as f:
        options_data = json.load(f)

    # Filter out header rows
    options_data = [row for row in options_data if row["KLASY"] != "KLASY"]
    print(f"Data rows (excl headers): {len(options_data)}")

    # 3. Map and generate SQL values
    sql_values = []
    unmapped = []

    for row in options_data:
        acronym = row["KLASY"]
        class_part, fuel_suffix = extract_class_fuel(acronym)

        if not class_part or not fuel_suffix:
            unmapped.append(f"{acronym} (parse fail)")
            continue

        samar_name = ACRONYM_TO_SAMAR_NAME.get(class_part)
        if not samar_name:
            unmapped.append(f"{acronym} (class_part={class_part} not in map)")
            continue

        samar_id = name_to_class_id.get(samar_name)
        engine_id = engine_id_map.get(fuel_suffix)

        if not samar_id:
            unmapped.append(f"{acronym} (samar_name={samar_name} not in DB)")
            continue
        if not engine_id:
            unmapped.append(f"{acronym} (fuel={fuel_suffix} not in engine_id_map)")
            continue

        for year in range(8):
            val = row.get(str(year), 0)
            if val is None:
                val = 0
            sql_values.append(f"({samar_id}, {engine_id}, {year}, {val})")

    print(f"\nGenerated {len(sql_values)} SQL value tuples")
    if unmapped:
        print(f"UNMAPPED ({len(unmapped)}): {unmapped}")

    # 4. Generate SQL migration
    sql = """-- Monolit 2: Utrata Wartości Opcji Fabrycznych (lata 0-7)
-- Klucz: samar_class_id + engine_type_id + year
-- Wartość: options_rv_percent (ułamek dziesiętny, np. 0.44 = 44%)

CREATE TABLE IF NOT EXISTS samar_class_options_rv (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES samar_classes(id) ON DELETE CASCADE,
    engine_type_id INTEGER NOT NULL REFERENCES engines(id) ON DELETE CASCADE,
    year INTEGER NOT NULL CHECK (year >= 0 AND year <= 7),
    options_rv_percent NUMERIC(6,4) NOT NULL DEFAULT 0,
    UNIQUE(samar_class_id, engine_type_id, year)
);

INSERT INTO samar_class_options_rv (samar_class_id, engine_type_id, year, options_rv_percent)
VALUES
"""
    sql += ",\n".join(sql_values)
    sql += "\nON CONFLICT (samar_class_id, engine_type_id, year) DO UPDATE SET options_rv_percent = EXCLUDED.options_rv_percent;\n"

    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    migration_path = f"../supabase/migrations/{ts}_create_options_rv_table.sql"
    with open(migration_path, "w", encoding="utf-8") as f:
        f.write(sql)

    print(f"\nMigration written to: {migration_path}")


if __name__ == "__main__":
    main()
