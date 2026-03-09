"""Generate SQL script to backup, wipe, and remap SAMAR classes atomically."""

import os
from core.database import supabase

NEW_CLASSES_MD = """
| Grupa                      | Klasa | Nazwa klasy     | Przykładowe modele                                                     |
| -------------------------- | ----- | --------------- | ---------------------------------------------------------------------- |
| Podstawowa                 | A     | MINI            | Fiat 500, Hyundai i10, Kia Picanto, Toyota Aygo X, Dacia Spring        |
| Podstawowa                 | B     | MAŁE            | Volkswagen Polo, Renault Clio, Toyota Yaris, Skoda Fabia, Opel Corsa   |
| Podstawowa                 | C     | NIŻSZA ŚREDNIA  | Volkswagen Golf, Toyota Corolla, Skoda Octavia, Kia Ceed, Ford Focus   |
| Podstawowa                 | D     | ŚREDNIA         | BMW Serii 3, Audi A5, Tesla Model 3, Toyota Camry, Volkswagen Passat   |
| Podstawowa                 | E     | WYŻSZA          | BMW Serii 5, Audi A6, Mercedes Klasa E, Volvo S90, Lexus ES            |
| Podstawowa                 | F     | LUKSUSOWE       | BMW Serii 7, Audi A8, Mercedes Klasa S, Porsche Panamera, Lexus LS     |
| Podstawowa                 | G     | SUPER LUKSUSOWE | Bentley Flying Spur, Rolls-Royce Ghost, Rolls-Royce Phantom            |
| Vany                       | B     | MICROVANY       | Honda Jazz                                                             |
| Vany                       | C     | MINIVANY        | BMW 2 Active Tourer, Dacia Jogger, Mercedes Klasa B, Volkswagen Touran |
| Vany                       | D     | VANY            | Forthing U-Tour                                                        |
| Vany                       | E     | WYŻSZA          | Forthing V-Tour, Voyah Dream                                           |
| Vany                       | F     | LUKSUSOWE       | Lexus LM                                                               |
| Sportowo-rekreacyjne       | A     | MINI            | Fiat 500 Cabrio, Abarth 500 Cabrio                                     |
| Sportowo-rekreacyjne       | B     | MAŁE            | Mini Cabrio                                                            |
| Sportowo-rekreacyjne       | C     | NIŻSZA ŚREDNIA  | BMW Serii 4, Ford Mustang, Porsche 718                                 |
| Sportowo-rekreacyjne       | D     | ŚREDNIA         | Mercedes CLE                                                           |
| Sportowo-rekreacyjne       | E     | WYŻSZA          | Alpine A110, BMW Z4, Mazda MX-5                                        |
| Sportowo-rekreacyjne       | F     | LUKSUSOWE       | BMW Serii 8, Porsche 911, Mercedes SL                                  |
| Sportowo-rekreacyjne       | G     | SUPER LUKSUSOWE | Ferrari 296, Lamborghini Revuelto, Aston Martin DB12                   |
| Terenowo-rekreacyjne (SUV) | B     | MAŁE            | Ford Puma, Toyota Yaris Cross, Volkswagen T-Cross, Hyundai Kona        |
| Terenowo-rekreacyjne (SUV) | C     | NIŻSZA ŚREDNIA  | BMW X3, Audi Q5, Hyundai Santa Fe, Kia Sorento                         |
| Terenowo-rekreacyjne (SUV) | D     | ŚREDNIA         | BMW X1, Audi Q3, Hyundai Tucson, Kia Sportage                          |
| Terenowo-rekreacyjne (SUV) | E     | WYŻSZA          | BMW X7, Mercedes GLS, Lotus Eletre                                     |
| Terenowo-rekreacyjne (SUV) | F     | LUKSUSOWE       | Lamborghini Urus, Bentley Bentayga, Rolls-Royce Cullinan               |
| Terenowo-rekreacyjne (SUV) | G     | SUPER LUKSUSOWE | BMW X5, Porsche Cayenne, Mercedes GLE                                  |
| Kombivany                  | H     | KOMBI-VANY      | Citroen Berlingo, Peugeot Rifter, Volkswagen Caddy                     |
| Minibusy                   | I     | MINIBUSY        | Volkswagen Multivan, Mercedes V-Class, Hyundai Staria                  |
| Kempingowe                 | K     | KEMPINGOWE      | Volkswagen California, Mercedes Marco Polo                             |
"""


