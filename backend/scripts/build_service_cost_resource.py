"""Build technical-cost (service) resource from PowerBI fleet data.

Reads the PowerBI pivot export, computes class-level median service rates
(PLN/km) for ASO and non-ASO, plus brand/fuel multipliers, and writes:

1. Google Sheets:
   - gid=1269082755 `samar_class_service_rates` (matrix Klasa SAMAR x przebieg)
   - gid=972056274 `service_rates_config` (multipliers brand/fuel; drive/gearbox preserved)
2. `backend/serwis_baza.csv` (single source of truth for migrations)
3. `output/service_rates_proposal.csv` + `output/multipliers_proposal.csv` (CSV backup)
4. `output/validation_report.json` (coverage, unmapped codes, legacy diff)
5. `output/legacy_diff_top20.csv` (top-20 model deltas vs TabelaSerwisowa)

Class mapping is loaded at runtime from gid=802400199 (`samar_classes`).

Usage:
    python -m scripts.build_service_cost_resource "C:/path/to/data (12).xlsx" \\
        --write-gsheet \\
        [--legacy-xlsx "C:/path/to/TabelaSerwisowa.xlsx"]

KINTO rows are filtered out (Toyota subscription, non-representative).
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.mdm_sync import _get_gspread_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
GID_SAMAR_CLASSES = 802400199
GID_SERVICE_RATES = 1269082755
GID_MULTIPLIERS = 972056274

MILEAGE_BANDS = [30000, 60000, 90000, 120000, 150000, 180000, 210000, 245000]
MIN_SAMPLE_CELL = 20
MIN_SAMPLE_CLASS = 50
MIN_SAMPLE_MULTIPLIER = 30

FUEL_NAME_MAP = {
    "PB": "Benzyna (PB)",
    "ON": "Diesel (ON)",
    "Mild Hybrid": "Benzyna mHEV (PB-mHEV)",
    "Hybrydowy": "Hybryda (HEV)",
    "Hybrydowy-Plug-in": "Plug-in Hybrid (PHEV)",
    "Elektryczny": "Elektryczny (BEV)",
    "PB/LPG": "LPG",
}


def load_class_mapping(gc) -> dict[str, list[str]]:
    """Read samar_classes sheet → {rental_code_upper: [samar_name, ...]}.

    Rental codes are comma-separated in source (e.g. 'P, PBF, PCh'); each
    expands to one entry. A single rental code may map to multiple SAMAR
    classes (e.g. 'B' → 4 classes incl. SUV, Sport, Vany).
    """
    ws = gc.open_by_key(SPREADSHEET_ID).get_worksheet_by_id(GID_SAMAR_CLASSES)
    rows = ws.get_all_values()
    mapping: dict[str, list[str]] = defaultdict(list)
    for row in rows[1:]:
        if len(row) < 3 or not row[1].strip():
            continue
        samar_name = row[1].strip()
        rental_codes = row[2].strip()
        if not rental_codes:
            continue
        for code in rental_codes.split(","):
            code_u = code.strip().upper()
            if code_u and samar_name not in mapping[code_u]:
                mapping[code_u].append(samar_name)
    return dict(mapping)


def expand_fleet_code(klasa: str, mapping: dict[str, list[str]]) -> list[str]:
    """Map a PowerBI Klasa code to a list of SAMAR class names.

    Handles variants:
      * exact match
      * '+' suffix (D+ → D)
      * 'LPG'/'CH' suffix (Blpg → B, MvCh → Mv)
      * 'SUV' → all 'Terenowo-rekreacyjne (SUV)' classes
      * case variants (Mvan vs MVAN, Tpick-up vs T-Pickup)
    """
    if not klasa:
        return []
    cu = klasa.strip().upper()
    if cu in mapping:
        return mapping[cu]
    while cu.endswith("+") and len(cu) > 1:
        cu = cu[:-1]
        if cu in mapping:
            return mapping[cu]
    for suffix in ("LPG", "CH"):
        if cu.endswith(suffix) and len(cu) > len(suffix):
            base = cu[: -len(suffix)]
            if base in mapping:
                return mapping[base]
            if base.endswith("V") and base + "AN" in mapping:
                return mapping[base + "AN"]
    if cu == "SUV":
        result = []
        for codes_list in mapping.values():
            for name in codes_list:
                if "(SUV)" in name and name not in result:
                    result.append(name)
        return result
    if cu in ("TPICK-UP", "TPICKUP"):
        return mapping.get("T-PICKUP", [])
    if cu.startswith("P") and 2 <= len(cu) <= 3 and cu not in mapping:
        return mapping.get("P", [])
    return []


def read_powerbi_leaves(xlsx_path: str):
    """Yield leaf rows from the PowerBI pivot.

    Each leaf row (with plate at col 9) has all 10 hierarchy columns filled
    in directly. Subtotal rows have 'Total' somewhere mid-hierarchy and are
    skipped. Cols 0-9 = mileage_cat, age_cat, sold, klasa, cost_type, fuel,
    marka, model, model_v, plate. Cost cols: 13 = mech_per_km, 16 = mech_per_day.
    Lifetime mileage at col 20, age days at col 21.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb.active
    for r in ws.iter_rows(min_row=2, values_only=True):
        padded = r + (None,) * max(0, 25 - len(r))
        if padded[9] is None or padded[9] == "Total":
            continue
        if any(padded[i] == "Total" for i in range(10)):
            continue
        yield {
            "klasa": _val_or_none(padded[3]),
            "cost_type": _val_or_none(padded[4]),
            "fuel": _val_or_none(padded[5]),
            "marka": _val_or_none(padded[6]),
            "model": _val_or_none(padded[7]),
            "mileage_cat": _val_or_none(padded[0]),
            "age_cat": _val_or_none(padded[1]),
            "mech_per_km": padded[13],
            "mech_per_day": padded[16],
            "lifetime_km": padded[20],
            "age_days": padded[21],
        }
    wb.close()


