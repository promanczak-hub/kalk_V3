import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_admin_client


def main() -> int:
    numer = sys.argv[1] if len(sys.argv) > 1 else "KALK/2026/05/2A86AC"
    client = get_admin_client()

    print(f"=== Diagnostyka powiazania ltr_kalkulacje <-> vehicle_synthesis ===")
    print(f"numer_kalkulacji: {numer}\n")

    # --- Krok 1: znalezc kalkulacje ---
    kalk_res = (
        client.table("ltr_kalkulacje")
        .select("id, numer_kalkulacji, status, created_at, updated_at, stan_json")
        .eq("numer_kalkulacji", numer)
        .execute()
    )
    rows = kalk_res.data or []

    if not rows:
        print(f"[KROK 1] BRAK kalkulacji o numerze {numer}")
        print("Wniosek: numer kalkulacji nie istnieje w ltr_kalkulacje.")
        return 0

    if len(rows) > 1:
        print(f"[KROK 1] UWAGA: znaleziono {len(rows)} kalkulacji o tym samym numerze")

    kalk = rows[0]
    stan_json = kalk.get("stan_json") or {}
    vehicle_id = stan_json.get("vehicle_id") if isinstance(stan_json, dict) else None
    has_key = isinstance(stan_json, dict) and "vehicle_id" in stan_json
    source_hint = stan_json.get("source") if isinstance(stan_json, dict) else None
    created_via = stan_json.get("created_via") if isinstance(stan_json, dict) else None

    kalk_summary = {
        "id": kalk.get("id"),
        "numer_kalkulacji": kalk.get("numer_kalkulacji"),
        "status": kalk.get("status"),
        "created_at": kalk.get("created_at"),
        "updated_at": kalk.get("updated_at"),
        "has_vehicle_id_key": has_key,
        "vehicle_id": vehicle_id,
        "source_hint": source_hint,
        "created_via": created_via,
        "stan_json_top_level_keys": sorted(stan_json.keys()) if isinstance(stan_json, dict) else None,
    }
    print("[KROK 1] ltr_kalkulacje:")
    print(json.dumps(kalk_summary, indent=2, ensure_ascii=False, default=str))

    if not vehicle_id:
        print("\n=== WNIOSEK: scenariusz #4 ===")
        print("Kalkulacja nie ma klucza 'vehicle_id' w stan_json (lub jest pusty).")
        print("Sprawdz czy uzywany jest inny wariant nazwy: vehicleId, vehicle_synthesis_id, itp.")
        if isinstance(stan_json, dict):
            print(f"Wszystkie klucze top-level stan_json: {sorted(stan_json.keys())}")
        return 0

    # --- Krok 2: sprawdzic vehicle_synthesis ---
    vs_res = (
        client.table("vehicle_synthesis")
        .select(
            "id, brand, model, verification_status, notes, document_category, "
            "created_at, processing_updated_at, raw_pdf_url, synthesis_data"
        )
        .eq("id", vehicle_id)
        .execute()
    )
    vs_rows = vs_res.data or []

    print(f"\n[KROK 2] vehicle_synthesis WHERE id = {vehicle_id}:")
    if not vs_rows:
        print("BRAK rekordu vehicle_synthesis o tym id.")
        vs_status = None
    else:
        vs = vs_rows[0]
        vs_status = vs.get("verification_status")
        vs_summary = {
            "id": vs.get("id"),
            "brand": vs.get("brand"),
            "model": vs.get("model"),
            "verification_status": vs_status,
            "notes": vs.get("notes"),
            "document_category": vs.get("document_category"),
            "created_at": vs.get("created_at"),
            "processing_updated_at": vs.get("processing_updated_at"),
            "has_synthesis_data": vs.get("synthesis_data") is not None,
            "has_raw_pdf_url": bool(vs.get("raw_pdf_url")),
            "raw_pdf_url": vs.get("raw_pdf_url"),
        }
        print(json.dumps(vs_summary, indent=2, ensure_ascii=False, default=str))

    # --- Krok 3: czy ten vehicle_id ma inne kalkulacje ---
    siblings_res = (
        client.table("ltr_kalkulacje")
        .select("id, numer_kalkulacji, status, created_at")
        .eq("stan_json->>vehicle_id", vehicle_id)
        .order("created_at")
        .execute()
    )
    siblings = siblings_res.data or []
    print(f"\n[KROK 3] Inne kalkulacje dla vehicle_id={vehicle_id}: {len(siblings)}")
    for s in siblings:
        print(f"  - {s.get('numer_kalkulacji')} (status={s.get('status')}, created_at={s.get('created_at')})")

    # --- Wniosek ---
    print("\n=== WNIOSEK ===")
    if not vs_rows:
        if len(siblings) == 1:
            print("Scenariusz #1 (lub #3): vehicle_synthesis NIE ISTNIEJE.")
            print("Ta kalkulacja jest jedyna dla tego vehicle_id — najpewniej utworzona recznie")
            print("przez /api/kalkulacje/manual, bez uprzedniej ekstrakcji PDF.")
            print("ALBO: vehicle_synthesis kiedys istnial i zostal usuniety (osierocenie).")
        else:
            print("Scenariusz #3 (osierocenie): vehicle_synthesis NIE ISTNIEJE,")
            print(f"ale istnieje {len(siblings)} kalkulacji wskazujacych na ten sam vehicle_id.")
            print("Sugeruje to, ze rekord vehicle_synthesis byl, ale zostal usuniety.")
    elif vs_status == "completed":
        print("Scenariusz NEUTRALNY: vehicle_synthesis ISTNIEJE w statusie 'completed'.")
        print("Technicznie powiazanie jest. Pytanie wymaga doprecyzowania —")
        print("byc moze problem jest w UI/froncie, ktory tego nie wyswietla.")
    else:
        print(f"Scenariusz #2: vehicle_synthesis ISTNIEJE, ale verification_status = '{vs_status}'.")
        print("Pipeline ekstrakcji przerwal sie przed ukonczeniem. Rekord istnieje,")
        print("ale brak mu kompletnego synthesis_data (lub jest niepelny).")
        print("Dalej: przeczytac pole 'notes' powyzej + logi [BG TASK] z tego okresu.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
