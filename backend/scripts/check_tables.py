from core.database import supabase


def check():
    tables = [
        "samar_classes",
        "replacement_car_rates",
        "ltr_admin_ubezpieczenia",
        "control_center",
        "tab_okres_final",
        "engines",
        "ltr_admin_wspolczynniki_szkodowe",
    ]

    print(f"{'Table':<35} | {'Rows':<5}")
    print("-" * 45)

    for t in tables:
        try:
            res = supabase.table(t).select("*", count="exact").limit(0).execute()
            count = res.count if hasattr(res, "count") else len(res.data)
            print(f"{t:<35} | {count:<5}")
        except Exception as e:
            print(f"{t:<35} | ERROR: {e}")


if __name__ == "__main__":
    check()
