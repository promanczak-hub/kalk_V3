import pandas as pd
from core.database import supabase

try:
    cat_res = (
        supabase.schema("reverse_search")
        .table("universal_feature_categories")
        .select("*")
        .execute()
    )
    categories = {
        c["id"]: c.get("display_name", c.get("category_key", "")) for c in cat_res.data
    }
    cat_keys = {c["id"]: c.get("category_key", "") for c in cat_res.data}

    feat_res = (
        supabase.schema("reverse_search")
        .table("universal_features")
        .select("*")
        .execute()
    )
    features = feat_res.data

    rows = []
    for f in features:
        rows.append(
            {
                "Kategoria (klucz)": cat_keys.get(f.get("category_id"), ""),
                "Kategoria (nazwa)": categories.get(f.get("category_id"), ""),
                "Klucz cechy (ENG/pl_bez_spacji)": f.get("feature_key", ""),
                "Nazwa wyświetlana (PL)": f.get("display_name", ""),
                "Typ (boolean/numeric/string)": f.get("feature_type", ""),
                "Zakres (both/commercial/passenger)": f.get("vehicle_scope", ""),
                "Filtrowalne (TRUE/FALSE)": f.get("is_filterable", ""),
                "Karta podsumowania (TRUE/FALSE)": f.get(
                    "is_visible_in_card_summary", ""
                ),
                "Jednostka (np. KM, cm3)": f.get("canonical_unit", ""),
            }
        )

    df = pd.DataFrame(rows)
    output_path = r"C:\Users\proma\Downloads\_cechy użytkowe_wszystkie oddziały- do uzupełnienia (3).xlsx"
    df.to_excel(output_path, index=False)
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
