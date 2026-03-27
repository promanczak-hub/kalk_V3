import sys
import os
import logging

# Add the parent directory to sys.path if not running through a proper entrypoint
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client
from migrate_excel_to_prod import (
    _load_samar_classes,
    _load_sheet,
    _parse_monolith,
    _safe_float,
)
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

# Create a service role client that bypasses RLS
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def migrate_kolor():
    logger.info("--- MIGRATING KOLOR ---")
    rows = _load_sheet(supabase, "KOLOR")
    if not rows:
        return

    # We map common names from excel_drafts (like "Akryl", "Metalik", "Perła") to paint_types names.
    # The IDs in paint_types: 1=Niemetalizowany (Bazowy), 2=Metalizowany (Metalik), 3=Perłowy
    # So we'll fetch existing first.
    res = supabase.table("paint_types").select("*").execute()
    existing = res.data or []
    id_map = {
        "Akryl (B/D)": 1,
        "Niemetalizowany (Bazowy)": 1,
        "Metalik (+)": 2,
        "Metalizowany (Metalik)": 2,
        "Perła / Specjalny (++)": 3,
        "Perłowy": 3,
    }

    updates = []
    for row in rows:
        name = row.get("col_1", "").strip()
        val = _safe_float(row.get("col_2"))

        type_id = id_map.get(name)
        if type_id:
            updates.append({"id": type_id, "wr_correction": val})
        else:
            logger.warning("Nie rozpoznano typu lakieru: %s", name)

    if updates:
        # Instead of API upserts, let's write to a SQL file for MCP execution
        with open("migration_output.sql", "a", encoding="utf-8") as f:
            for update in updates:
                f.write(
                    f"UPDATE public.paint_types SET wr_correction = {update['wr_correction']} WHERE id = {update['id']};\n"
                )
        logger.info("Generated SQL for %d paint_types", len(updates))


def migrate_kor_marka(class_map: dict[str, int]):
    logger.info("--- MIGRATING KOR. MARKA ---")
    rows = _load_sheet(supabase, "KOR. MARKA")
    if not rows:
        return

    inserts = []
    for row in rows:
        col1 = row.get("col_1", "")
        brand_name = row.get("col_2", "").strip().upper()
        korekta = _safe_float(row.get("col_4"))

        parsed = _parse_monolith(col1, class_map)
        if not parsed:
            continue
        samar_id, fuel_id = parsed

        if brand_name:
            inserts.append(
                {
                    "klasa_wr_id": samar_id,
                    "rodzaj_paliwa": fuel_id,
                    "brand_name": brand_name,
                    "korekta_procent": korekta,
                }
            )

    if inserts:
        with open("migration_output.sql", "a", encoding="utf-8") as f:
            for ins in inserts:
                brand_safe = ins["brand_name"].replace("'", "''")
                f.write(f"""
INSERT INTO public.ltr_admin_korekta_wr_markas (klasa_wr_id, rodzaj_paliwa, brand_name, korekta_procent) 
VALUES ({ins["klasa_wr_id"]}, {ins["rodzaj_paliwa"]}, '{brand_safe}', {ins["korekta_procent"]}) 
ON CONFLICT (klasa_wr_id, rodzaj_paliwa, brand_name) DO UPDATE SET korekta_procent = excluded.korekta_procent;
""")
        logger.info("Generated SQL for %d brand corrections", len(inserts))


def migrate_nadwozie():
    logger.info("--- MIGRATING NADWOZIE ---")
    rows = _load_sheet(supabase, "NADWOZIE")
    if not rows:
        return

    draft_dict = {
        row.get("col_1", "").strip(): _safe_float(row.get("col_2")) for row in rows
    }

    res_bt = supabase.table("body_types").select("*").execute()
    body_types = res_bt.data or []

    bt_rules = {}
    for bt in body_types:
        name_with_desc = f"{bt['vehicle_class']} - {bt['name']}"
        val = draft_dict.get(name_with_desc, 0.0)

        vclass = str(bt.get("vehicle_class", "")).strip().upper()
        bname = str(bt.get("name", "")).strip().upper()

        if vclass in ("DOSTAWCZY", "CIĘŻAROWY"):
            if bname != "FURGON":
                val = 0.04

        bt_rules[bt["id"]] = val

    logger.info("Fetching existing body_type_wr_corrections (might be large)...")
    limit = 1000
    offset = 0
    all_bt_corr = []

    while True:
        res_existing = (
            supabase.table("body_type_wr_corrections")
            .select("id, body_type_id")
            .range(offset, offset + limit - 1)
            .execute()
        )
        batch = res_existing.data or []
        all_bt_corr.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    if not all_bt_corr:
        logger.warning(
            "No existing rows in body_type_wr_corrections found. Run seed script first."
        )
        return

    updates = []
    for item in all_bt_corr:
        bt_id = item["body_type_id"]
        if bt_id in bt_rules:
            updates.append({"id": item["id"], "correction_percent": bt_rules[bt_id]})

    if updates:
        with open("migration_output.sql", "a", encoding="utf-8") as f:
            for update in updates:
                f.write(
                    f"UPDATE public.body_type_wr_corrections SET correction_percent = {update['correction_percent']} WHERE id = {update['id']};\n"
                )
        logger.info("Generated SQL for NADWOZIE (rows: %d)", len(updates))


def migrate_all():
    if os.path.exists("migration_output.sql"):
        os.remove("migration_output.sql")
    class_map = _load_samar_classes(supabase)
    migrate_kolor()
    migrate_kor_marka(class_map)
    migrate_nadwozie()
    logger.info("All SQL generated to migration_output.sql")


if __name__ == "__main__":
    try:
        migrate_all()
    except Exception:
        import traceback

        with open("error_trace.txt", "w") as f:
            traceback.print_exc(file=f)
        logger.error("Failed due to an exception. See error_trace.txt")
