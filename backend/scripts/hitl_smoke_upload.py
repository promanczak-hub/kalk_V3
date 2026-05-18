"""HITL smoke test — upload izoterma_EX.pdf przez backend /extract/async.

Replikuje frontendowy flow z useDocumentProcessing.ts:
1. Oblicza MD5 pliku
2. Sprawdza duplikat w vehicle_synthesis
3. Wstawia nowy wiersz z verification_status='processing'
4. POST /api/extract/async (file + file_id)
5. Pollu je do status='needs_review' albo 'completed'
6. Wypluwa vehicle_id do dalszego użycia
"""

from __future__ import annotations

import hashlib
import sys
import time
import uuid
from pathlib import Path

import httpx

from core.database import supabase

BACKEND_BASE = "http://localhost:8000"
PDF_PATH = Path(r"C:\Users\proma\Downloads\izoterma_EX.pdf")
MAX_WAIT_SECONDS = 240
POLL_INTERVAL = 3


def main() -> None:
    if not PDF_PATH.exists():
        print(f"ERR: brak pliku {PDF_PATH}", file=sys.stderr)
        sys.exit(1)

    raw = PDF_PATH.read_bytes()
    md5 = hashlib.md5(raw).hexdigest()
    print(f"[1/5] MD5: {md5}")

    # Sprawdź duplikat (pomijaj error/cancelled/moved_to_library)
    dup_res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, verification_status")
        .eq("file_hash", md5)
        .not_.in_("verification_status", ("error", "cancelled", "moved_to_library"))
        .limit(1)
        .execute()
    )
    if dup_res.data:
        existing = dup_res.data[0]
        print(
            f"[2/5] DUPLIKAT istnieje: id={existing['id']} "
            f"brand={existing.get('brand')!r} model={existing.get('model')!r} "
            f"status={existing.get('verification_status')!r}"
        )
        if existing.get("verification_status") == "needs_review":
            print(f"VEHICLE_ID={existing['id']}")
            return
        # Re-use ID — czekamy na status
        vehicle_id = existing["id"]
    else:
        vehicle_id = str(uuid.uuid4())
        print(f"[2/5] Brak duplikatu — tworzę nowy wiersz id={vehicle_id}")
        supabase.table("vehicle_synthesis").insert(
            {
                "id": vehicle_id,
                "verification_status": "processing",
                "file_hash": md5,
            }
        ).execute()

        print(f"[3/5] Uploaduje plik {PDF_PATH.name} ({len(raw)/1024:.1f} KB)")
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{BACKEND_BASE}/api/extract/async",
                files={"file": (PDF_PATH.name, raw, "application/pdf")},
                data={"file_id": vehicle_id},
            )
        if response.status_code >= 400:
            print(f"ERR: backend {response.status_code} {response.text}", file=sys.stderr)
            sys.exit(2)
        print(f"[3/5] Backend response: {response.json()}")

    # Poll status
    print(f"[4/5] Polling do needs_review/completed (max {MAX_WAIT_SECONDS}s)")
    deadline = time.time() + MAX_WAIT_SECONDS
    last_status: str | None = None
    while time.time() < deadline:
        res = (
            supabase.table("vehicle_synthesis")
            .select("verification_status, brand, model")
            .eq("id", vehicle_id)
            .single()
            .execute()
        )
        status = (res.data or {}).get("verification_status")
        if status != last_status:
            print(
                f"  • status={status!r} brand={res.data.get('brand')!r} "
                f"model={res.data.get('model')!r}"
            )
            last_status = status
        if status in ("needs_review", "completed", "error"):
            print(f"[5/5] Final status: {status}")
            print(f"VEHICLE_ID={vehicle_id}")
            return
        time.sleep(POLL_INTERVAL)

    print(f"TIMEOUT po {MAX_WAIT_SECONDS}s — ostatni status: {last_status}", file=sys.stderr)
    print(f"VEHICLE_ID={vehicle_id}")
    sys.exit(3)


if __name__ == "__main__":
    main()
