"""
Usuwa ghost records z vehicle_synthesis.
Ghost record = wpis gdzie synthesis_data jest pusty ({}) lub brak brand i model.

⚠️ WYMAGA POTWIERDZENIA PRZED URUCHOMIENIEM.
Uruchom z --dry-run aby zobaczyc co zostanie usuniete.
Uruchom z --confirm aby faktycznie usunac.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import supabase


def find_ghosts() -> list[dict]:
    """Zwraca liste ghost record'ow do usuniecia."""
    res = supabase.table("vehicle_synthesis").select(
        "id, brand, model, created_at, synthesis_data, verification_status"
    ).execute()

    ghosts = []
    for row in res.data or []:
        sd = row.get("synthesis_data") or {}
        brand = row.get("brand")
        model = row.get("model")

        is_empty_synthesis = not sd or sd == {}
        is_no_brand = not brand or str(brand).strip() in ("", "None", "?")
        is_no_model = not model or str(model).strip() in ("", "None", "?")

        # Ghost = pusty synthesis_data LUB brak marki i modelu jednoczesnie
        if is_empty_synthesis or (is_no_brand and is_no_model):
            ghosts.append({
                "id": row["id"],
                "brand": brand or "?",
                "model": model or "?",
                "created_at": (row.get("created_at") or "?")[:10],
                "status": row.get("verification_status", "?"),
                "reason": "pusty synthesis_data" if is_empty_synthesis else "brak marki i modelu",
            })

    return ghosts


def delete_ghosts(ghost_ids: list[str]) -> int:
    """Usuwa ghost records i powiazane kalkulacje auto_extract. Zwraca liczbe usunietych."""
    deleted = 0
    for vid in ghost_ids:
        # 1. Usun powiazane auto-extract kalkulacje
        supabase.table("ltr_kalkulacje").delete().eq(
            "stan_json->>vehicle_id", vid
        ).eq("stan_json->>source", "auto_extract").execute()

        # 2. Usun vehicle_matrix_cache entries
        supabase.table("vehicle_matrix_cache").delete().eq("vehicle_id", vid).execute()

        # 3. Usun sam rekord
        supabase.table("vehicle_synthesis").delete().eq("id", vid).execute()
        deleted += 1

    return deleted


def main() -> None:
    dry_run = "--confirm" not in sys.argv
    if dry_run:
        print("\n[DRY-RUN] Uruchom z --confirm aby faktycznie usunac rekordy.\n")

    ghosts = find_ghosts()

    if not ghosts:
        print("Brak ghost records. Baza jest czysta!")
        return

    print(f"\nZnaleziono {len(ghosts)} ghost record(s):\n")
    print(f"  {'DATA':<12} {'MARKA/MODEL':<40} {'STATUS':<20} {'POWOD':<25} ID")
    print(f"  {'-'*12} {'-'*40} {'-'*20} {'-'*25} {'-'*36}")
    for g in ghosts:
        label = f"{g['brand']} {g['model']}".strip()
        print(f"  [{g['created_at']}]  {label:<40} {g['status']:<20} {g['reason']:<25} {g['id']}")

    if dry_run:
        print(f"\n[DRY-RUN] Aby usunac te {len(ghosts)} rekordow, uruchom:")
        print("  python scripts/cleanup_ghost_records.py --confirm\n")
        return

    print(f"\nUsuwanie {len(ghosts)} ghost records...")
    ids = [g["id"] for g in ghosts]
    deleted = delete_ghosts(ids)
    print(f"\nGotowe! Usunieto {deleted} ghost records z bazy.")


if __name__ == "__main__":
    main()
