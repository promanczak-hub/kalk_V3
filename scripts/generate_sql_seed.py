import json
import uuid


def generate_sql():
    try:
        with open("d:\\kalk_v3\\parsed_features.json", "r", encoding="utf-8") as f:
            features = json.load(f)

        # Group features into categories based on some simple substring matching for now
        # (or just put them in a generic category for the seed, as a starting point)
        categories = {
            "Wymiary i Masy": [
                "długość",
                "szerokość",
                "wysokość",
                "masa",
                "ładowność",
                "progu",
            ],
            "Silnik i Napęd": [
                "naped",
                "napęd",
                "paliwa",
                "zasięg",
                "akumulatora",
                "lpg",
                "silnik",
            ],
            "Przestrzeń Ładunkowa": [
                "przestrzeni",
                "europalet",
                "kubatura",
                "nadkolami",
            ],
            "Zabudowy Specjalistyczne": [
                "chłodni",
                "agregat",
                "winda",
                "wywrot",
                "tachograf",
                "sypialna",
                "webasto",
            ],
            "Komfort i Wnętrze": [
                "klimatyzacja",
                "fotel",
                "kierownica",
                "radio",
                "audio",
                "szyby",
                "tapicerka",
                "podłokietnik",
                "gniazd",
                "rolet",
            ],
            "Bezpieczeństwo": [
                "poduszk",
                "abs",
                "asr",
                "esp",
                "czujnik",
                "kamer",
                "isofix",
                "tempomat",
                "alarm",
                "immobiliser",
                "asystent",
            ],
            "Wygląd Zewnętrzny": [
                "reflektor",
                "felg",
                "lakier",
                "relingi",
                "dach",
                "lusterka",
                "drzwi",
            ],
            "Inne": [],
        }

        category_uuids = {k: str(uuid.uuid4()) for k in categories.keys()}

        def assign_category(feat_name):
            name_lower = feat_name.lower()
            for cat_name, keywords in categories.items():
                if any(kw in name_lower for kw in keywords):
                    return category_uuids[cat_name]
            return category_uuids["Inne"]

        sql_lines = []
        sql_lines.append("-- Wyczyść stare dane (opcjonalnie)")
        sql_lines.append("DELETE FROM reverse_search.universal_features;")
        sql_lines.append("DELETE FROM reverse_search.universal_feature_categories;")
        sql_lines.append("")

        sql_lines.append("-- Dodaj Kategorie")
        for cat_name, cat_id in category_uuids.items():
            slug = cat_name.lower().replace(" i ", "_").replace(" ", "_")
            sql_lines.append(
                f"INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('{cat_id}', '{slug}', '{cat_name}');"
            )

        sql_lines.append("")
        sql_lines.append("-- Dodaj Cechy")
        for f in features:
            f_id = str(uuid.uuid4())
            cat_id = assign_category(f["display_name"])
            f_key = f["feature_key"]
            f_name = f["display_name"].replace("'", "''")
            f_type = f["feature_type"]

            # Metadata for enums
            meta_str = "NULL"
            if f_type == "enum" and f["options"]:
                meta_json = json.dumps({"options": f["options"]}, ensure_ascii=False)
                meta_str = f"'{meta_json}'::jsonb"

            sql_lines.append(
                "INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) "
            )
            sql_lines.append(
                f"VALUES ('{f_id}', '{cat_id}', '{f_key}', '{f_name}', '{f_type}', {meta_str});"
            )

        with open("d:\\kalk_v3\\seed_features.sql", "w", encoding="utf-8") as f:
            f.write("\n".join(sql_lines))

        print("Successfully generated seed_features.sql")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    generate_sql()
