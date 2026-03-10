import json
import uuid


def generate_online_sql():
    with open("d:\\kalk_v3\\excel_info.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    features_columns = data["columns"]
    samples = data["sample_rows"]

    # We want to skip first few columns typically vin, nr rej, nr kontraktu, Klasa
    skip_columns = {"vin", "nr rej", "nr kontraktu", "Klasa"}
    filtered_features = [c for c in features_columns if c not in skip_columns]

    categories = {
        "Wymiary": ["długość", "szerokość", "wysokość", "nadkolami"],
        "Cargo / Ładunek": [
            "przestrzeni",
            "europalet",
            "kubatura",
            "ładowność",
            "progu",
            "burt",
            "plandeki",
        ],
        "Zabudowa": [
            "chłodni",
            "agregat",
            "winda",
            "wywrot",
            "izoterma",
            "rodzaj zabudowy",
            "zabudowy",
            "ściana",
        ],
        "Holowanie / Hak": [
            "hak",
            "uciag",
            "przyczepy",
            "zespołu pojazdów",
            "nacisk na hak",
        ],
        "Instalacja LPG": ["lpg"],
        "Winda / Tachograf / Wywrot": ["tachograf", "wywrot", "windy", "winda"],
        "Napęd / Paliwo / EV": [
            "naped",
            "napęd",
            "paliwa",
            "zasięg",
            "akumulatora",
            "kabel",
            "wtyczki",
        ],
        "Komfort": [
            "klimatyzacja",
            "fotel",
            "kierownica",
            "radio",
            "audio",
            "szyby",
            "podłokietnik",
            "gniazd",
            "rolet",
            "tempomat",
            "webasto",
        ],
        "Bezpieczeństwo": [
            "poduszk",
            "abs",
            "asr",
            "esp",
            "czujnik",
            "kamer",
            "isofix",
            "alarm",
            "immobiliser",
            "asystent",
            "tachograf",
        ],
        "Oświetlenie": ["reflektor", "światła", "lampy"],
        "Kabina / Dach": ["sypialna", "dach", "relingi", "spoiler"],
    }

    # Get Category IDs
    # I will query them using deterministic UUIDs based on category key, but better to insert them or just use subquery

    sql_lines = []
    sql_lines.append(
        "-- Skrypt do zasilenia bazy produkcyjnej nowymi cechami uzytkowymi z pliku Excel"
    )
    sql_lines.append("")
    # Because category IDs might be different in production, we will use a subquery to find category_id by category_key
    # Assuming 'dimensions', 'cargo', 'loading', 'bodywork', 'towing', 'lpg', 'refrigeration', 'lift_tachograph', 'drivetrain', 'body_type', 'comfort', 'safety', 'multimedia', 'seats', 'lighting', 'security', 'cabin', 'energy'

    cat_mapping = {
        "Wymiary": "dimensions",
        "Cargo / Ładunek": "cargo",
        "Zabudowa": "bodywork",
        "Holowanie / Hak": "towing",
        "Instalacja LPG": "lpg",
        "Winda / Tachograf / Wywrot": "lift_tachograph",
        "Napęd / Paliwo / EV": "drivetrain",
        "Komfort": "comfort",
        "Bezpieczeństwo": "safety",
        "Oświetlenie": "lighting",
        "Kabina / Dach": "cabin",
    }

    def assign_category_slug(feat_name):
        name_lower = feat_name.lower()
        for cat_name, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                return cat_mapping.get(cat_name, "bodywork")
        return "bodywork"

    def determine_type(col_name, sample_vals):
        # Check standard boolean indicators
        if "(tak/nie)" in col_name.lower():
            return "boolean"

        # Check numeric indicators
        num_keywords = [
            " w mm",
            " w kg",
            " w m3",
            " w litrach",
            " w km",
            " kwh",
            "miesiącach",
            "ilość",
        ]
        if any(kw in col_name.lower() for kw in num_keywords):
            return "numeric"

        # Try to parse sample vals
        for v in sample_vals:
            if v == "X" or v == "x" or v is None:
                continue
            try:
                float(v)
                return "numeric"
            except:
                pass

        return "text"

    for feat in filtered_features:
        f_key = (
            feat.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("\\n", "_")
            .replace("/", "_")
            .replace(",", "")
            .replace("-", "_")
            .replace("°", "st")
        )
        # clean multiple underscores
        while "__" in f_key:
            f_key = f_key.replace("__", "_")
        f_key = f_key.strip("_")

        f_name = feat.replace("'", "''").replace("\\n", " ").strip()
        cat_slug = assign_category_slug(feat)

        sample_vals = [s.get(feat) for s in samples if s.get(feat) is not None]
        f_type = determine_type(feat, sample_vals)

        f_id = str(uuid.uuid4())

        sql = f"""
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '{f_id}', id, '{f_key}', '{f_name}', '{f_type}', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = '{cat_slug}'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;
"""
        sql_lines.append(sql.strip())

    with open("d:\\kalk_v3\\online_features_import.sql", "w", encoding="utf-8") as f:
        f.write("\n\n".join(sql_lines))

    print("Wygenerowano plik d:\\kalk_v3\\online_features_import.sql")


if __name__ == "__main__":
    generate_online_sql()
