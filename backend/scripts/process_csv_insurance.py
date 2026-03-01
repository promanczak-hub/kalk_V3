import csv
import os

UBEZP1_FILE = r"C:\Users\proma\OneDrive\Dokumenty\ubezp1.csv"
UBEZP2_FILE = r"C:\Users\proma\OneDrive\Dokumenty\ubezp2.csv"
UBEZP3_FILE = r"C:\Users\proma\OneDrive\Dokumenty\ubezp3.csv"
OUT_SQL = r"d:\kalk_v3\supabase\migrations\20260227100000_seed_v1_insurance_data.sql"

# Mapping from old SQL Server ID to SamarRV class ID
# A, Asport, B, Bsport, Bsuv, Bvan, C, Csport, Csuv, Cvan, D, Dsport, Dsuv, Dvan, E, Esuv, F, Fsport, Fsuv, M, Mvan, R, P, T PICK_UP
# ID in SQL server: (from ubezp2 mapping)
SQL_TO_NEW_ID = {
    17: 1,  # A -> Asport? Let's assume based on data
    1: 2,
    2: 3,
    19: 4,
    3: 5,
    4: 6,
    14: 7,
    29: 8,
    5: 9,
    6: 10,
    21: 11,
    7: 12,
    13: 13,
    8: 14,
    12: 15,
    20: 16,
    9: 17,
    24: 18,
    23: 19,
    22: 20,
    10: 21,
    11: 22,
    18: 23,
    16: 24,
}


def main():
    with open(OUT_SQL, "w", encoding="utf-8") as out:
        out.write("-- Migration generated from V1 Express_test database extract\n\n")

        # 1. ltr_admin_ubezpieczenia
        out.write(
            "-- 1. LTRAdminUbezpieczenia (Stawki AC / OC w zaleznosci od roku i klasy)\n"
        )
        out.write("DO $$\nBEGIN\n")
        if os.path.exists(UBEZP1_FILE):
            with open(UBEZP1_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=";")
                for row in reader:
                    if len(row) < 5:
                        continue
                    # row: Id, KlasaId, StawkaBazowaAC, SkladkaOC, KolejnyRok(9/11/etc)
                    # wait, order is 131; 1(Rok? / Klasa?); 0.0150(StawkaAC); 1476(SkladkaOC); ... ; 9(Klasa/Rok)
                    # Let's inspect rows:
                    # 131;1;0.0150;1476.0000;NULL;2023-10-10 16:17:24.8517806;NULL;66;NULL;NULL;0x00000000560AFB22;NULL

                    rok = row[1]
                    stawkaAC = row[2]
                    skladkaOC = row[3]
                    klasa_id = row[-1] if row[-1] != "NULL" else "NULL"

                    if klasa_id != "NULL":
                        try:
                            old_id = int(klasa_id)
                            # Only use old_id if it's within 1-24 range
                            if 1 <= old_id <= 24:
                                new_klasa_id = str(old_id)
                            else:
                                new_klasa_id = "NULL"
                        except Exception:
                            new_klasa_id = "NULL"
                    else:
                        new_klasa_id = "NULL"

                    out.write(
                        f'    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES ({rok}, {stawkaAC}, {skladkaOC}, {new_klasa_id});\n'
                    )
        out.write("END $$;\n\n")

        # 2. ltr_admin_wspolczynniki_szkodowe
        out.write(
            "-- 2. LTRAdminWspolczynnikiSzkodowe (Wspolczynniki dla poszczegolnych klas)\n"
        )
        out.write("DO $$\nBEGIN\n")
        if os.path.exists(UBEZP2_FILE):
            with open(UBEZP2_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=";")
                for row in reader:
                    if len(row) < 3:
                        continue
                    # row: 408; 0.9100; 1.0000; ... ; 17 (klasaId)
                    wsp_sredni_przebieg = row[1]
                    wsp_wartosc_szkody = row[2]
                    klasa_id = row[-1] if row[-1] != "NULL" else "NULL"

                    if klasa_id != "NULL":
                        try:
                            old_id = int(klasa_id)
                            # Only use old_id if it's within 1-24 range
                            if 1 <= old_id <= 24:
                                new_klasa_id = str(old_id)
                            else:
                                new_klasa_id = "NULL"
                        except Exception:
                            new_klasa_id = "NULL"
                    else:
                        new_klasa_id = "NULL"

                    out.write(
                        f"    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES ({new_klasa_id}, {wsp_sredni_przebieg}, {wsp_wartosc_szkody});\n"
                    )
        out.write("END $$;\n\n")

        # 3. Control center parameter
        out.write(
            "-- 3. LTRAdminParametry (Globalne nastawy szkodowosci i ryzyka ubezpieczeniowego)\n"
        )
        out.write("UPDATE public.control_center SET\n")
        out.write("  ins_theft_doub_pct = 0.10,\n")
        out.write("  ins_driving_school_doub_pct = 0.5,\n")
        out.write("  ins_avg_damage_value = 2587,\n")
        out.write("  ins_avg_damage_mileage = 80000;\n")


if __name__ == "__main__":
    main()