def _val_or_none(v):
    return None if v in (None, "Total", "") else v


def get_neighbor_class(samar_name: str, all_classes: list[str]) -> str | None:
    """Step one letter UP within the same category. A→B, B→C, ..., F→G.

    Used as cross-class fallback when current class has insufficient data.
    Returns None for classes without a size letter (Autobusy, Lekkie VAN, etc.).
    """
    if " - " not in samar_name:
        return None
    category, rest = samar_name.split(" - ", 1)
    if not rest or rest[0] not in "ABCDEFG":
        return None
    next_char = chr(ord(rest[0]) + 1)
    prefix = f"{category} - {next_char}"
    for cls in all_classes:
        if cls.startswith(prefix):
            return cls
    return None


def lifetime_band(km) -> int | None:
    if km is None:
        return None
    try:
        km_f = float(km)
    except (TypeError, ValueError):
        return None
    if km_f <= 0:
        return None
    for b in MILEAGE_BANDS:
        if km_f <= b:
            return b
    return MILEAGE_BANDS[-1]


def compute_base_rates(leaves, mapping):
    """Simplified: direct median PLN/km per (samar_class × band × cost_type) from PowerBI.

    No anchor, no growth factor — just raw medians. Fallback ladder:
      1. (klasa × band × ct) median if n ≥ MIN_SAMPLE_CELL
      2. (klasa × ct) median across all bands (flat for this band)
      3. derived from the other cost_type via class ASO premium floor

    ASO premium floor per class: realistic_class_median, or 1.30 if ASO would be
    cheaper than nonASO in raw data (forced 30% bump).
    """
    cell: dict = defaultdict(lambda: defaultdict(list))
    cls_all: dict = defaultdict(lambda: defaultdict(list))
    unmapped: dict[str, int] = defaultdict(int)
    total_in = total_kept = total_kinto = 0

    for row in leaves:
        total_in += 1
        if row["cost_type"] == "KINTO":
            total_kinto += 1
            continue
        if not row["klasa"] or not row["cost_type"]:
            continue
        if row["mech_per_km"] is None or float(row["mech_per_km"]) <= 0:
            continue
        band = lifetime_band(row["lifetime_km"])
        if band is None:
            continue
        samar_names = expand_fleet_code(row["klasa"], mapping)
        if not samar_names:
            unmapped[row["klasa"]] += 1
            continue
        ct = "aso" if row["cost_type"].upper() == "ASO" else "non_aso"
        mpk = float(row["mech_per_km"])
        for s in samar_names:
            cell[(s, band)][ct].append(mpk)
            cls_all[s][ct].append(mpk)
        total_kept += 1

    logger.info(
        f"PowerBI rows: total={total_in}, kept={total_kept}, kinto={total_kinto}, "
        f"unmapped={sum(unmapped.values())}"
    )

    class_aso_premium_floor: dict[str, tuple[float, str]] = {}
    for samar_name in cls_all.keys():
        aso_vals = cls_all[samar_name].get("aso", [])
        non_vals = cls_all[samar_name].get("non_aso", [])
        if len(aso_vals) >= MIN_SAMPLE_CELL and len(non_vals) >= MIN_SAMPLE_CELL:
            realistic = statistics.median(aso_vals) / statistics.median(non_vals)
            if realistic < 1.0:
                class_aso_premium_floor[samar_name] = (1.30, f"forced_30pct_(real={realistic:.2f})")
            else:
                class_aso_premium_floor[samar_name] = (realistic, "realistic_class_median")
        else:
            class_aso_premium_floor[samar_name] = (1.30, "default_low_sample")

    forced_count = sum(1 for _, src in class_aso_premium_floor.values() if "forced" in src)
    logger.info(
        f"ASO premium floor: {len(class_aso_premium_floor)} classes computed, "
        f"{forced_count} forced to 1.30 (ASO would have been cheaper in raw data)"
    )

    rates = []
    all_samar = sorted(set(cls_all.keys()))

    def resolve(samar_name, band, ct, _seen=None):
        """Cascade: band_data → class_data → neighbor_class (recursive) → low_n class."""
        if _seen is None:
            _seen = set()
        if samar_name in _seen:
            return None, 0, "cycle"
        _seen = _seen | {samar_name}
        band_vals = cell.get((samar_name, band), {}).get(ct, [])
        class_vals = cls_all.get(samar_name, {}).get(ct, [])
        if len(band_vals) >= MIN_SAMPLE_CELL:
            return statistics.median(band_vals), len(band_vals), "powerbi_band"
        if len(class_vals) >= MIN_SAMPLE_CLASS:
            return statistics.median(class_vals), len(class_vals), "fallback_class"
        neighbor = get_neighbor_class(samar_name, all_samar)
        if neighbor and neighbor != samar_name:
            n_rate, n_count, n_src = resolve(neighbor, band, ct, _seen)
            if n_rate is not None:
                short = neighbor.split(" - ")[1][:6] if " - " in neighbor else neighbor[:6]
                return n_rate, n_count, f"cross_class_{short}({n_src})"
        if class_vals:
            return statistics.median(class_vals), len(class_vals), "fallback_class_low_n"
        return None, 0, "missing"

    for samar_name in all_samar:
        required_premium, premium_src = class_aso_premium_floor.get(samar_name, (1.30, "default"))

        for band in MILEAGE_BANDS:
            non_aso_rate, n_non, src_non = resolve(samar_name, band, "non_aso")
            aso_rate, n_aso, src_aso = resolve(samar_name, band, "aso")

            if aso_rate and non_aso_rate and aso_rate < non_aso_rate * required_premium:
                aso_rate = non_aso_rate * required_premium
                src_aso += f"+floored_x{required_premium:.2f}"
            elif not aso_rate and non_aso_rate:
                aso_rate = non_aso_rate * required_premium
                src_aso = f"derived_from_nonaso_x{required_premium:.2f}"
            elif aso_rate and not non_aso_rate:
                non_aso_rate = aso_rate / required_premium
                src_non = f"derived_from_aso_/x{required_premium:.2f}"

            rates.append(
                {
                    "samar_name": samar_name,
                    "przebieg_do": band,
                    "aso_rate": aso_rate,
                    "non_aso_rate": non_aso_rate,
                    "n_aso_anchor": n_aso,
                    "n_non_anchor": n_non,
                    "growth_aso": 1.0,
                    "growth_non_aso": 1.0,
                    "aso_premium_floor": required_premium,
                    "source": (
                        f"aso={src_aso};non_aso={src_non};"
                        f"floor={required_premium:.2f}_{premium_src}"
                    ),
                }
            )

    return rates, dict(unmapped)