def parse_new_classes():
    lines = [line.strip() for line in NEW_CLASSES_MD.splitlines() if "|" in line]
    lines = lines[2:]  # skip headers
    classes = []
    for idx, line in enumerate(lines):
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) >= 4:
            classes.append(
                {
                    "id": idx + 100,  # New clean ID sequence
                    "group_name": parts[0],
                    "size_class": parts[1],
                    "name": f"{parts[1]} {parts[2]}",  # e.g. "B MAŁE"
                    "category": parts[0],
                    "example_models": parts[3],
                }
            )
    return classes


def get_current_data():
    classes = supabase.table("samar_classes").select("*").execute().data
    insurance = supabase.table("ltr_admin_ubezpieczenia").select("*").execute().data
    damage = (
        supabase.table("ltr_admin_wspolczynniki_szkodowe").select("*").execute().data
    )
    rc = supabase.table("replacement_car_rates").select("*").execute().data
    return classes, insurance, damage, rc


def normalize_str(s):
    if not s:
        return ""
    return str(s).upper().replace(" ", "").replace("-", "")


def build_mapping(old_cls, new_cls):
    mapping = {}
    overrides = {
        "Klasa M MAŁE VANY": next(
            n["id"] for n in new_cls if n["name"] == "B MICROVANY"
        ),
        "PICK-UP": None,
        "KOMERCYJNE": None,
    }

    for oc in old_cls:
        oc_name = str(oc.get("name", "") or "")
        oc_cat = str(oc.get("category", "") or "")

        handled = False
        for k, v in overrides.items():
            if k in oc_name:
                mapping[oc["id"]] = v
                handled = True
                break
        if handled:
            continue

        nom_name = normalize_str(oc_name).replace("PODSTAWOWA", "").replace("KLASA", "")
        nom_cat = (
            normalize_str(oc_cat)
            .replace("TERENOWOREKREACYJNE", "SUV")
            .replace("SPORTOWOREKREACYJNE", "SPORT")
        )

        best_match = None
        for nc in new_cls:
            n_name = normalize_str(nc["name"])
            n_group = normalize_str(nc["category"]).replace(
                "TERENOWOREKREACYJNE(SUV)", "SUV"
            )

            if n_name in nom_name and (n_group in nom_cat or nom_cat in n_group):
                best_match = nc["id"]
                break

        if not best_match:
            for nc in new_cls:
                n_name = normalize_str(nc["name"])
                if n_name in nom_name:
                    best_match = nc["id"]
                    break

        mapping[oc["id"]] = best_match
    return mapping


