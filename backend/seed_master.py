"""
Master Seeder: Populate engines + samar_classes + all V1 data.

Run: cd backend && python seed_master.py
"""

from core.database import supabase


# ── 1. Engines (9 types matching V1) ──
ENGINES = [
    {"id": 1, "name": "Benzyna (PB)", "category": "spalinowy"},
    {"id": 2, "name": "Diesel (ON)", "category": "spalinowy"},
    {"id": 3, "name": "Benzyna mHEV (PB-mHEV)", "category": "mhev"},
    {"id": 4, "name": "Diesel mHEV (ON-mHEV)", "category": "mhev"},
    {"id": 5, "name": "Hybryda (HEV)", "category": "hybryda"},
    {"id": 6, "name": "Plug-in Hybrid (PHEV)", "category": "phev"},
    {"id": 7, "name": "Elektryczny (BEV)", "category": "ev"},
    {"id": 8, "name": "Wodór (FCEV)", "category": "ev"},
    {"id": 9, "name": "LPG", "category": "spalinowy"},
]

# ── 2. SAMAR Classes (29 klas) ──
SAMAR_CLASSES = [
    {"id": 1, "name": "Klasa A MINI"},
    {"id": 2, "name": "Klasa B MAŁA"},
    {"id": 3, "name": "Klasa Bsuv B-SUV"},
    {"id": 4, "name": "Klasa C KOMPAKTOWA"},
    {"id": 5, "name": "Klasa E WYŻSZA"},
    {"id": 6, "name": "Klasa F LUKSUSOWA"},
    {"id": 7, "name": "Klasa Bvan B-VAN"},
    {"id": 8, "name": "Klasa Cvan C-VAN"},
    {"id": 9, "name": "Klasa Csuv C-SUV"},
    {"id": 10, "name": "Klasa Csport C-SPORT"},
    {"id": 11, "name": "Klasa Dsuv D-SUV"},
    {"id": 12, "name": "Klasa Dsport D-SPORT"},
    {"id": 13, "name": "Klasa Dvan D-VAN"},
    {"id": 14, "name": "Klasa D ŚREDNIA"},
    {"id": 15, "name": "Klasa A000 MIKRO"},
    {"id": 16, "name": "Klasa Asport A-SPORT"},
    {"id": 17, "name": "Klasa Asuv A-SUV"},
    {"id": 18, "name": "Klasa Bsport B-SPORT"},
    {"id": 19, "name": "Klasa Dsport D-SPORT/2"},
    {"id": 20, "name": "Klasa Dsuv D-SUV/2"},
    {"id": 21, "name": "Klasa Dvan D-VAN/2"},
    {"id": 22, "name": "Klasa Esuv E-SUV"},
    {"id": 23, "name": "Klasa Fsport F-SPORT"},
    {"id": 24, "name": "Klasa Fsuv F-SUV"},
    {"id": 25, "name": "Klasa M MULTI-VAN"},
    {"id": 26, "name": "Klasa Mvan M-DOSTAWCZY"},
    {"id": 27, "name": "Klasa R REKREACJA"},
    {"id": 28, "name": "Klasa P DOSTAWCZY LEKKI"},
    {"id": 29, "name": "Klasa T PICK-UP"},
]


def seed_engines() -> int:
    """Upsert engines."""
    print("⚙️  Seeding engines...")
    res = supabase.table("engines").upsert(ENGINES, on_conflict="id").execute()
    cnt = len(res.data) if res.data else 0
    print(f"   ✅ {cnt} engines upserted")
    return cnt


def seed_samar_classes() -> int:
    """Upsert samar_classes."""
    print("📊 Seeding samar_classes...")
    res = (
        supabase.table("samar_classes")
        .upsert(SAMAR_CLASSES, on_conflict="id")
        .execute()
    )
    cnt = len(res.data) if res.data else 0
    print(f"   ✅ {cnt} classes upserted")
    return cnt


def run_seeder(script_name: str) -> None:
    """Run a seeder script by importing and calling main()."""
    import importlib
    import sys

    mod_name = script_name.replace(".py", "")
    print(f"\n🚀 Uruchamiam: {script_name} ...")
    try:
        if mod_name in sys.modules:
            mod = importlib.reload(sys.modules[mod_name])
        else:
            mod = importlib.import_module(mod_name)
        if hasattr(mod, "main"):
            mod.main()
            print(f"   ✅ {script_name} — zakończone")
        else:
            print(f"   ⚠️  {script_name} nie ma funkcji main()")
    except FileNotFoundError as e:
        print(f"   ❌ {script_name} — brak pliku Excel: {e}")
    except Exception as e:
        print(f"   ❌ {script_name} — błąd: {e}")


def main() -> None:
    print("=" * 60)
    print("MASTER SEEDER — V1 → V3 data import")
    print("=" * 60)

    # Phase 1: Master dictionaries
    seed_engines()
    seed_samar_classes()

    # Phase 2: Excel-based seeders (require engines + samar_classes)
    SEEDERS = [
        "seed_depreciation_rates",
        "seed_body_and_brand_corrections",
        "seed_body_types",
        "seed_replacement_rates",
        "seed_budget_data",
    ]
    for s in SEEDERS:
        run_seeder(s)

    # Phase 3: CSV/Excel importers
    IMPORTERS = [
        "v1_insurance_seeder",
        "import_tabele_rabaty",
        "import_rabaty_bmw",
    ]
    for s in IMPORTERS:
        run_seeder(s)

    # Phase 4: Audit
    print("\n" + "=" * 60)
    print("📋 AUDIT — stan tabel po seedowaniu:")
    print("=" * 60)

    AUDIT_TABLES = [
        "engines",
        "samar_classes",
        "samar_class_depreciation_rates",
        "samar_class_mileage_corrections",
        "samar_brand_corrections",
        "body_type_wr_corrections",
        "body_types",
        "replacement_car_rates",
        "samar_service_costs",
        "tabela_rabaty",
        "koszty_opon",
        "zabudowa_types",
        "zabudowa_wr_corrections",
    ]
    for t in AUDIT_TABLES:
        try:
            r = supabase.table(t).select("*").limit(1).execute()
            cnt = len(r.data)
            s = "✅ HAS DATA" if cnt else "❌ EMPTY"
            print(f"  {t:<45} {s}")
        except Exception as e:
            print(f"  {t:<45} ⚠️  ERR: {str(e)[:40]}")

    print("\n🎉 Master seed zakończony!")


if __name__ == "__main__":
    main()
