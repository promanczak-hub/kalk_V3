import os
import csv
import logging
import psycopg2
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()
db_url = os.environ.get(
    "SUPABASE_DB_URL",
    "postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@aws-1-eu-central-1.pooler.supabase.com:6543/postgres",
)

db_url = os.environ.get(
    "SUPABASE_DB_URL",
    "postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@aws-1-eu-central-1.pooler.supabase.com:6543/postgres",
)


def apply_schema():
    print("Applying schema...")
    sql = """
    CREATE TABLE IF NOT EXISTS public.samar_service_brand_multipliers (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        brand_normalized VARCHAR NOT NULL UNIQUE,
        multiplier NUMERIC NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public.samar_service_fuel_multipliers (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        fuel_normalized VARCHAR NOT NULL UNIQUE,
        multiplier NUMERIC NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public.samar_service_drive_multipliers (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        drive_normalized VARCHAR NOT NULL UNIQUE,
        multiplier NUMERIC NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public.samar_service_gearbox_multipliers (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        gearbox_normalized VARCHAR NOT NULL UNIQUE,
        multiplier NUMERIC NOT NULL
    );

    CREATE TABLE IF NOT EXISTS public.samar_class_service_rates (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
        mileage_up_to BIGINT NOT NULL,
        cost_aso_per_km NUMERIC NOT NULL,
        cost_non_aso_per_km NUMERIC NOT NULL,
        UNIQUE(samar_class_id, mileage_up_to)
    );

    ALTER TABLE public.samar_service_brand_multipliers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.samar_service_fuel_multipliers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.samar_service_drive_multipliers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.samar_service_gearbox_multipliers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.samar_class_service_rates ENABLE ROW LEVEL SECURITY;
    
    -- Drop old policies to re-add them without errors
    DROP POLICY IF EXISTS "Enable read for all" ON public.samar_service_brand_multipliers;
    DROP POLICY IF EXISTS "Enable read for all" ON public.samar_service_fuel_multipliers;
    DROP POLICY IF EXISTS "Enable read for all" ON public.samar_service_drive_multipliers;
    DROP POLICY IF EXISTS "Enable read for all" ON public.samar_service_gearbox_multipliers;
    DROP POLICY IF EXISTS "Enable read for all" ON public.samar_class_service_rates;
    
    DROP POLICY IF EXISTS "Enable all for authenticated" ON public.samar_service_brand_multipliers;
    DROP POLICY IF EXISTS "Enable all for authenticated" ON public.samar_service_fuel_multipliers;
    DROP POLICY IF EXISTS "Enable all for authenticated" ON public.samar_service_drive_multipliers;
    DROP POLICY IF EXISTS "Enable all for authenticated" ON public.samar_service_gearbox_multipliers;
    DROP POLICY IF EXISTS "Enable all for authenticated" ON public.samar_class_service_rates;

    CREATE POLICY "Enable read for all" ON public.samar_service_brand_multipliers FOR SELECT USING (true);
    CREATE POLICY "Enable all for authenticated" ON public.samar_service_brand_multipliers FOR ALL TO authenticated USING (true) WITH CHECK(true);

    CREATE POLICY "Enable read for all" ON public.samar_service_fuel_multipliers FOR SELECT USING (true);
    CREATE POLICY "Enable all for authenticated" ON public.samar_service_fuel_multipliers FOR ALL TO authenticated USING (true) WITH CHECK(true);

    CREATE POLICY "Enable read for all" ON public.samar_service_drive_multipliers FOR SELECT USING (true);
    CREATE POLICY "Enable all for authenticated" ON public.samar_service_drive_multipliers FOR ALL TO authenticated USING (true) WITH CHECK(true);

    CREATE POLICY "Enable read for all" ON public.samar_service_gearbox_multipliers FOR SELECT USING (true);
    CREATE POLICY "Enable all for authenticated" ON public.samar_service_gearbox_multipliers FOR ALL TO authenticated USING (true) WITH CHECK(true);

    CREATE POLICY "Enable read for all" ON public.samar_class_service_rates FOR SELECT USING (true);
    CREATE POLICY "Enable all for authenticated" ON public.samar_class_service_rates FOR ALL TO authenticated USING (true) WITH CHECK(true);

    -- Grant access safely
    GRANT SELECT, INSERT, UPDATE, DELETE ON public.samar_service_brand_multipliers TO authenticated, anon;
    GRANT SELECT, INSERT, UPDATE, DELETE ON public.samar_service_fuel_multipliers TO authenticated, anon;
    GRANT SELECT, INSERT, UPDATE, DELETE ON public.samar_service_drive_multipliers TO authenticated, anon;
    GRANT SELECT, INSERT, UPDATE, DELETE ON public.samar_service_gearbox_multipliers TO authenticated, anon;
    GRANT SELECT, INSERT, UPDATE, DELETE ON public.samar_class_service_rates TO authenticated, anon;
    """
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print("Schema applied successfully.")