def generate_sql():
    nc = parse_new_classes()
    oc, ins, dam, rc = get_current_data()
    mapping = build_mapping(oc, nc)

    sql = ["BEGIN;\\n"]

    # 1. Brak tabeli pojazdy_master
    sql.append("-- 1. Brak powiązań wymagających kaskady w master danych")

    # Do the same for brand corrections as it's a structural config we don't want to lose, but wait, brand corrections are heavily tied to samar_class_id. Let's just delete the brand corrections classes and re-insert them? No, brand corrections are currently manually managed, let's keep them if mapped. Actually, let's let cascade wipe config, we will re-insert them. No, we only want to remap insurance, rc, damage. Correct.
    # What about service_base_costs_config, service_rates_config? They don't use samar_class_id, they use local IDs (klasa_id PK).
    # brand corr:
    bc = supabase.table("ltr_admin_korekta_wr_markas").select("*").execute().data
    bc_mapped = []
    bc_seen = set()
    for b in bc:
        if mapping.get(b["samar_class_id"]):
            key = (mapping[b["samar_class_id"]], b["rodzaj_paliwa"], b["brand_name"])
            if key not in bc_seen:
                bc_mapped.append(b)
                bc_seen.add(key)

    # 2. Delete classes (cascades to rates)
    sql.append(
        "\\n-- 2. Twardy reset obecnych klas (Kaskadowo usunie stawki, zrobimy re-insert)"
    )
    sql.append("DELETE FROM public.samar_classes;\\n")

    # 3. Insert 28 New Classes
    sql.append("-- 3. Wrzutka nowych 28 klas SAMAR")
    for c in nc:
        # prepend category for uniqueness since name has a UNIQUE constraint
        nm = f"{c['category']} - {c['name']}".replace("'", "''")
        cat = c["category"].replace("'", "''")
        sc = c["size_class"].replace("'", "''")
        em = c["example_models"].replace("'", "''")
        sql.append(
            f"INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES ({c['id']}, '{nm}', '{cat}', '{sc}', '{em}');"
        )

    # 4. Re-insert Insurance
    sql.append("\\n-- 4. Odtworzenie i zmapowanie stawek ubezpieczeń")
    ins_seen = set()
    for i in ins:
        if mapping.get(i["samar_class_id"]):
            new_id = mapping[i["samar_class_id"]]
            rok = i["KolejnyRok"]
            key = (new_id, rok)
            if key not in ins_seen:
                ins_seen.add(key)
                ac = i["StawkaBazowaAC"]
                oc_a = i["SkladkaOC"]
                sql.append(
                    f'INSERT INTO public.ltr_admin_ubezpieczenia (samar_class_id, \\"KolejnyRok\\", \\"StawkaBazowaAC\\", \\"SkladkaOC\\") VALUES ({new_id}, {rok}, {ac}, {oc_a});'
                )

    # 5. Re-insert Damage
    sql.append("\\n-- 5. Odtworzenie starych współczynników szkodowych")
    dam_seen = set()
    for d in dam:
        if mapping.get(d["samar_class_id"]):
            new_id = mapping[d["samar_class_id"]]
            if new_id not in dam_seen:
                dam_seen.add(new_id)
                km = d["wsp_sredni_przebieg"]
                ws = d["wsp_wartosc_szkody"]
                sql.append(
                    f"INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (samar_class_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES ({new_id}, {km}, {ws});"
                )

    # 6. Re-insert RC rates
    sql.append("\\n-- 6. Odtworzenie stawek wynajmu aut zastępczych")
    rc_seen = set()
    for r in rc:
        if mapping.get(r["samar_class_id"]):
            new_id = mapping[r["samar_class_id"]]
            if new_id not in rc_seen:
                rc_seen.add(new_id)
                mapped_nc = next(n for n in nc if n["id"] == new_id)
                n_name = f"{mapped_nc['category']} - {mapped_nc['name']}".replace(
                    "'", "''"
                )
                net = r["daily_rate_net"]
                avg = r["average_days_per_year"]
                sql.append(
                    f"INSERT INTO public.replacement_car_rates (samar_class_id, samar_class_name, average_days_per_year, daily_rate_net) VALUES ({new_id}, '{n_name}', {avg}, {net});"
                )

    # 7. Re-insert brand corrections
    sql.append("\\n-- 7. Odtworzenie korekt marek bazujących na klasach")
    for b in bc_mapped:
        new_id = mapping.get(b["samar_class_id"])
        if new_id:
            rp = b["rodzaj_paliwa"]
            bn = b["brand_name"].replace("'", "''")
            mn = b["model_name"].replace("'", "''") if b["model_name"] else "NULL"
            if mn != "NULL":
                mn = f"'{mn}'"
            kp = b["korekta_procent"]
            no = b["notes"].replace("'", "''") if b["notes"] else "NULL"
            if no != "NULL":
                no = f"'{no}'"
            sql.append(
                f"INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES ({new_id}, {rp}, '{bn}', {mn}, {kp}, {no});"
            )

    # Final logic updates for vehicles to be relinked
    sql.append("\\n-- 8. Brak pojazdy_master pomijam")

    sql.append("\\nCOMMIT;\\n")

    with open("migration_replacer.sql", "w", encoding="utf-8") as f:
        f.write("\\n".join(sql))

    print("Wygenerowano plik migration_replacer.sql")


if __name__ == "__main__":
    generate_sql()
