import pandas as pd
from core.database import supabase

# --- Configuration ---
CSV_FILES = {
    "samar_classes": "samar_classes.csv",
    "rv_matrix": "rv_matrix.csv",
    "options_rv": "options_rv.csv",
    "opony": "opony.csv",
    "serwis": "serwis_baza.csv",
    "ubezp": "ubezp.csv",
    "zast": "zast.csv",
    "przebieg": "przebieg.csv",
    "marka_kor": "marka_kor.csv",
    "nadwozie_kor": "nadwozie_kor.csv",
    "rocznik_kor": "rocznik_kor.csv",
    "serwis_mnozniki": "serwis_mnozniki.csv",
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


def migrate():
    print("Starting Samar V3 Migration...")

    # 1. Load Samar Classes from rv_matrix.csv (it has the 33 names in order)
    df_rv = pd.read_csv(CSV_FILES["rv_matrix"], encoding="utf-8")
    class_names = df_rv["Klasa_SAMAR"].tolist()

    # Map names to IDs 1-33
    class_id_map = {name: i + 1 for i, name in enumerate(class_names)}

    # 2. Update samar_classes table
    print("Updating samar_classes...")
    classes_to_upsert = []
    for i, name in enumerate(class_names):
        classes_to_upsert.append(
            {
                "id": i + 1,
                "name": name,
                "mileage_threshold_km": 190000,
                "base_mileage_km": 140000,
                "base_period_months": 48,
            }
        )
    supabase.table("samar_classes").upsert(classes_to_upsert).execute()

    # 3. Migrate Base RV Matrix
    print("Migrating samar_class_base_rv...")
    rv_records = []
    for index, row in df_rv.iterrows():
        class_id = class_id_map[row["Klasa_SAMAR"]]
        for eng_name, eng_id in ENGINE_MAPPING.items():
            if eng_name in row:
                rv_records.append(
                    {
                        "samar_class_id": class_id,
                        "engine_type_id": eng_id,
                        "base_rv_percent": clean_num(row[eng_name]),
                    }
                )
    supabase.table("samar_class_base_rv").upsert(
        rv_records, on_conflict="samar_class_id, engine_type_id"
    ).execute()

    # 4. Migrate Options RV
    print("Migrating samar_class_options_rv...")
    df_opt = pd.read_csv(CSV_FILES["options_rv"], header=None, skiprows=2)
    # File structure: Class, Engine, Year0, Year1, ... Year7
    opt_records = []
    for _, row in df_opt.iterrows():
        c_name = row[0]
        e_name = row[1]
        if c_name not in class_id_map or e_name not in ENGINE_MAPPING:
            continue
        c_id = class_id_map[c_name]
        e_id = ENGINE_MAPPING[e_name]
        for year in range(8):
            val = clean_num(row[year + 2])
            opt_records.append(
                {
                    "samar_class_id": c_id,
                    "engine_type_id": e_id,
                    "year": year,
                    "options_rv_percent": val,
                }
            )
    supabase.table("samar_class_options_rv").upsert(
        opt_records, on_conflict="samar_class_id, engine_type_id, year"
    ).execute()

    # 5. Migrate Insurance
    print("Migrating ltr_admin_ubezpieczenia...")
    df_ins = pd.read_csv(CSV_FILES["ubezp"], header=None, skiprows=1)
    # File: Class, Year, AC_Rate, OC_Flat
    ins_records = []
    for _, row in df_ins.iterrows():
        c_name = row[0]
        if c_name not in class_id_map:
            continue
        c_id = class_id_map[c_name]
        year = int(row[1])
        ac = clean_num(row[2])
        oc = clean_num(row[3])
        ins_records.append(
            {
                "samar_class_id": c_id,
                "KolejnyRok": year,
                "StawkaBazowaAC": ac,
                "SkladkaOC": oc,
            }
        )
    supabase.table("ltr_admin_ubezpieczenia").upsert(
        ins_records, on_conflict="samar_class_id, KolejnyRok"
    ).execute()

    # 6. Migrate Service Costs
    print("Migrating samar_service_costs...")
    df_svc = pd.read_csv(CSV_FILES["serwis"], header=None, skiprows=1)
    # File: Class, Engine, PowerBand, ASO, Non-ASO
    svc_records = []
    for _, row in df_svc.iterrows():
        c_name = row[0]
        e_name = row[1]
        if c_name not in class_id_map or e_name not in ENGINE_MAPPING:
            continue
        svc_records.append(
            {
                "samar_class_id": class_id_map[c_name],
                "engine_type_id": ENGINE_MAPPING[e_name],
                "power_band": row[2],
                "cost_aso_per_km": clean_num(row[3]),
                "cost_non_aso_per_km": clean_num(row[4]),
            }
        )
    supabase.table("samar_service_costs").upsert(
        svc_records, on_conflict="samar_class_id, engine_type_id, power_band"
    ).execute()

    # 7. Replacement Car Rates
    print("Migrating replacement_car_rates...")
    df_zast = pd.read_csv(CSV_FILES["zast"], header=None, skiprows=1)
    zast_records = []
    for _, row in df_zast.iterrows():
        c_name = row[0]
        if c_name not in class_id_map:
            continue
        zast_records.append(
            {
                "samar_class_id": class_id_map[c_name],
                "samar_class_name": c_name,
                "average_days_per_year": clean_num(row[1]),
                "daily_rate_net": clean_num(row[2]),
            }
        )
    supabase.table("replacement_car_rates").upsert(
        zast_records, on_conflict="samar_class_id"
    ).execute()

    # 8. Mileage Adjustments
    print("Migrating samar_mileage_adjustments...")
    df_pb = pd.read_csv(CSV_FILES["przebieg"], header=None, skiprows=1)
    pb_records = []
    for _, row in df_pb.iterrows():
        c_name = row[0]
        if c_name not in class_id_map:
            continue
        pb_records.append(
            {
                "samar_class_id": class_id_map[c_name],
                "max_mileage_target": int(clean_num(row[1])),
                "correction_below_threshold": clean_num(row[2]),
                "correction_above_threshold": clean_num(row[3]),
            }
        )
    supabase.table("samar_mileage_adjustments").upsert(
        pb_records, on_conflict="samar_class_id"
    ).execute()

    # 9. Brand Corrections
    print("Migrating ltr_admin_korekta_wr_markas...")
    df_marka = pd.read_csv(CSV_FILES["marka_kor"], header=None, skiprows=1)
    marka_records = []
    for _, row in df_marka.iterrows():
        c_name = row[0]
        e_name = row[1]
        if c_name not in class_id_map or e_name not in ENGINE_MAPPING:
            continue
        marka_records.append(
            {
                "samar_class_id": class_id_map[c_name],
                "rodzaj_paliwa": ENGINE_MAPPING[e_name],
                "brand_name": str(row[2]).strip().upper(),
                "korekta_procent": clean_num(row[3]),
            }
        )
    # This might have many rows, upsert on conflict
    supabase.table("ltr_admin_korekta_wr_markas").upsert(
        marka_records, on_conflict="samar_class_id, rodzaj_paliwa, brand_name"
    ).execute()

    print("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