def pick_representative_models(leaves, mapping) -> dict[str, tuple[str, int]]:
    """For each SAMAR class, find the most common 'Marka Model' from PowerBI.

    Returns dict {samar_name: (rep_label, count)}.
    """
    by_samar: dict = defaultdict(Counter)
    for row in leaves:
        if row["cost_type"] == "KINTO" or not row["klasa"]:
            continue
        samar_names = expand_fleet_code(row["klasa"], mapping)
        if not samar_names:
            continue
        if row["marka"] and row["model"]:
            key = f"{row['marka'].strip()} {row['model'].strip()}"
            for s in samar_names:
                by_samar[s][key] += 1
    return {
        s: (counter.most_common(1)[0][0], counter.most_common(1)[0][1])
        for s, counter in by_samar.items()
        if counter
    }


def build_legacy_cost_lookup(legacy_xlsx_path: str | None) -> dict:
    """Read legacy TabelaSerwisowa → dict {(brand, model, band): {'aso': median_pln, 'nonaso': median_pln}}.

    Legacy columns: KwotaSerwisu = ASO band cost, KwotaNonASO = non-ASO band cost.
    """
    if not legacy_xlsx_path or not Path(legacy_xlsx_path).exists():
        return {}
    wb = openpyxl.load_workbook(legacy_xlsx_path, data_only=True, read_only=True)
    ws = wb.active
    raw_aso: dict = defaultdict(list)
    raw_non: dict = defaultdict(list)
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[1] is None or r[4] is None:
            continue
        try:
            mil = int(r[1])
        except (TypeError, ValueError):
            continue
        if mil <= 0:
            continue
        m = (r[4] or "").strip()
        parts = m.split(" ", 2)
        if len(parts) < 2:
            continue
        brand = parts[0].upper()
        model = parts[1].upper()
        band = next((b for b in MILEAGE_BANDS if mil <= b), MILEAGE_BANDS[-1])

        try:
            aso_cost = float(str(r[2] or "0").replace(",", "."))
        except (TypeError, ValueError):
            aso_cost = 0
        try:
            non_cost = float(str(r[3] or "0").replace(",", "."))
        except (TypeError, ValueError):
            non_cost = 0

        if aso_cost >= 50:
            raw_aso[(brand, model, band)].append(aso_cost)
        if non_cost >= 50:
            raw_non[(brand, model, band)].append(non_cost)
    wb.close()

    lookup: dict = {}
    for key, vals in raw_aso.items():
        lookup.setdefault(key, {})["aso"] = statistics.median(vals)
    for key, vals in raw_non.items():
        lookup.setdefault(key, {})["nonaso"] = statistics.median(vals)
    return lookup


