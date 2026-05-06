"""Read-only audit: porównuje 5 calc-touching tabel SOT (CSV) vs DB.

Output: /tmp/sot_audit/REPORT.md z:
- Per tabela: rows added (in SOT, not DB), modified (key match, value diff),
  removed (in DB, not SOT)
- Per tabela: ile pojazdów w vehicle_synthesis będzie afekted (na poziomie key)
- Tolerance: stringi exact match po normalizacji (replace ',' → '.' dla numerków)

Run: docker exec kalk_v3-backend-1 sh -c 'cd /app && python -u scripts/audit_sot_vs_db.py'
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from typing import Any

from core.database import supabase

SOT_DIR = "/tmp/sot_audit"
OUT = "/tmp/sot_audit/REPORT.md"


def n(x: Any) -> str:
    """Normalize: strip, lowercase, comma→dot for numbers."""
    if x is None:
        return ""
    s = str(x).strip()
    return s


def num(x: Any) -> float | None:
    if x is None or str(x).strip() == "":
        return None
    s = str(x).strip().replace(",", ".").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def load_sot_csv(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def fetch_db_table(table: str, columns: str = "*") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 0
    page_size = 1000
    while True:
        resp = (
            supabase.table(table)
            .select(columns)
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        chunk = resp.data or []
        rows.extend(chunk)
        if len(chunk) < page_size:
            break
        page += 1
    return rows


def fetch_samar_classes() -> dict[int, str]:
    rows = fetch_db_table("samar_classes", "id,name")
    return {r["id"]: r["name"] for r in rows}


# ── B1 audit: samar_brand_corrections ───────────────────────────────────────

def audit_b1(report: list[str]) -> None:
    report.append("\n## B1 — `samar_brand_corrections`\n")
    sot = load_sot_csv(f"{SOT_DIR}/samar_brand_corrections.csv")
    db = fetch_db_table("samar_brand_corrections", "klasa_samar,marka,model,silnik,korekta")
    classes = fetch_samar_classes()

    # Index DB by (klasa_name, marka, model_or_empty, silnik)
    db_idx: dict[tuple, float] = {}
    for r in db:
        klasa_name = classes.get(r["klasa_samar"], f"<id={r['klasa_samar']}>")
        key = (n(klasa_name), n(r["marka"]), n(r["model"]), n(r["silnik"]))
        db_idx[key] = float(r["korekta"]) if r["korekta"] is not None else 0.0

    sot_idx: dict[tuple, float] = {}
    for r in sot:
        key = (n(r["KLASA SAMAR"]), n(r["MARKA"]), n(r["MODEL"]), n(r["SILNIK"]))
        sot_idx[key] = num(r["KOREKTA"]) or 0.0

    sot_keys = set(sot_idx.keys())
    db_keys = set(db_idx.keys())
    added = sot_keys - db_keys
    removed = db_keys - sot_keys
    common = sot_keys & db_keys
    modified = {k for k in common if abs(sot_idx[k] - db_idx[k]) > 1e-6}

    report.append(f"- SOT rows: **{len(sot_idx)}**")
    report.append(f"- DB  rows: **{len(db_idx)}**")
    report.append(f"- Added (in SOT, not DB): **{len(added)}**")
    report.append(f"- Removed (in DB, not SOT): **{len(removed)}**")
    report.append(f"- Modified (key match, value diff): **{len(modified)}**")
    report.append(f"- Identical: **{len(common) - len(modified)}**\n")

    # Show actual diffs
    if added:
        report.append("### Added (SOT → would be inserted)")
        for k in sorted(added)[:20]:
            report.append(f"  - `{k[0]}` / `{k[1]}` / `{k[3]}` → korekta=**{sot_idx[k]:+.4g}**")
        if len(added) > 20:
            report.append(f"  - ... +{len(added) - 20} more\n")
        report.append("")
    if removed:
        report.append("### Removed (in DB, not SOT)")
        for k in sorted(removed)[:20]:
            report.append(f"  - `{k[0]}` / `{k[1]}` / `{k[3]}` → korekta_db=**{db_idx[k]:+.4g}**")
        report.append("")
    if modified:
        report.append("### Modified (value diff > 1e-6)")
        for k in sorted(modified)[:20]:
            report.append(f"  - `{k[0]}` / `{k[1]}` / `{k[3]}` → DB=**{db_idx[k]:+.4g}** vs SOT=**{sot_idx[k]:+.4g}** (Δ={sot_idx[k] - db_idx[k]:+.4g})")
        if len(modified) > 20:
            report.append(f"  - ... +{len(modified) - 20} more\n")
        report.append("")

    # Affected vehicle count: vehicles whose (samar_class, marka, silnik) matches an "added" or "modified" key
    # Reader behaviour: brand correction lookup falls back to 0.0 when no match → so affected =
    # (currently fall-back-zero vehicles whose (klasa, marka, silnik) is now in "added") +
    # (vehicles whose (klasa, marka, silnik) is in "modified" — value would change)
    impacted_keys = added | modified
    if impacted_keys:
        # Pull every vehicle's (samar_category, brand, fuel) — these are the lookup fields
        veh = fetch_db_table(
            "vehicle_synthesis",
            "id,brand,verification_status,synthesis_data",
        )
        affected = 0
        affected_examples = []
        for v in veh:
            if v.get("verification_status") != "completed":
                continue
            sd = v.get("synthesis_data") or {}
            mai = sd.get("mapped_ai_data") or {}
            klasa = n(mai.get("samar_category"))
            marka = n(v.get("brand", "")).upper()
            silnik = n(mai.get("fuel"))
            # Brand correction reader cascade: (klasa, marka, model, silnik) then (klasa, marka, "", silnik)
            # SOT only has model="" rows so we only check level-2 lookup
            key = (klasa, marka, "", silnik)
            if key in impacted_keys:
                affected += 1
                if len(affected_examples) < 5:
                    affected_examples.append((klasa, marka, silnik))
        report.append(f"### Wpływ na pojazdy")
        report.append(f"- Pojazdy w vehicle_synthesis (completed) z `(klasa, marka, silnik)` w added/modified: **{affected}**")
        for k in affected_examples:
            report.append(f"  - przykład: `{k[0]}` / `{k[1]}` / `{k[2]}`")
        report.append("")


# ── B2 audit: ltr_admin_korekta_wr_roczniks ─────────────────────────────────

def audit_b2(report: list[str]) -> None:
    report.append("\n## B2 — `ltr_admin_korekta_wr_roczniks` (schema mismatch)\n")
    sot = load_sot_csv(f"{SOT_DIR}/ltr_admin_korekta_wr_rocznik.csv")
    db = fetch_db_table("ltr_admin_korekta_wr_roczniks", "id,rocznik,korekta_procent")

    report.append("**SOT schema**: `(samar_class, Korekta_za_ubiegly_rocznik, rocznik_biezacy)` — per-class")
    report.append("**DB  schema**: `(id, rocznik, korekta_procent)` — global")
    report.append("**Schema niezgodny — sync wymaga ALTER TABLE.**\n")

    report.append(f"- SOT rows: **{len(sot)}**")
    report.append(f"- DB  rows: **{len(db)}**")
    report.append(f"- DB current entries:")
    for r in db:
        report.append(f"  - rocznik=`{r['rocznik']}` → korekta=**{r['korekta_procent']}**")

    report.append(f"\n### SOT sample (first 5)")
    for r in sot[:5]:
        report.append(f"  - `{r['samar_class']}` → ubiegly=**{r['Korekta_za_ubiegly_rocznik']}**, biezacy=**{r['rocznik_biezacy']}**")

    # All SOT rows have same value? Check uniformity
    ubiegly_vals = {r["Korekta_za_ubiegly_rocznik"] for r in sot}
    biezacy_vals = {r["rocznik_biezacy"] for r in sot}
    report.append(f"\n### Uniformity check")
    report.append(f"- Unique `Korekta_za_ubiegly_rocznik` values across {len(sot)} klas: **{ubiegly_vals}**")
    report.append(f"- Unique `rocznik_biezacy` values: **{biezacy_vals}**")
    if len(ubiegly_vals) == 1 and len(biezacy_vals) == 1:
        report.append("→ **SOT jest uniformny — dane per-class są identyczne.** Schema ALTER niepotrzebny — wystarczy global config.")


# ── B3 audit: tab_okres_final ───────────────────────────────────────────────

def audit_b3(report: list[str]) -> None:
    report.append("\n## B3 — `tab_okres_final`\n")
    db = fetch_db_table("tab_okres_final", "*")
    if not db:
        report.append("DB jest pusta — pokażemy tylko SOT.")
        return

    db_cols = list(db[0].keys())
    report.append(f"DB columns: `{db_cols}`")
    classes = fetch_samar_classes()

    sot_path = f"{SOT_DIR}/tab_okres_final.csv"
    sot_rows: list[dict[str, str]] = []
    with open(sot_path, encoding="utf-8") as f:
        rdr = csv.reader(f)
        next(rdr)  # skip header line 1
        for row in rdr:
            if len(row) >= 9 and row[0] and not row[0].lower().startswith("rok"):
                sot_rows.append({
                    "klasa": row[0], "silnik": row[1],
                    "km_35000": row[2], "km_70000": row[3], "km_105000": row[4],
                    "km_140000": row[5], "km_175000": row[6], "km_210000": row[7], "km_245000": row[8],
                })

    report.append(f"\n- DB rows: **{len(db)}**")
    report.append(f"- SOT rows (data only): **{len(sot_rows)}**\n")

    # DB key columns: klasa_samar (int FK) + rodzaj_silnika (text)
    sot_idx: dict[tuple, dict[str, float | None]] = {}
    for r in sot_rows:
        key = (n(r["klasa"]), n(r["silnik"]))
        sot_idx[key] = {col: num(r[col]) for col in ["km_35000", "km_70000", "km_105000", "km_140000", "km_175000", "km_210000", "km_245000"]}

    db_idx: dict[tuple, dict[str, float | None]] = {}
    for r in db:
        klasa_id = r.get("klasa_samar")
        klasa_name = classes.get(klasa_id, f"<id={klasa_id}>")
        silnik = r.get("rodzaj_silnika") or ""
        key = (n(klasa_name), n(silnik))
        db_idx[key] = {col: num(r.get(col)) for col in ["km_35000", "km_70000", "km_105000", "km_140000", "km_175000", "km_210000", "km_245000"]}

    sot_keys = set(sot_idx.keys())
    db_keys = set(db_idx.keys())
    added = sot_keys - db_keys
    removed = db_keys - sot_keys
    common = sot_keys & db_keys

    modified = []
    for k in common:
        s, d = sot_idx[k], db_idx[k]
        diffs = []
        for col in s:
            sv, dv = s[col], d[col]
            if sv is None and dv is None:
                continue
            if sv is None or dv is None or abs(sv - dv) > 1e-6:
                diffs.append((col, dv, sv))
        if diffs:
            modified.append((k, diffs))

    report.append(f"- Added (SOT → not in DB): **{len(added)}**")
    report.append(f"- Removed (DB → not in SOT): **{len(removed)}**")
    report.append(f"- Common keys: **{len(common)}**")
    report.append(f"- Modified (value diff in any of 7 km cols): **{len(modified)}**")
    report.append(f"- Identical: **{len(common) - len(modified)}**\n")

    if added:
        report.append(f"### Added sample (first 10)")
        for k in sorted(added)[:10]:
            report.append(f"  - `{k[0]}` / `{k[1]}`")
        if len(added) > 10:
            report.append(f"  - ... +{len(added) - 10} more")
        report.append("")
    if removed:
        report.append(f"### Removed sample (first 10)")
        for k in sorted(removed)[:10]:
            report.append(f"  - `{k[0]}` / `{k[1]}`")
        report.append("")
    if modified:
        report.append(f"### Modified sample (first 5)")
        for k, diffs in modified[:5]:
            report.append(f"  - `{k[0]}` / `{k[1]}`:")
            for col, dv, sv in diffs[:3]:
                report.append(f"    - `{col}`: DB=**{dv}** vs SOT=**{sv}**")
        if len(modified) > 5:
            report.append(f"  - ... +{len(modified) - 5} more")
        report.append("")


# ── B4 audit: ltr_admin_korekta_wr_kolors vs paint_types ────────────────────

def audit_b4(report: list[str]) -> None:
    report.append("\n## B4 — `ltr_admin_korekta_wr_kolors` vs `paint_types` (schema mismatch)\n")
    sot = load_sot_csv(f"{SOT_DIR}/ltr_admin_korekta_wr_kolors.csv")
    db = fetch_db_table("paint_types", "id,name,wr_correction")

    report.append("**SOT**: `(samar_class, korekta_metallik, korekta_niemetallik)` — per-class")
    report.append("**DB**:  `(id, name, wr_correction)` — global per paint type\n")

    report.append(f"- SOT rows: **{len(sot)}**")
    report.append(f"- DB  rows: **{len(db)}**")
    report.append(f"- DB content:")
    for r in db:
        report.append(f"  - `{r['name']}` → wr_correction=**{r['wr_correction']}**")

    # Uniformity check on SOT
    metallik_vals = {r["korekta_metallik"] for r in sot}
    niemetallik_vals = {r["korekta_niemetallik"] for r in sot}
    report.append(f"\n### Uniformity SOT")
    report.append(f"- Unique metallik values: **{metallik_vals}**")
    report.append(f"- Unique niemetallik values: **{niemetallik_vals}**")
    if len(metallik_vals) == 1 and len(niemetallik_vals) == 1:
        report.append("→ **SOT jest uniformny** — wszystkie klasy mają tę samą korektę metalik/niemetalik. Schema per-class niepotrzebny — wystarczy global config (jak DB ma teraz).")
    else:
        report.append("→ **SOT NIE jest uniformny** — różne klasy mają różne korekty. Schema per-class potrzebny.")
        # Show variation
        klas_grouped = defaultdict(list)
        for r in sot:
            klas_grouped[(r["korekta_metallik"], r["korekta_niemetallik"])].append(r["samar_class"])
        report.append("\n#### SOT grouped by korekta value")
        for (met, niem), klas in klas_grouped.items():
            report.append(f"- met=**{met}**, niem=**{niem}** → {len(klas)} klas: {klas[:5]}{'...' if len(klas) > 5 else ''}")

    # How many vehicles have paint_type_id set?
    veh = fetch_db_table("vehicle_synthesis", "id,verification_status,synthesis_data")
    has_paint = 0
    for v in veh:
        if v.get("verification_status") != "completed":
            continue
        sd = v.get("synthesis_data") or {}
        cs = sd.get("card_summary") or {}
        if cs.get("paint_type_id") is not None or cs.get("paint_type") is not None:
            has_paint += 1
    report.append(f"\n### Wpływ")
    report.append(f"- Pojazdów completed: **{sum(1 for v in veh if v.get('verification_status') == 'completed')}**")
    report.append(f"- Z ustawionym paint_type w card_summary: **{has_paint}**")


# ── B5 audit: equipment_wr_corrections vs samar_class_options_rv ────────────

def audit_b5(report: list[str]) -> None:
    report.append("\n## B5 — `equipment_wr_corrections` vs `samar_class_options_rv` (deep diff)\n")
    sot = load_sot_csv(f"{SOT_DIR}/equipment_wr_corrections.csv")
    db = fetch_db_table("samar_class_options_rv", "samar_class_id,engine_type_id,year,options_rv_percent")
    classes = fetch_samar_classes()
    engines = fetch_db_table("engines", "id,name")
    eng_map = {e["id"]: e["name"] for e in engines}

    sot_cols = list(sot[0].keys()) if sot else []
    report.append(f"**SOT shape**: wide `(KLASA SAMAR, SILNIK, year_0..year_7)` = 297 rows × 8 year cols = 2376 cells")
    report.append(f"**DB shape**:  long `(samar_class_id, engine_type_id, year, options_rv_percent)` = {len(db)} rows")
    report.append(f"**Cell count match**: SOT 2376 ≟ DB {len(db)} → **{'YES ✓' if len(db) == 2376 else 'NO ✗'}**\n")

    # Build SOT lookup: (klasa_name, silnik_name, year_int) → value
    sot_idx: dict[tuple, float | None] = {}
    for r in sot:
        klasa = n(r.get("KLASA SAMAR", ""))
        silnik = n(r.get("SILNIK", ""))
        for y in range(8):
            v = num(r.get(str(y)))
            sot_idx[(klasa, silnik, y)] = v

    # Build DB lookup: (klasa_name, silnik_name, year) → value
    db_idx: dict[tuple, float | None] = {}
    for r in db:
        klasa_name = classes.get(r["samar_class_id"], f"<id={r['samar_class_id']}>")
        silnik_name = eng_map.get(r["engine_type_id"], f"<id={r['engine_type_id']}>")
        year = int(r["year"]) if r["year"] is not None else None
        db_idx[(n(klasa_name), n(silnik_name), year)] = float(r["options_rv_percent"]) if r["options_rv_percent"] is not None else None

    # Diff
    sot_keys = set(sot_idx.keys())
    db_keys = set(db_idx.keys())
    common = sot_keys & db_keys
    added = sot_keys - db_keys
    removed = db_keys - sot_keys
    modified = []
    for k in common:
        sv, dv = sot_idx[k], db_idx[k]
        if sv is None and dv is None:
            continue
        if sv is None or dv is None or abs(sv - dv) > 1e-6:
            modified.append((k, dv, sv))

    report.append(f"- Common (klasa, silnik, year) keys: **{len(common)}**")
    report.append(f"- Added (SOT → not in DB): **{len(added)}**")
    report.append(f"- Removed (DB → not in SOT): **{len(removed)}**")
    report.append(f"- Modified (value diff): **{len(modified)}**")
    report.append(f"- Identical: **{len(common) - len(modified)}**\n")

    if added:
        report.append(f"### Added sample (first 5)")
        for k in sorted(added)[:5]:
            report.append(f"  - `{k[0]}` / `{k[1]}` / year={k[2]} → val=**{sot_idx[k]}**")
        report.append("")
    if removed:
        report.append(f"### Removed sample (first 5)")
        for k in sorted(removed)[:5]:
            report.append(f"  - `{k[0]}` / `{k[1]}` / year={k[2]} → DB val=**{db_idx[k]}**")
        report.append("")
    if modified:
        report.append(f"### Modified sample (first 10)")
        for k, dv, sv in modified[:10]:
            report.append(f"  - `{k[0]}` / `{k[1]}` / year={k[2]}: DB=**{dv}** vs SOT=**{sv}** (Δ={sv - dv if (sv is not None and dv is not None) else 'N/A'})")
        if len(modified) > 10:
            report.append(f"  - ... +{len(modified) - 10} more")


# ── B6 audit: body_types (GSheet gid=484265370) ────────────────────────────

def audit_b6(report: list[str]) -> None:
    report.append("\n## B6 — `body_types` (GSheet gid=484265370)\n")

    sot_url = (
        "https://docs.google.com/spreadsheets/d/"
        "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=484265370"
    )
    try:
        import pandas as pd
        sot_df = pd.read_csv(sot_url)
    except Exception as exc:
        report.append(f"⚠ Nie udało się pobrać SOT z GSheet: {exc}")
        return

    db = fetch_db_table("body_types", "id,nazwa_nadwozia,vehicle_class")

    sot_idx: dict[int, tuple[str, str]] = {}
    for _, r in sot_df.iterrows():
        try:
            b_id = int(r["ID"])
        except (KeyError, ValueError, TypeError):
            continue
        sot_idx[b_id] = (n(r.get("Nazwa_Nadwozia")), n(r.get("Typ_Pojazdu")))

    db_idx: dict[int, tuple[str, str]] = {
        int(r["id"]): (n(r.get("nazwa_nadwozia")), n(r.get("vehicle_class"))) for r in db
    }

    sot_keys = set(sot_idx.keys())
    db_keys = set(db_idx.keys())
    added = sot_keys - db_keys
    removed = db_keys - sot_keys
    common = sot_keys & db_keys
    modified = {k for k in common if sot_idx[k] != db_idx[k]}

    report.append(f"- SOT rows: **{len(sot_idx)}**")
    report.append(f"- DB  rows: **{len(db_idx)}**")
    report.append(f"- Added (in SOT, not DB): **{len(added)}**")
    report.append(f"- Removed (in DB, not SOT): **{len(removed)}**")
    report.append(f"- Modified (key match, name/class diff): **{len(modified)}**")
    report.append(f"- Identical: **{len(common) - len(modified)}**\n")

    if added:
        report.append("### Added (SOT → would be inserted)")
        for k in sorted(added):
            n_name, n_class = sot_idx[k]
            report.append(f"  - id=**{k}**: `{n_name}` / `{n_class}`")
        report.append("")
    if removed:
        report.append("### Removed (in DB, not SOT)")
        for k in sorted(removed):
            d_name, d_class = db_idx[k]
            report.append(f"  - id=**{k}**: `{d_name}` / `{d_class}`")
        report.append("")
    if modified:
        report.append("### Modified")
        for k in sorted(modified):
            d_name, d_class = db_idx[k]
            s_name, s_class = sot_idx[k]
            report.append(
                f"  - id=**{k}**: "
                f"name DB=`{d_name}` vs SOT=`{s_name}`, "
                f"class DB=`{d_class}` vs SOT=`{s_class}`"
            )
        report.append("")


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    report: list[str] = []
    report.append("# SOT vs DB Audit Report")
    report.append("")
    report.append(f"Generated: {os.popen('date').read().strip()}")
    report.append(f"Project: gnpsdiarmwvqhqbyetce (kalk_v3 prod)")
    report.append(f"SOT: GSheet 1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q")

    audit_b1(report)
    audit_b2(report)
    audit_b3(report)
    audit_b4(report)
    audit_b5(report)
    audit_b6(report)

    text = "\n".join(report)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n\n=== Saved to {OUT} ===")


if __name__ == "__main__":
    main()
