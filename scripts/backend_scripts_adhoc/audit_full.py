"""Full audit of klasa_wr_id, klasa_id, KlasaId across entire DB."""

from core.database import supabase

TABLES = [
    "ltr_admin_korekta_wr_markas",
    "ltr_admin_stawki_ubezpieczen",
    "ltr_admin_wspolczynniki_szkodowe",
    "ltr_admin_korekta_wr_roczniks",
    "samar_classes",
    "samar_class_depreciation_rates",
    "samar_class_mileage_corrections",
    "body_type_wr_corrections",
    "zabudowa_wr_corrections",
    "replacement_car_rates",
    "pojazdy_master",
    "vehicle_synthesis",
    "koszty_opon",
    "paint_types",
    "engines",
    "control_center",
    "KlasaSAMAR_czak",
]

lines: list[str] = []
for t in TABLES:
    try:
        resp = supabase.table(t).select("*").limit(1).execute()
        if resp.data:
            cols = list(resp.data[0].keys())
            hits = [
                c
                for c in cols
                if any(k in c.lower() for k in ("klasa", "samar", "class"))
            ]
            lines.append(f"{t}: ALL_COLS={cols}")
            lines.append(f"  SAMAR_HITS={hits}")
        else:
            lines.append(f"{t}: (empty) - checking schema impossible")
    except Exception as e:
        err = str(e)[:100]
        lines.append(f"{t}: ERR={err}")

with open("d:\\kalk_v3\\full_audit.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