def legacy_cost_for(rep_label: str, band: int, ct: str, lookup: dict) -> float | None:
    """Look up legacy BAND cost in PLN for rep model at given band, for given cost_type."""
    if not rep_label:
        return None
    parts = rep_label.upper().split(" ", 1)
    if len(parts) < 2:
        return None
    brand, model = parts[0], parts[1].split(" ")[0]
    key = (brand, model, band)
    if key in lookup and ct in lookup[key]:
        return lookup[key][ct]
    brand_band_costs = [
        v[ct] for (b, _, ba), v in lookup.items() if b == brand and ba == band and ct in v
    ]
    if brand_band_costs:
        return statistics.median(brand_band_costs)
    return None


def legacy_cumulative_for(rep_label: str, band: int, ct: str, lookup: dict) -> float | None:
    """Cumulative legacy cost up to and including this band, for given cost_type."""
    total = 0.0
    found_any = False
    for b in MILEAGE_BANDS:
        if b > band:
            break
        cost = legacy_cost_for(rep_label, b, ct, lookup)
        if cost is not None:
            total += cost
            found_any = True
    return total if found_any else None


def compute_multipliers(leaves, mapping):
    """Compute per-row relative deviation from class median, then aggregate per brand/fuel."""
    by_samar_ct: dict = defaultdict(list)
    rows_for_mult = []
    for row in leaves:
        if row["cost_type"] == "KINTO":
            continue
        if not row["klasa"] or not row["cost_type"]:
            continue
        if row["mech_per_km"] is None or float(row["mech_per_km"]) <= 0:
            continue
        samar_names = expand_fleet_code(row["klasa"], mapping)
        if not samar_names:
            continue
        ct = "aso" if row["cost_type"].upper() == "ASO" else "non_aso"
        mpk = float(row["mech_per_km"])
        for s in samar_names:
            by_samar_ct[(s, ct)].append(mpk)
        rows_for_mult.append(
            {
                "marka": (row["marka"] or "").strip().upper(),
                "fuel": (row["fuel"] or "").strip(),
                "mech": mpk,
                "samar_names": samar_names,
                "ct": ct,
            }
        )

    samar_ct_median = {k: statistics.median(v) for k, v in by_samar_ct.items() if v}

    brand_devs: dict = defaultdict(list)
    fuel_devs: dict = defaultdict(list)
    all_devs = []
    for row in rows_for_mult:
        deviations = []
        for s in row["samar_names"]:
            med = samar_ct_median.get((s, row["ct"]))
            if med and med > 0:
                deviations.append(row["mech"] / med)
        if not deviations:
            continue
        rel = statistics.median(deviations)
        all_devs.append(rel)
        if row["marka"]:
            brand_devs[row["marka"]].append(rel)
        if row["fuel"]:
            fuel_devs[row["fuel"]].append(rel)

    brand_mult = {
        b: (round(statistics.median(v), 4), len(v))
        for b, v in brand_devs.items()
        if len(v) >= MIN_SAMPLE_MULTIPLIER
    }
    fuel_mult = {
        FUEL_NAME_MAP.get(f, f): (round(statistics.median(v), 4), len(v))
        for f, v in fuel_devs.items()
        if len(v) >= MIN_SAMPLE_MULTIPLIER
    }
    global_median_dev = statistics.median(all_devs) if all_devs else None
    return {"brand": brand_mult, "fuel": fuel_mult, "global_median_deviation": global_median_dev}


