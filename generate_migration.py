import json


def to_snake_case(name):
    s1 = "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")
    # Custom mappings
    mappings = {
        "klasa_w_rs": "samar_klasa_wr",
        "l_t_r_admin_tabela_w_r_klasas": "ltr_admin_tabela_wr_klasas",
        "l_t_r_admin_korekta_w_r_markas": "ltr_admin_korekta_wr_markas",
        "l_t_r_admin_tabela_w_r_deprecjacjas": "ltr_admin_tabela_wr_deprecjacjas",
        "l_t_r_admin_tabela_w_r_doposazenies": "ltr_admin_tabela_wr_doposazenies",
        "l_t_r_admin_tabela_w_r_przebiegs": "ltr_admin_tabela_wr_przebiegs",
        "l_t_r_admin_korekta_w_r_roczniks": "ltr_admin_korekta_wr_roczniks",
        "l_t_r_admin_korekta_w_r_kolors": "ltr_admin_korekta_wr_kolors",
        "l_t_r_admin_korekta_w_r_zabudowas": "ltr_admin_korekta_wr_zabudowas",
        "klasa_w_r_id": "klasa_wr_id",
        "korekta_procent_ponizej190": "korekta_procent_ponizej_190",
        "korekta_procent_powyzej190": "korekta_procent_powyzej_190",
    }
    return mappings.get(s1, s1)


def format_val(val, col):
    if val is None:
        return "NULL"

    # Try float parsing for numerics
    if "Procent" in col or col in [
        "Id",
        "RodzajPaliwa",
        "KlasaWRId",
        "MarkaId",
        "Rok",
        "LiczbaLat",
    ]:
        if "." in val or val.isdigit() or val.lstrip("-").isdigit():
            return val

    # Text
    # Fix Polish encoding from SQLCMD
    val_fixed = (
        val.encode("cp1252", errors="ignore").decode("cp1250", errors="ignore")
        if "\u00e2" in val
        else val
    )
    return f"'{val_fixed}'"


def main():
    with open("samar_rv_data.json", "r", encoding="utf-8") as f:
        db = json.load(f)

    sql = """-- RV SAMAR MIGRATION
-- Table creation and initial seeding

"""

    # 1. CREATE TABLES
    tables_to_create = [
        (
            "KlasaWRs",
            """
CREATE TABLE samar_klasa_wr (
    id BIGINT PRIMARY KEY,
    nazwa TEXT NOT NULL
);""",
        ),
        (
            "LTRAdminKorektaWRRoczniks",
            """
CREATE TABLE ltr_admin_korekta_wr_roczniks (
    id BIGINT PRIMARY KEY,
    rocznik TEXT NOT NULL,
    korekta_procent NUMERIC(10,4) NOT NULL
);""",
        ),
        (
            "LTRAdminKorektaWRKolors",
            """
CREATE TABLE ltr_admin_korekta_wr_kolors (
    id BIGINT PRIMARY KEY,
    kolor TEXT NOT NULL,
    korekta_procent NUMERIC(10,4) NOT NULL
);""",
        ),
        (
            "LTRAdminKorektaWRZabudowas",
            """
CREATE TABLE ltr_admin_korekta_wr_zabudowas (
    id BIGINT PRIMARY KEY,
    rodzaj_zabudowy TEXT NOT NULL,
    korekta_procent NUMERIC(10,4) NOT NULL
);""",
        ),
        (
            "LTRAdminTabelaWRKlasas",
            """
CREATE TABLE ltr_admin_tabela_wr_klasas (
    id BIGINT PRIMARY KEY,
    rodzaj_paliwa INT NOT NULL,
    klasa_wr_id BIGINT REFERENCES samar_klasa_wr(id),
    korekta_procent NUMERIC(10,4) NOT NULL
);""",
        ),
        (
            "LTRAdminKorektaWRMarkas",
            """
CREATE TABLE ltr_admin_korekta_wr_markas (
    id BIGINT PRIMARY KEY,
    rodzaj_paliwa INT NOT NULL,
    klasa_wr_id BIGINT REFERENCES samar_klasa_wr(id),
    marka_id BIGINT,
    korekta_procent NUMERIC(10,4) NOT NULL
);""",
        ),
        (
            "LTRAdminTabelaWRDeprecjacjas",
            """
CREATE TABLE ltr_admin_tabela_wr_deprecjacjas (
    id BIGINT PRIMARY KEY,
    rodzaj_paliwa INT NOT NULL,
    klasa_wr_id BIGINT REFERENCES samar_klasa_wr(id),
    rok INT NOT NULL,
    korekta_procent NUMERIC(10,4) NOT NULL
);""",
        ),
        (
            "LTRAdminTabelaWRDoposazenies",
            """
CREATE TABLE ltr_admin_tabela_wr_doposazenies (
    id BIGINT PRIMARY KEY,
    liczba_lat INT NOT NULL,
    rodzaj_paliwa INT NOT NULL,
    klasa_wr_id BIGINT REFERENCES samar_klasa_wr(id),
    korekta_procent NUMERIC(10,4) NOT NULL
);""",
        ),
        (
            "LTRAdminTabelaWRPrzebiegs",
            """
CREATE TABLE ltr_admin_tabela_wr_przebiegs (
    id BIGINT PRIMARY KEY,
    klasa_wr_id BIGINT REFERENCES samar_klasa_wr(id),
    korekta_procent_ponizej_190 NUMERIC(10,4) NOT NULL,
    korekta_procent_powyzej_190 NUMERIC(10,4) NOT NULL
);""",
        ),
    ]

    for tname, ddl in tables_to_create:
        sql += ddl + "\n\n"

    # 2. INSERT DATA
    for tname, _ in tables_to_create:
        rows = db.get(tname, [])
        if not rows:
            continue

        snake_tname = to_snake_case(tname)

        # filter columns to only the ones we created in DDL
        # avoiding DaneHistorii_*
        valid_cols = [c for c in rows[0].keys() if not c.startswith("DaneHistorii_")]
        cols_snake = [to_snake_case(c) for c in valid_cols]

        sql += f"-- SEEDING {snake_tname}\n"

        batch_size = 100
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            sql += f"INSERT INTO {snake_tname} ({', '.join(cols_snake)}) VALUES\n"

            values_lines = []
            for row in batch:
                vals = [format_val(row[c], c) for c in valid_cols]
                values_lines.append(f"({', '.join(vals)})")

            sql += ",\n".join(values_lines) + ";\n\n"

    # Enable RLS on all
    sql += "-- Setup RLS\n"
    for tname, _ in tables_to_create:
        snake_tname = to_snake_case(tname)
        sql += f"ALTER TABLE {snake_tname} ENABLE ROW LEVEL SECURITY;\n"
        sql += f'CREATE POLICY "Enable ALL for authenticated users on {snake_tname}" ON {snake_tname} FOR ALL TO authenticated USING (true) WITH CHECK (true);\n'
        sql += f'CREATE POLICY "Enable READ for anon users on {snake_tname}" ON {snake_tname} FOR SELECT TO anon USING (true);\n\n'

    with open(
        "supabase/migrations/20260224190000_add_samar_rv_tables.sql",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(sql)

    print(
        "Migration created at supabase/migrations/20260224190000_add_samar_rv_tables.sql"
    )


if __name__ == "__main__":
    main()