def normalize_float(val: str) -> float:
    return float(val.replace(",", ".").replace(" ", "").strip())


def seed_multipliers():
    print("Seeding multipliers...")
    brands = []
    drives = []
    fuels = []
    gearboxes = []

    with open("tmp_multipliers.csv", mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row or len(row) < 11:
                row = row + [""] * (11 - len(row))

            # Brand (Idx 0 and 1)
            if row[0].strip() and row[1].strip():
                brands.append(
                    {
                        "brand_normalized": row[0].strip().upper(),
                        "multiplier": normalize_float(row[1]),
                    }
                )

            # Drive (Idx 3 and 4)
            if row[3].strip() and row[4].strip():
                drives.append(
                    {
                        "drive_normalized": row[3].strip().upper(),
                        "multiplier": normalize_float(row[4]),
                    }
                )

            # Fuel (Idx 6 and 7)
            if row[6].strip() and row[7].strip():
                fuels.append(
                    {
                        "fuel_normalized": row[6].strip().upper(),
                        "multiplier": normalize_float(row[7]),
                    }
                )

            # Gearbox (Idx 9 and 10)
            if row[9].strip() and row[10].strip():
                gearboxes.append(
                    {
                        "gearbox_normalized": row[9].strip().upper(),
                        "multiplier": normalize_float(row[10]),
                    }
                )

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    if brands:
        cur.executemany(
            "INSERT INTO public.samar_service_brand_multipliers (brand_normalized, multiplier) VALUES (%(brand_normalized)s, %(multiplier)s) ON CONFLICT (brand_normalized) DO UPDATE SET multiplier = EXCLUDED.multiplier",
            brands,
        )
    if fuels:
        cur.executemany(
            "INSERT INTO public.samar_service_fuel_multipliers (fuel_normalized, multiplier) VALUES (%(fuel_normalized)s, %(multiplier)s) ON CONFLICT (fuel_normalized) DO UPDATE SET multiplier = EXCLUDED.multiplier",
            fuels,
        )
    if drives:
        cur.executemany(
            "INSERT INTO public.samar_service_drive_multipliers (drive_normalized, multiplier) VALUES (%(drive_normalized)s, %(multiplier)s) ON CONFLICT (drive_normalized) DO UPDATE SET multiplier = EXCLUDED.multiplier",
            drives,
        )
    if gearboxes:
        cur.executemany(
            "INSERT INTO public.samar_service_gearbox_multipliers (gearbox_normalized, multiplier) VALUES (%(gearbox_normalized)s, %(multiplier)s) ON CONFLICT (gearbox_normalized) DO UPDATE SET multiplier = EXCLUDED.multiplier",
            gearboxes,
        )

    conn.commit()
    cur.close()
    conn.close()

    print(
        f"Upserted {len(brands)} brands, {len(fuels)} fuels, {len(drives)} drives, {len(gearboxes)} gearboxes."
    )


def seed_base_rates():
    print("Seeding base rates...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM public.samar_classes")
    class_map = {row[1].strip().upper(): row[0] for row in cur.fetchall()}

    rates = []
    with open("tmp_base_rates.csv", mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 4:
                continue
            cls_name = row[0].strip().upper()
            if cls_name not in class_map:
                print(f"WARNING: Class {cls_name} not found in DB!")
                continue

            rates.append(
                {
                    "samar_class_id": class_map[cls_name],
                    "mileage_up_to": int(row[1].strip()),
                    "cost_aso_per_km": normalize_float(row[2]),
                    "cost_non_aso_per_km": normalize_float(row[3]),
                }
            )

    if rates:
        cur.executemany(
            "INSERT INTO public.samar_class_service_rates (samar_class_id, mileage_up_to, cost_aso_per_km, cost_non_aso_per_km) VALUES (%(samar_class_id)s, %(mileage_up_to)s, %(cost_aso_per_km)s, %(cost_non_aso_per_km)s) ON CONFLICT (samar_class_id, mileage_up_to) DO UPDATE SET cost_aso_per_km = EXCLUDED.cost_aso_per_km, cost_non_aso_per_km = EXCLUDED.cost_non_aso_per_km",
            rates,
        )
        conn.commit()

    cur.close()
    conn.close()

    print(f"Upserted {len(rates)} base rate rules.")


if __name__ == "__main__":
    apply_schema()
    seed_multipliers()
    seed_base_rates()