def _fmt_pl(v: float | None, decimals: int = 4) -> str:
    if v is None:
        return ""
    return f"{v:.{decimals}f}".replace(".", ",")


def write_csv_outputs(rates, multipliers, reps, legacy_lookup, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    p1 = output_dir / "service_rates_proposal.csv"
    with open(p1, "w", encoding="utf-8", newline="") as f:
        f.write(
            "Klasa SAMAR (FK),przebieg_do,stawka_aso_per_km,stawka_non_aso_per_km,"
            "n_aso,n_nonaso,aso_premium_floor,representative_model,"
            "legacy_nonASO_cumul,legacy_ASO_cumul,BI_nonASO_cumul,BI_ASO_cumul,"
            "diff_nonASO_pct,diff_ASO_pct,source\n"
        )
        for r in rates:
            rep_label, _ = reps.get(r["samar_name"], ("", 0))
            band = r["przebieg_do"]
            leg_non = legacy_cumulative_for(rep_label, band, "nonaso", legacy_lookup)
            leg_aso = legacy_cumulative_for(rep_label, band, "aso", legacy_lookup)
            bi_non = r["non_aso_rate"] * band if r["non_aso_rate"] is not None else None
            bi_aso = r["aso_rate"] * band if r["aso_rate"] is not None else None
            diff_non = (
                round((bi_non - leg_non) / leg_non * 100, 1)
                if leg_non and bi_non is not None and leg_non > 0
                else None
            )
            diff_aso = (
                round((bi_aso - leg_aso) / leg_aso * 100, 1)
                if leg_aso and bi_aso is not None and leg_aso > 0
                else None
            )
            f.write(
                f'"{r["samar_name"]}",{band},'
                f'"{_fmt_pl(r["aso_rate"])}","{_fmt_pl(r["non_aso_rate"])}",'
                f'{r["n_aso_anchor"]},{r["n_non_anchor"]},'
                f'"{_fmt_pl(r["aso_premium_floor"], 2)}",'
                f'"{rep_label}",'
                f'"{_fmt_pl(leg_non, 0)}","{_fmt_pl(leg_aso, 0)}",'
                f'"{_fmt_pl(bi_non, 0)}","{_fmt_pl(bi_aso, 0)}",'
                f'"{_fmt_pl(diff_non, 1) if diff_non is not None else ""}",'
                f'"{_fmt_pl(diff_aso, 1) if diff_aso is not None else ""}",'
                f'"{r["source"]}"\n'
            )
    logger.info(f"Wrote {p1}")

    p2 = output_dir / "multipliers_proposal.csv"
    with open(p2, "w", encoding="utf-8", newline="") as f:
        f.write("layer,key,multiplier,n_sample\n")
        for b, (m, n) in sorted(multipliers.get("brand", {}).items()):
            f.write(f'brand,"{b}","{_fmt_pl(m)}",{n}\n')
        for fu, (m, n) in sorted(multipliers.get("fuel", {}).items()):
            f.write(f'fuel,"{fu}","{_fmt_pl(m)}",{n}\n')
    logger.info(f"Wrote {p2}")


def overwrite_serwis_baza_csv(rates, target_path: str):
    """Overwrite backend/serwis_baza.csv with new rates (4 cols, legacy format)."""
    with open(target_path, "w", encoding="utf-8", newline="") as f:
        f.write("Klasa SAMAR (FK),przebieg_do,stawka_aso_per_km,stawka_non_aso_per_km\n")
        for r in rates:
            aso = _fmt_pl(r["aso_rate"]) or "0"
            non_aso = _fmt_pl(r["non_aso_rate"]) or "0"
            f.write(f'"{r["samar_name"]}",{r["przebieg_do"]},"{aso}","{non_aso}"\n')
    logger.info(f"Overwrote {target_path}")


def write_validation_report(rates, multipliers, unmapped, legacy_diff, output_path: Path):
    anchor_sources: Counter = Counter()
    floored_count = 0
    premium_per_class: dict = {}
    for r in rates:
        s = r["source"]
        for tag in (
            "powerbi_30k",
            "fallback_class",
            "fallback_class_low_n",
            "missing",
            "derived_from_nonaso",
            "derived_from_aso",
        ):
            if tag in s:
                anchor_sources[tag] += 1
        if "floored" in s:
            floored_count += 1
        if r["samar_name"] not in premium_per_class:
            floor = r.get("aso_premium_floor", 1.30)
            forced = "forced" in s
            premium_per_class[r["samar_name"]] = {
                "floor": round(floor, 3),
                "forced_to_30pct": forced,
            }
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "methodology": (
            "anchor@30k_per_class + universal_growth_per_band + "
            "ASO_floor=realistic_class_median (or 1.30 if ASO_would_be_cheaper)"
        ),
        "unmapped_fleet_codes": dict(unmapped),
        "anchor_source_counts": dict(anchor_sources),
        "aso_floored_cells": floored_count,
        "aso_premium_floor_per_class": premium_per_class,
        "global_median_deviation_diagnostic": multipliers.get("global_median_deviation"),
        "brand_multiplier_count_diagnostic": len(multipliers.get("brand", {})),
        "fuel_multiplier_count_diagnostic": len(multipliers.get("fuel", {})),
        "total_rate_rows": len(rates),
        "min_sample_cell": MIN_SAMPLE_CELL,
        "legacy_diff_top20": legacy_diff,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Wrote {output_path}")


def compute_legacy_diff(rates, legacy_xlsx_path: str | None) -> list[dict]:
    """Diff new rates vs legacy TabelaSerwisowa.

    Legacy KwotaNonASO at mileage X is the cost INCURRED within the band
    leading up to X (typically 30k wide). Per-km cost in that band =
    cost / band_width. We aggregate legacy per-band-per-km medians per
    brand and compare to new rates aggregated to brand level.
    """
    if not legacy_xlsx_path or not Path(legacy_xlsx_path).exists():
        return []
    wb = openpyxl.load_workbook(legacy_xlsx_path, data_only=True, read_only=True)
    ws = wb.active
    legacy_avg: dict = defaultdict(list)
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[1] is None or r[3] is None:
            continue
        try:
            mil = int(r[1])
            cost = float(str(r[3]).replace(",", "."))
        except (TypeError, ValueError):
            continue
        if mil <= 0 or cost < 50:
            continue
        band = next((b for b in MILEAGE_BANDS if mil <= b), MILEAGE_BANDS[-1])
        band_width = 30000
        per_km = cost / band_width
        m = (r[4] or "").strip()
        if not m:
            continue
        brand = m.split(" ")[0].upper()
        legacy_avg[(brand, band)].append(per_km)
    wb.close()

    diffs = []
    for (brand, band), per_km_list in legacy_avg.items():
        if len(per_km_list) < 3:
            continue
        legacy_med = statistics.median(per_km_list)
        same_band = [r for r in rates if r["przebieg_do"] == band and r["non_aso_rate"]]
        if not same_band:
            continue
        new_avg = statistics.median([r["non_aso_rate"] for r in same_band])
        delta_pct = (new_avg - legacy_med) / legacy_med * 100 if legacy_med > 0 else 0
        diffs.append(
            {
                "brand": brand,
                "przebieg_do": band,
                "legacy_per_km": round(legacy_med, 5),
                "new_class_avg_per_km": round(new_avg, 5),
                "delta_pct": round(delta_pct, 1),
                "n_legacy": len(per_km_list),
            }
        )
    diffs.sort(key=lambda d: abs(d["delta_pct"]), reverse=True)
    return diffs[:20]


def write_to_gsheets(gc, rates, reps, legacy_lookup):
    ss = gc.open_by_key(SPREADSHEET_ID)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    ws_rates = ss.get_worksheet_by_id(GID_SERVICE_RATES)
    rows = [
        [
            "Klasa SAMAR (FK)",
            "przebieg_do",
            "stawka_aso_per_km",
            "stawka_non_aso_per_km",
            "n_aso",
            "n_nonaso",
            "aso_premium_floor",
            "last_updated",
            "representative_model",
            "legacy_nonASO_cumul",
            "legacy_ASO_cumul",
            "BI_nonASO_cumul",
            "BI_ASO_cumul",
            "diff_nonASO_pct",
            "diff_ASO_pct",
            "source",
        ]
    ]
    for r in rates:
        rep_label, _ = reps.get(r["samar_name"], ("", 0))
        band = r["przebieg_do"]
        leg_non = legacy_cumulative_for(rep_label, band, "nonaso", legacy_lookup)
        leg_aso = legacy_cumulative_for(rep_label, band, "aso", legacy_lookup)
        bi_non = r["non_aso_rate"] * band if r["non_aso_rate"] is not None else None
        bi_aso = r["aso_rate"] * band if r["aso_rate"] is not None else None
        diff_non = (
            round((bi_non - leg_non) / leg_non * 100, 1)
            if leg_non and bi_non is not None and leg_non > 0
            else None
        )
        diff_aso = (
            round((bi_aso - leg_aso) / leg_aso * 100, 1)
            if leg_aso and bi_aso is not None and leg_aso > 0
            else None
        )
        rows.append(
            [
                r["samar_name"],
                band,
                _fmt_pl(r["aso_rate"]),
                _fmt_pl(r["non_aso_rate"]),
                r["n_aso_anchor"],
                r["n_non_anchor"],
                _fmt_pl(r["aso_premium_floor"], 2),
                today,
                rep_label,
                _fmt_pl(leg_non, 0),
                _fmt_pl(leg_aso, 0),
                _fmt_pl(bi_non, 0),
                _fmt_pl(bi_aso, 0),
                _fmt_pl(diff_non, 1) if diff_non is not None else "",
                _fmt_pl(diff_aso, 1) if diff_aso is not None else "",
                r["source"],
            ]
        )
    ws_rates.clear()
    ws_rates.update(values=rows, range_name="A1", value_input_option="USER_ENTERED")
    logger.info(f"Wrote {len(rows)-1} rate rows to gid={GID_SERVICE_RATES}")

    logger.info(
        f"Skipped multipliers sheet (gid={GID_MULTIPLIERS}) by design — "
        "user policy keeps brand/fuel/drive/gearbox multipliers at 1.0 as a manual buffer"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("xlsx_path", help="Path to PowerBI fleet data XLSX")
    parser.add_argument(
        "--legacy-xlsx",
        default=r"C:\Users\proma\Downloads\TabelaSerwisowa_2026-03-13 101722.xlsx",
        help="Optional path to legacy TabelaSerwisowa XLSX for diff",
    )
    parser.add_argument("--write-gsheet", action="store_true")
    parser.add_argument("--output-dir", default=r"D:\kalk_v3\backend\output")
    parser.add_argument(
        "--no-overwrite-serwis-baza",
        action="store_true",
        help="Skip overwriting backend/serwis_baza.csv",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gc = _get_gspread_client()
    logger.info("Loading class mapping from gsheet...")
    mapping = load_class_mapping(gc)
    logger.info(f"Loaded {len(mapping)} rental codes mapping to SAMAR classes")

    logger.info(f"Reading PowerBI XLSX: {args.xlsx_path}")
    leaves = list(read_powerbi_leaves(args.xlsx_path))
    logger.info(f"Got {len(leaves)} leaf rows")

    rates, unmapped = compute_base_rates(leaves, mapping)
    multipliers = compute_multipliers(leaves, mapping)
    reps = pick_representative_models(leaves, mapping)
    legacy_lookup = build_legacy_cost_lookup(args.legacy_xlsx)
    legacy_diff = compute_legacy_diff(rates, args.legacy_xlsx)

    write_csv_outputs(rates, multipliers, reps, legacy_lookup, output_dir)
    if not args.no_overwrite_serwis_baza:
        overwrite_serwis_baza_csv(rates, r"D:\kalk_v3\backend\serwis_baza.csv")
    write_validation_report(
        rates, multipliers, unmapped, legacy_diff, output_dir / "validation_report.json"
    )

    if args.write_gsheet:
        write_to_gsheets(gc, rates, reps, legacy_lookup)
    else:
        logger.info("Skipped gsheet write (use --write-gsheet to enable)")

    logger.info("Done.")


if __name__ == "__main__":
    main()
