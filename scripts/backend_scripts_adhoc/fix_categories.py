import urllib.request
import json

online_url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"


def get_supabase(table):
    url = f"{online_url}/rest/v1/{table}?select=*"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept-Profile": "reverse_search",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def post_supabase(table, data):
    url = f"{online_url}/rest/v1/{table}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal, resolution=merge-duplicates",
        "Content-Profile": "reverse_search",
    }
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Upserted {len(data)} to {table}")
    except urllib.error.HTTPError as e:
        print(f"Upsert error: {e.code} - {e.read().decode('utf-8')}")


categories = get_supabase("universal_feature_categories")
cat_map = {c["category_key"]: c["id"] for c in categories}
print("Available categories:", list(cat_map.keys()))

# Mapping features to correct category keys
feat_cat_map = {
    "aktywny_tempomat": "bezpieczeństwo",
    "monitorowanie_martwego_pola": "bezpieczeństwo",
    "asystent_pasa_ruchu": "bezpieczeństwo",
    "rozpoznawanie_znakow_drogowych": "bezpieczeństwo",
    "kamera_cofania": "parking",
    "czujniki_parkowania_przod_i_tyl": "parking",
    "matrycowe_reflektory_led": "lighting",
    "cyfrowe_zegary": "komfort_wnętrze",
    "klimatyzacja_wielostrefowa": "komfort_wnętrze",
    "bezkluczykowy_dostep": "komfort_wnętrze",
    "elektrycznie_sterowana_klapa_bagaznika": "komfort_wnętrze",
    "podgrzewane_fotele_przednie": "seats",
    "apple_carplay_android_auto": "multimedia",
    "ladowarka_indukcyjna": "multimedia",
    "podgrzewana_kierownica": "komfort_wnętrze",
    "podgrzewana_przednia_szyba": "komfort_wnętrze",
}

features = get_supabase("universal_features")
to_update = []
for f in features:
    if f["feature_key"] in feat_cat_map:
        cat_key = feat_cat_map[f["feature_key"]]
        cat_id = cat_map.get(cat_key)
        if cat_id:
            updated_f = dict(f)
            updated_f["category_id"] = cat_id
            to_update.append(updated_f)
            print(f"Mapping {f['feature_key']} to {cat_key} ({cat_id})")
        else:
            print(f"Warning: Category {cat_key} not found for {f['feature_key']}")

if to_update:
    post_supabase("universal_features", to_update)
