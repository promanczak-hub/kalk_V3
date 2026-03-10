import uuid
import json
import urllib.request
import urllib.parse
from urllib.error import HTTPError
import unicodedata
import re

online_url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


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


def post_to_supabase(table, data):
    url = f"{online_url}/rest/v1/{table}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal, resolution=merge-duplicates",
        "Content-Profile": "reverse_search",
        "Accept-Profile": "reverse_search",
    }
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Uploaded {len(data)} to {table}: HTTP {response.status}")
    except HTTPError as e:
        print(f"Upload error to {table}: {e.code} - {e.read().decode('utf-8')}")


def main():
    new_features = [
        (
            "Aktywny tempomat (ACC)",
            "aktywny_tempomat",
            "boolean",
            ["Adaptive Cruise Control", "Tempomat adaptacyjny", "Distronic", "ACC"],
        ),
        (
            "Monitorowanie martwego pola (Blind Spot)",
            "monitorowanie_martwego_pola",
            "boolean",
            [
                "Side Assist",
                "BLIS",
                "asystent martwego pola",
                "Side Assist - funkcja monitorowania martwego pola z Rear Traffic Alert oraz Exit Warning",
            ],
        ),
        (
            "Asystent pasa ruchu (Lane Assist)",
            "asystent_pasa_ruchu",
            "boolean",
            [
                "Lane Keeping Assist",
                "LKA",
                "utrzymanie pasa",
                "Lane Assist + Emergency Assist i Traffic Jam Assist",
            ],
        ),
        (
            "Rozpoznawanie znaków drogowych",
            "rozpoznawanie_znakow_drogowych",
            "boolean",
            ["Traffic Sign Recognition", "TSR", "czytanie znaków"],
        ),
        (
            "Kamera cofania",
            "kamera_cofania",
            "boolean",
            ["Rear view camera", "kamera z tyłu"],
        ),
        (
            "Czujniki parkowania przód i tył",
            "czujniki_parkowania_przod_i_tyl",
            "boolean",
            [
                "PDC przód tył",
                "Park Assist",
                "czujniki parkowania z przodu i z tyłu",
                "czujniki parkowania tył oraz przód",
            ],
        ),
        (
            "Matrycowe reflektory LED (Matrix)",
            "matrycowe_reflektory_led",
            "boolean",
            [
                "Full LED Matrix",
                "Matrix LED",
                "IQ.Light",
                "Multibeam",
                "Reflektory Full LED Matrix",
            ],
        ),
        (
            "Cyfrowe zegary",
            "cyfrowe_zegary",
            "boolean",
            [
                "Virtual Cockpit",
                "Active Info Display",
                "cyfrowy zestaw wskaźników",
                "Virtual Cockpit - cyfrowy zestaw wskaźników",
            ],
        ),
        (
            "Klimatyzacja wielostrefowa",
            "klimatyzacja_wielostrefowa",
            "boolean",
            [
                "Climatronic 3-strefowy",
                "klimatyzacja automatyczna trójstrefowa",
                "Klimatyzacja automatyczna 3-strefowa",
                "klimatyzacja automatyczna 2-strefowa",
            ],
        ),
        (
            "Bezkluczykowy dostęp (Keyless)",
            "bezkluczykowy_dostep",
            "boolean",
            [
                "Kessy Full",
                "Keyless Go",
                "Advanced Key",
                "dostęp komfortowy",
                "bezkluczykowy system obsługi samochodu",
                "Bezkluczykowy system obsługi samochodu (bez funkcji SAFE)",
            ],
        ),
        (
            "Elektrycznie sterowana klapa bagażnika",
            "elektrycznie_sterowana_klapa_bagaznika",
            "boolean",
            [
                "Easy Close",
                "elektryczna pokrywa bagażnika",
                "klapa na przycisk",
                "bezdotykowo otwierana elektrycznie sterowana pokrywa bagażnika",
            ],
        ),
        (
            "Podgrzewane fotele przednie",
            "podgrzewane_fotele_przednie",
            "boolean",
            ["Winter pack", "podgrzewane siedzenia", "Podgrzewane fotele z przodu"],
        ),
        (
            "Apple CarPlay / Android Auto",
            "apple_carplay_android_auto",
            "boolean",
            ["SmartLink", "App-Connect", "interfejs smartfona", "Wireless SmartLink"],
        ),
        (
            "Ładowarka indukcyjna do telefonu",
            "ladowarka_indukcyjna",
            "boolean",
            ["ładowanie bezprzewodowe", "wireless charger", "Phone Box"],
        ),
        (
            "Podgrzewana kierownica",
            "podgrzewana_kierownica",
            "boolean",
            ["ogrzewana kierownica"],
        ),
        (
            "Podgrzewana przednia szyba",
            "podgrzewana_przednia_szyba",
            "boolean",
            ["ogrzewana przednia szyba"],
        ),
    ]

    existing_features = get_supabase("universal_features")
    existing_keys = {f["feature_key"] for f in existing_features}

    categories = get_supabase("universal_feature_categories")
    cat_id = None
    for cat in categories:
        if (
            cat["category_key"] == "technologia_i_bezpieczenstwo"
            or cat["category_key"] == "technologia"
        ):
            cat_id = cat["id"]
            break
    if not cat_id and categories:
        cat_id = categories[0]["id"]

    print("Using category_id:", cat_id)

    features_to_insert = []
    aliases_to_insert = []

    for display_name, feature_key, feature_type, aliases in new_features:
        if feature_key in existing_keys:
            print(f"Skipping {feature_key}, already exists.")
            continue

        feat_id = str(uuid.uuid4())
        # Add base feature
        features_to_insert.append(
            {
                "id": feat_id,
                "category_id": cat_id,
                "feature_key": feature_key,
                "display_name": display_name,
                "feature_type": feature_type,
                "vehicle_scope": "both",
                "is_filterable": True,
                "is_active": True,
                "sort_order": 20,
                "metadata": {},
            }
        )

        # Add aliases
        # Add original name as alias too
        all_aliases = [display_name] + aliases
        for alias in set(all_aliases):
            aliases_to_insert.append(
                {
                    "id": str(uuid.uuid4()),
                    "feature_id": feat_id,
                    "alias_text": alias,
                    "normalized_alias": _normalize_text(alias),
                }
            )

    if features_to_insert:
        post_to_supabase("universal_features", features_to_insert)
    if aliases_to_insert:
        # split aliases into chunks of 50 to avoid too large payloads
        for i in range(0, len(aliases_to_insert), 50):
            post_to_supabase("universal_feature_aliases", aliases_to_insert[i : i + 50])

    print(
        "Success. Added",
        len(features_to_insert),
        "features and",
        len(aliases_to_insert),
        "aliases.",
    )


if __name__ == "__main__":
    main()
