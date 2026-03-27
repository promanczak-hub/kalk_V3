import pandas as pd

CSV_FILES = {
    "rv_matrix": "rv_matrix.csv",
    "options_rv": "options_rv.csv",
    "ubezp": "ubezp.csv",
    "serwis": "serwis_baza.csv",
    "zast": "zast.csv",
    "przebieg": "przebieg.csv",
    "marka_kor": "marka_kor.csv",
}

ENGINE_MAPPING = {
    "Benzyna (PB)": 1,
    "Diesel (ON)": 2,
    "Benzyna mHEV (PB-mHEV)": 3,
    "Diesel mHEV (ON-mHEV)": 4,
    "Hybryda (HEV)": 5,
    "Plug-in Hybrid (PHEV)": 6,
    "Elektryczny (BEV)": 7,
    "Wodór (FCEV)": 8,
    "LPG": 9,
}


def clean_num(val):
    if pd.isna(val) or val == "":
        return 0.0
    if isinstance(val, str):
        val = val.replace(",", ".").replace("%", "").strip()
    try:
        return float(val)
    except:
        return 0.0


def generate_sql():
    df_rv = pd.read_csv(CSV_FILES["rv_matrix"], encoding="utf-8")
    class_names = df_rv["Klasa_SAMAR"].tolist()
    class_map = {name: i + 1 for i, name in enumerate(class_names)}

    sql = []

    # 1. samar_classes
    print("Generating samar_classes SQL...")
    for i, name in enumerate(class_names):
        sql.append(
            f"INSERT INTO public.samar_classes (id, name, mileage_threshold_km, base_mileage_km, base_period_months) VALUES ({i + 1}, '{name}', 190000, 140000, 48) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name;"
        )

    # 2. samar_class_base_rv
    print("Generating base_rv SQL...")
    for index, row in df_rv.iterrows():
        c_id = class_map[row["Klasa_SAMAR"]]
        for eng_name, eng_id in ENGINE_MAPPING.items():
            if eng_name in row:
                val = clean_num(row[eng_name])
                sql.append(
                    f"INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent) VALUES ({c_id}, {eng_id}, {val}) ON CONFLICT (samar_class_id, engine_type_id) DO UPDATE SET base_rv_percent=EXCLUDED.base_rv_percent;"
                )

    # 3. samar_class_options_rv
    print("Generating options_rv SQL...")
    df_opt = pd.read_csv(CSV_FILES["options_rv"], header=None, skiprows=2)
    for _, row in df_opt.iterrows():
        c_name = row[0]
        e_name = row[1]
        if c_name not in class_map or e_name not in ENGINE_MAPPING:
            continue
        c_id = class_map[c_name]
        e_id = ENGINE_MAPPING[e_name]
        for year in range(8):
            val = clean_num(row[year + 2])
            sql.append(
                f"INSERT INTO public.samar_class_options_rv (samar_class_id, engine_type_id, year, options_rv_percent) VALUES ({c_id}, {e_id}, {year}, {val}) ON CONFLICT (samar_class_id, engine_type_id, year) DO UPDATE SET options_rv_percent=EXCLUDED.options_rv_percent;"
            )

    # 4. ltr_admin_ubezpieczenia
    print("Generating insurance SQL...")
    df_ins = pd.read_csv(CSV_FILES["ubezp"], header=None, skiprows=1)
    for _, row in df_ins.iterrows():
        c_name = row[0]
        if c_name not in class_map:
            continue
        c_id = class_map[c_name]
        year = int(row[1])
        ac = clean_num(row[2])
        oc = clean_num(row[3])
        sql.append(
            f'INSERT INTO public.ltr_admin_ubezpieczenia (samar_class_id, "KolejnyRok", "StawkaBazowaAC", "SkladkaOC") VALUES ({c_id}, {year}, {ac}, {oc}) ON CONFLICT (samar_class_id, "KolejnyRok") DO UPDATE SET "StawkaBazowaAC"=EXCLUDED."StawkaBazowaAC", "SkladkaOC"=EXCLUDED."SkladkaOC";'
        )

    # 5. samar_service_costs
    print("Generating service costs SQL...")
    df_svc = pd.read_csv(CSV_FILES["serwis"], header=None, skiprows=1)
    for _, row in df_svc.iterrows():
        c_name = row[0]
        e_name = row[1]
        if c_name not in class_map or e_name not in ENGINE_MAPPING:
            continue
        c_id = class_map[c_name]
        e_id = ENGINE_MAPPING[e_name]
        pb = row[2]
        aso = clean_num(row[3])
        naso = clean_num(row[4])
        sql.append(
            f"INSERT INTO public.samar_service_costs (samar_class_id, engine_type_id, power_band, cost_aso_per_km, cost_non_aso_per_km) VALUES ({c_id}, {e_id}, '{pb}', {aso}, {naso}) ON CONFLICT (samar_class_id, engine_type_id, power_band) DO UPDATE SET cost_aso_per_km=EXCLUDED.cost_aso_per_km, cost_non_aso_per_km=EXCLUDED.cost_non_aso_per_km;"
        )

    # 6. replacement_car_rates
    print("Generating replacement rates SQL...")
    df_zast = pd.read_csv(CSV_FILES["zast"], header=None, skiprows=1)
    for _, row in df_zast.iterrows():
        c_name = row[0]
        if c_name not in class_map:
            continue
        c_id = class_map[c_name]
        days = clean_num(row[1])
        rate = clean_num(row[2])
        sql.append(
            f"INSERT INTO public.replacement_car_rates (samar_class_id, samar_class_name, average_days_per_year, daily_rate_net) VALUES ({c_id}, '{c_name}', {days}, {rate}) ON CONFLICT (samar_class_id) DO UPDATE SET average_days_per_year=EXCLUDED.average_days_per_year, daily_rate_net=EXCLUDED.daily_rate_net;"
        )

    # 10. damage coefficients
    print("Generating damage coefficients SQL...")
    for c_id in class_map.values():
        sql.append(
            f'INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (samar_class_id, "WspSredniPrzebieg", "WspWartoscSzkody") VALUES ({c_id}, 1.0, 1.0) ON CONFLICT (samar_class_id) DO NOTHING;'
        )

    with open("migration_samar_v3.sql", "w", encoding="utf-8") as f:
        f.write("\n".join(sql))


if __name__ == "__main__":
    generate_sql()
