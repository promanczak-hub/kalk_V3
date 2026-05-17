"""Sync body_types z GSheet (gid=484265370) do DB.

SOT: GSheet body_types tab (kolumny: ID, Nazwa_Nadwozia, Typ_Pojazdu, Korekta).
DB target: public.body_types (id, nazwa_nadwozia, typ_pojazdu, utrata_wartosci).

Zastępuje wcześniejszy `update_body_types_from_sheet.py` który miał bug
(odwołanie do nieistniejącej kolumny `vehicle_class`) i nie obsługiwał kolumny
korekt.

Uruchomienie:
    python -m backend.scripts.sync_body_types
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

sys.path.append(str(Path(__file__).parent.parent))
from core.database import supabase  # noqa: E402

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
BODY_TYPES_GID = 484265370


def _client() -> gspread.Client:
    key_path = os.environ.get(
        "GOOGLE_SA_KEY_PATH", "D:/kalk_v3/backend/google_sa_key.json"
    )
    creds = Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return gspread.authorize(creds)


def sync_body_types() -> None:
    gc = _client()
    ws = next(
        (w for w in gc.open_by_key(SPREADSHEET_ID).worksheets() if w.id == BODY_TYPES_GID),
        None,
    )
    if ws is None:
        logger.error("Worksheet with gid %s not found", BODY_TYPES_GID)
        return

    raw = ws.get_all_values()
    headers = raw[0]
    rows: list[dict] = []
    for r in raw[1:]:
        if not r or not r[0].strip():
            continue
        rows.append({headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))})
    logger.info("Pobrano %d wierszy z GSheet '%s'", len(rows), ws.title)

    def _to_float(v) -> float:
        """Parse number from GSheet text, accepting Polish comma (0,4) and dot (0.4)."""
        if v is None or v == "":
            return 0.0
        return float(str(v).replace(",", ".").strip())

    existing = (
        supabase.table("body_types")
        .select("id, nazwa_nadwozia, typ_pojazdu, utrata_wartosci")
        .execute()
        .data
        or []
    )
    db_idx = {r["id"]: r for r in existing}

    payloads: list[dict] = []
    added = updated = unchanged = 0
    for r in rows:
        b_id = int(r["ID"])
        payload = {
            "id": b_id,
            "nazwa_nadwozia": str(r["Nazwa_Nadwozia"]).strip(),
            "typ_pojazdu": str(r["Typ_Pojazdu"]).strip(),
            "utrata_wartosci": _to_float(r.get("Korekta")),
        }
        payloads.append(payload)

        prior = db_idx.get(b_id)
        if prior is None:
            added += 1
        elif (
            (prior.get("nazwa_nadwozia") or "").strip() != payload["nazwa_nadwozia"]
            or (prior.get("typ_pojazdu") or "").strip() != payload["typ_pojazdu"]
            or float(prior.get("utrata_wartosci") or 0) != payload["utrata_wartosci"]
        ):
            updated += 1
        else:
            unchanged += 1

    supabase.table("body_types").upsert(payloads, on_conflict="id").execute()
    sot_ids = {p["id"] for p in payloads}
    orphans = [r for r in existing if r["id"] not in sot_ids]

    logger.info(
        "Sync zakończony: added=%d updated=%d unchanged=%d in_db_not_in_sot=%d",
        added,
        updated,
        unchanged,
        len(orphans),
    )
    if orphans:
        logger.warning("Sieroty (w DB, brak w SOT):")
        for o in orphans:
            logger.warning("  id=%s name=%r", o["id"], o.get("nazwa_nadwozia"))


if __name__ == "__main__":
    sync_body_types()
