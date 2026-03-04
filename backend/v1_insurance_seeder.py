import csv
import os
from supabase import create_client, Client


def main():
    url = os.environ.get("VITE_SUPABASE_URL", "http://127.0.0.1:54321")
    key = os.environ.get(
        "VITE_SUPABASE_SERVICE_ROLE_KEY", "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
    )

    # Optional override if run via poetry from backend
    from dotenv import load_dotenv

    load_dotenv()

    supabase: Client = create_client(url, key)

    downloads_dir = r"C:\Users\proma\Downloads"

    # 1. Load klasy.csv mapping (Id -> FULL NAME)
    print("Loading class mappings...")
    class_map = {}
    with open(os.path.join(downloads_dir, "klasy.csv"), encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if row and len(row) > 1:
                class_map[row[0].strip()] = row[1].strip()

    # 2. Seed v1_admin_parametry (35.csv)
    print("Seeding v1_admin_parametry...")
    parametry_data = []
    with open(os.path.join(downloads_dir, "35.csv"), encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if row and len(row) >= 3:
                nazwa = row[1].strip()
                wartosc_str = row[2].strip().replace(",", ".")
                if not nazwa or nazwa == "NULL":
                    continue
                try:
                    wartosc = float(wartosc_str)
                except ValueError:
                    wartosc = 0.0
                parametry_data.append({"nazwa": nazwa, "wartosc": wartosc})

    if parametry_data:
        # Check and insert safely
        try:
            supabase.table("v1_admin_parametry").delete().neq(
                "nazwa", "NON_EXISTING"
            ).execute()
            for start in range(0, len(parametry_data), 100):
                supabase.table("v1_admin_parametry").insert(
                    parametry_data[start : start + 100]
                ).execute()
            print(f"Inserted {len(parametry_data)} parameters.")
        except Exception as e:
            print(f"Failed parametry: {e}")

    # 3. Seed ubezpieczenie_wspolczynniki_szkodowe (36.csv)
    print("Seeding ubezpieczenie_wspolczynniki_szkodowe...")
    wsp_data = []
    seen_classes_wsp = set()
    with open(os.path.join(downloads_dir, "36.csv"), encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if row and len(row) >= 11:
                wsp_wartosc_str = row[1].strip().replace(",", ".")
                klasa_id = row[10].strip()
                if klasa_id in class_map:
                    klasa_nazwa = class_map[klasa_id]
                    if klasa_nazwa not in seen_classes_wsp:
                        try:
                            wsp_data.append(
                                {
                                    "klasa_samar": klasa_nazwa,
                                    "wspolczynnik_szkodowy": float(wsp_wartosc_str),
                                }
                            )
                            seen_classes_wsp.add(klasa_nazwa)
                        except ValueError:
                            pass

    if wsp_data:
        try:
            supabase.table("ubezpieczenie_wspolczynniki_szkodowe").delete().neq(
                "klasa_samar", "NON_EXISTING"
            ).execute()
            for start in range(0, len(wsp_data), 100):
                supabase.table("ubezpieczenie_wspolczynniki_szkodowe").insert(
                    wsp_data[start : start + 100]
                ).execute()
            print(f"Inserted {len(wsp_data)} szkodowe rows.")
        except Exception as e:
            print(f"Failed szkodowe: {e}")

    # 4. Seed v1_admin_ubezpieczenie (34.csv)
    print("Seeding v1_admin_ubezpieczenie...")
    ubez_data = []
    with open(os.path.join(downloads_dir, "34.csv"), encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if row and len(row) >= 8:
                try:
                    kolejny_rok = int(row[1].strip())
                    stawka_bazowa_ac = float(row[2].strip().replace(",", "."))
                    skladka_oc_wartosc = float(row[3].strip().replace(",", "."))
                    klasa_id = row[7].strip()

                    # If it matches a SAMAR class, great! Otherwise stringify the ID as fallback.
                    klasa_nazwa = class_map.get(klasa_id, f"GLOBAL_ID_{klasa_id}")

                    ubez_data.append(
                        {
                            "kolejny_rok": kolejny_rok,
                            "stawka_bazowa_ac": stawka_bazowa_ac,
                            "skladka_oc_wartosc": skladka_oc_wartosc,
                            "klasa_samar": klasa_nazwa,
                        }
                    )
                except ValueError:
                    pass

    if ubez_data:
        try:
            supabase.table("v1_admin_ubezpieczenie").delete().neq(
                "klasa_samar", "NON_EXISTING"
            ).execute()
            for start in range(0, len(ubez_data), 100):
                supabase.table("v1_admin_ubezpieczenie").insert(
                    ubez_data[start : start + 100]
                ).execute()
            print(f"Inserted {len(ubez_data)} ubezpieczenie rows.")
        except Exception as e:
            print(f"Failed ubez_data: {e}")

    print("Success! Data has been seeded.")


if __name__ == "__main__":
    main()
