"""Recalibrate `samar_class_service_rates` from qBI lifetime-per-VIN nonASO export.

Differences from `build_service_cost_resource.py`:
- Input is per-VIN aggregate (one row per vehicle, lifetime totals), not per-event rows.
- Input contains ONLY nonASO data (no ASO column).
- ASO column is derived as `nonASO * --aso-premium` (default 1.30).
- Multipliers computed as DIAGNOSTIC CSV ONLY per existing policy
  (memory: `feedback_service_multipliers_neutral.md` — multipliers stay at 1.0 in
  production; differentiation lives in base rates per Klasa SAMAR x prog km).
- Drive/gearbox parsed from BI `Model (pełny BI)` string (no dedicated columns).

Methodology caveat (logged into validation_report.json):
- BI `Koszt techn./km` is a lifetime average (total cost / total km on that VIN).
- A 100k-km vehicle in band 120k reports its cumulative-up-to-now PLN/km — NOT the
  marginal cost of segment 90k→120k. Runtime calculator treats these rates as
  marginal per segment. Lower bands underestimate marginal cost, upper bands
  overestimate it. Same assumption as in build_service_cost_resource.py; not a
  regression. Fix would require raw cost-event records (not in this export).

Usage:
    poetry run python -m scripts.recalibrate_service_from_lifetime_nonaso \\
        "C:/Users/proma/Downloads/lista_pojazdow_nonaso_lifetime.xlsx"
    # Dry-run by default — writes proposal/diff/report files only.
    # Add --apply to overwrite backend/serwis_baza.csv and run import_serwis_baza.
    # Add --no-import-supabase to skip the import (write CSV only).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.build_service_cost_resource import (  # noqa: E402
    MILEAGE_BANDS,
    MIN_SAMPLE_CELL,
    MIN_SAMPLE_CLASS,
    MIN_SAMPLE_MULTIPLIER,
    _fmt_pl,
    expand_fleet_code,
    get_neighbor_class,
    lifetime_band,
    load_class_mapping,
    overwrite_serwis_baza_csv,
)
from scripts.mdm_sync import _get_gspread_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SERWIS_BAZA = Path(__file__).resolve().parent.parent / "serwis_baza.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

VALID_STATES = {"Operacyjny", "Wycofany", "Zutylizowany"}
SANITY_MEDIAN_RANGE = (0.02, 0.10)
OUTLIER_REL_RANGE = (0.1, 5.0)

DRIVE_RE_AWD = re.compile(r"\b4x4\b", re.IGNORECASE)
DRIVE_RE_FWD = re.compile(r"\b(?:2x4|4x2)\b", re.IGNORECASE)
GEARBOX_RE_AT = re.compile(
    r"\b(?:AT|DCT|DSG|S[- ]?TRONIC|AUT(?:OMAT)?|MULTITRONIC|TIPTRONIC|EAT|CVT)\b",
    re.IGNORECASE,
)
GEARBOX_RE_MT = re.compile(r"\b(?:MT|MAN(?:UAL)?)\b", re.IGNORECASE)

FUEL_NORM = {
    "Benzyna": "BENZYNA (PB)",
    "Diesel": "DIESEL (ON)",
    "Mild Hybrid": "BENZYNA MHEV (PB-MHEV)",
    "Hybryda": "HYBRYDA (HEV)",
    "PHEV": "PLUG-IN HYBRID (PHEV)",
    "BEV": "ELEKTRYCZNY (BEV)",
    "Benzyna+LPG": "LPG",
}

XLSX_COL_PRZEBIEG = "Przebieg (km)"
XLSX_COL_STAN = "Stan"
XLSX_COL_KLASA = "Klasa"
XLSX_COL_MARKA = "Marka"
XLSX_COL_MODEL_BI = "Model (pełny BI)"
XLSX_COL_PALIWO_ZNACZNIK = "Paliwo (znacznik)"
XLSX_COL_PALIWO_SZCZEGOL = "Paliwo (szczegół)"
XLSX_COL_COST_PER_KM = "Koszt techn. / km (PLN)"
XLSX_COL_COST_TOTAL = "Koszt techniczny TOTAL (PLN)"
XLSX_COL_ZDARZEN_TECH = "Zdarzeń tech."
XLSX_COL_VIN = "VIN"


def parse_drive_gearbox(model_bi: str | None) -> tuple[str | None, str | None]:
    """Extract drive ('AWD'/'FWD') and gearbox ('AUTOMATYCZNA'/'MANUALNA') from BI text.

    Returns (None, None) for unparseable / missing tokens — NOT defaulted.
    """
    if not model_bi:
        return None, None
    s = str(model_bi)
    drive = "AWD" if DRIVE_RE_AWD.search(s) else ("FWD" if DRIVE_RE_FWD.search(s) else None)
    if GEARBOX_RE_AT.search(s):
        gearbox = "AUTOMATYCZNA"
    elif GEARBOX_RE_MT.search(s):
        gearbox = "MANUALNA"
    else:
        gearbox = None
    return drive, gearbox


def normalize_fuel(paliwo_znacznik: str | None, paliwo_szczegol: str | None) -> str | None:
    """Map BI fuel tag → canonical name used in samar_service_fuel_multipliers.

    `Paliwo (znacznik)` (curated) takes priority over `Paliwo (szczegół)` (raw).
    """
    znacznik = (paliwo_znacznik or "").strip()
    if znacznik in FUEL_NORM:
        return FUEL_NORM[znacznik]
    szczegol = (paliwo_szczegol or "").strip()
    if "Plug" in szczegol or "PHEV" in szczegol:
        return FUEL_NORM["PHEV"]
    if "Hybrydowy" in szczegol and "Plug" not in szczegol:
        return FUEL_NORM["Hybryda"]
    if "Mild" in szczegol or "mHEV" in szczegol:
        return FUEL_NORM["Mild Hybrid"]
    if "Elektryczny" in szczegol:
        return FUEL_NORM["BEV"]
    if "LPG" in szczegol or szczegol == "PB/LPG":
        return FUEL_NORM["Benzyna+LPG"]
    if szczegol == "PB":
        return FUEL_NORM["Benzyna"]
    if szczegol == "ON":
        return FUEL_NORM["Diesel"]
    return None


def read_lifetime_xlsx(path: str, sheet: str, min_km: int) -> list[dict]:
    """Read qBI lifetime export, filter, return list of vehicle dicts."""
    logger.info(f"Reading {path} sheet='{sheet}'")
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    n_total = len(df)

    df = df[df[XLSX_COL_PRZEBIEG].notna() & (df[XLSX_COL_PRZEBIEG] >= min_km)]
    df = df[df[XLSX_COL_ZDARZEN_TECH].fillna(0) >= 1]
    df = df[df[XLSX_COL_STAN].isin(VALID_STATES)]
    df = df[df[XLSX_COL_COST_PER_KM].notna() & (df[XLSX_COL_COST_PER_KM] > 0)]

    median_cost = float(df[XLSX_COL_COST_PER_KM].median())
    if not (SANITY_MEDIAN_RANGE[0] <= median_cost <= SANITY_MEDIAN_RANGE[1]):
        msg = (
            f"Sanity check failed: median Koszt techn./km = {median_cost:.4f} "
            f"outside expected range {SANITY_MEDIAN_RANGE}. "
            f"Possible column swap with 'Koszt wsz./km' (~0.17). Aborting."
        )
        raise ValueError(msg)
    logger.info(
        f"Sanity OK: median Koszt techn./km = {median_cost:.4f} "
        f"(expected ~0.04-0.06)"
    )

    vehicles = []
    for _, row in df.iterrows():
        drive, gearbox = parse_drive_gearbox(row.get(XLSX_COL_MODEL_BI))
        vehicles.append(
            {
                "vin": str(row.get(XLSX_COL_VIN, "")).strip(),
                "klasa": str(row[XLSX_COL_KLASA]).strip() if pd.notna(row[XLSX_COL_KLASA]) else None,
                "marka": (str(row[XLSX_COL_MARKA]).strip().upper()
                          if pd.notna(row[XLSX_COL_MARKA]) else None),
                "fuel": normalize_fuel(
                    row.get(XLSX_COL_PALIWO_ZNACZNIK),
                    row.get(XLSX_COL_PALIWO_SZCZEGOL),
                ),
                "drive": drive,
                "gearbox": gearbox,
                "mileage_km": float(row[XLSX_COL_PRZEBIEG]),
                "cost_per_km": float(row[XLSX_COL_COST_PER_KM]),
                "cost_total": (
                    float(row[XLSX_COL_COST_TOTAL])
                    if pd.notna(row.get(XLSX_COL_COST_TOTAL)) else 0.0
                ),
                "model_bi": str(row.get(XLSX_COL_MODEL_BI, "")),
            }
        )

    logger.info(
        f"Vehicles: total={n_total}, kept_after_filter={len(vehicles)} "
        f"(filter: km>={min_km}, ≥1 tech event, status∈{VALID_STATES}, cost>0)"
    )
    return vehicles


def compute_base_rates_lifetime(
    vehicles: list[dict],
    mapping: dict[str, list[str]],
    aso_premium: float,
    preserve_lookup: dict | None = None,
) -> tuple[list[dict], dict[str, int], dict]:
    """Compute nonASO median per (samar_class × band); ASO = nonASO × premium.

    Same fallback ladder as build_service_cost_resource.compute_base_rates:
      cell≥MIN_SAMPLE_CELL → cls_all≥MIN_SAMPLE_CLASS → neighbor → cls_all_low_n.

    If `preserve_lookup` is provided, any (samar_class, band) pair present in the
    lookup but absent from the BI data will be carried over verbatim (with source
    tagged `preserved_from_current_csv`). This protects niche classes like
    'Podstawowa - A MINI' that the BI export's rental-code taxonomy doesn't cover.
    """
    cell: dict = defaultdict(lambda: defaultdict(list))
    cls_all: dict = defaultdict(lambda: defaultdict(list))
    unmapped: dict[str, int] = defaultdict(int)
    n_per_band_per_class: dict = defaultdict(lambda: defaultdict(int))

    for v in vehicles:
        if not v["klasa"]:
            continue
        band = lifetime_band(v["mileage_km"])
        if band is None:
            continue
        samar_names = expand_fleet_code(v["klasa"], mapping)
        if not samar_names:
            unmapped[v["klasa"]] += 1
            continue
        mpk = v["cost_per_km"]
        for s in samar_names:
            cell[(s, band)]["non_aso"].append(mpk)
            cls_all[s]["non_aso"].append(mpk)
            n_per_band_per_class[s][band] += 1

    all_samar = sorted(set(cls_all.keys()))

    def resolve(samar_name, band, _seen=None):
        if _seen is None:
            _seen = set()
        if samar_name in _seen:
            return None, 0, "cycle"
        _seen = _seen | {samar_name}
        band_vals = cell.get((samar_name, band), {}).get("non_aso", [])
        class_vals = cls_all.get(samar_name, {}).get("non_aso", [])
        if len(band_vals) >= MIN_SAMPLE_CELL:
            return statistics.median(band_vals), len(band_vals), "qbi_band"
        if len(class_vals) >= MIN_SAMPLE_CLASS:
            return statistics.median(class_vals), len(class_vals), "fallback_class"
        neighbor = get_neighbor_class(samar_name, all_samar)
        if neighbor and neighbor != samar_name:
            n_rate, n_count, n_src = resolve(neighbor, band, _seen)
            if n_rate is not None:
                short = neighbor.split(" - ")[1][:6] if " - " in neighbor else neighbor[:6]
                return n_rate, n_count, f"cross_class_{short}({n_src})"
        if class_vals:
            return statistics.median(class_vals), len(class_vals), "fallback_class_low_n"
        return None, 0, "missing"

    rates = []
    for samar_name in all_samar:
        for band in MILEAGE_BANDS:
            non_aso_rate, n_non, src_non = resolve(samar_name, band)
            aso_rate = non_aso_rate * aso_premium if non_aso_rate is not None else None
            rates.append(
                {
                    "samar_name": samar_name,
                    "przebieg_do": band,
                    "aso_rate": aso_rate,
                    "non_aso_rate": non_aso_rate,
                    "n_nonaso": n_non,
                    "aso_premium_used": aso_premium,
                    "source": f"non_aso={src_non};aso=nonaso_x{aso_premium:.2f}",
                }
            )

    if preserve_lookup:
        covered = {(r["samar_name"], r["przebieg_do"]) for r in rates}
        preserved_count = 0
        for (samar_name, band), (old_aso, old_non) in preserve_lookup.items():
            if (samar_name, band) in covered:
                continue
            rates.append(
                {
                    "samar_name": samar_name,
                    "przebieg_do": band,
                    "aso_rate": old_aso,
                    "non_aso_rate": old_non,
                    "n_nonaso": 0,
                    "aso_premium_used": (
                        round(old_aso / old_non, 2)
                        if old_non and old_non > 0 else aso_premium
                    ),
                    "source": "preserved_from_current_csv (class not in BI export)",
                }
            )
            preserved_count += 1
        if preserved_count:
            logger.info(
                f"Preserved {preserved_count} (class, band) rows from current CSV "
                f"(classes not covered by BI export)"
            )
        rates.sort(key=lambda r: (r["samar_name"], r["przebieg_do"]))

    coverage = {
        "n_classes_covered": len(all_samar),
        "n_per_class": {
            s: {"total": sum(n_per_band_per_class[s].values()),
                "per_band": dict(n_per_band_per_class[s])}
            for s in all_samar
        },
    }
    return rates, dict(unmapped), coverage


def compute_multipliers_lifetime(
    vehicles: list[dict], mapping: dict[str, list[str]]
) -> dict:
    """Per-vehicle ratio vs class median, then median per layer key.

    DIAGNOSTIC ONLY per policy `feedback_service_multipliers_neutral.md`.
    Computes brand+fuel only (drive/gearbox skipped per policy).
    """
    samar_vals: dict = defaultdict(list)
    rows: list[dict] = []
    for v in vehicles:
        if not v["klasa"]:
            continue
        samar_names = expand_fleet_code(v["klasa"], mapping)
        if not samar_names:
            continue
        for s in samar_names:
            samar_vals[s].append(v["cost_per_km"])
        rows.append({**v, "samar_names": samar_names})

    class_median = {k: statistics.median(vals) for k, vals in samar_vals.items() if vals}

    brand_devs: dict = defaultdict(list)
    fuel_devs: dict = defaultdict(list)
    all_devs: list[float] = []
    for r in rows:
        deviations = []
        for s in r["samar_names"]:
            med = class_median.get(s)
            if med and med > 0:
                deviations.append(r["cost_per_km"] / med)
        if not deviations:
            continue
        rel = statistics.median(deviations)
        if rel < OUTLIER_REL_RANGE[0] or rel > OUTLIER_REL_RANGE[1]:
            continue
        all_devs.append(rel)
        if r["marka"]:
            brand_devs[r["marka"]].append(rel)
        if r["fuel"]:
            fuel_devs[r["fuel"]].append(rel)

    brand_mult = {
        b: (round(statistics.median(v), 4), len(v))
        for b, v in brand_devs.items()
        if len(v) >= MIN_SAMPLE_MULTIPLIER
    }
    fuel_mult = {
        f: (round(statistics.median(v), 4), len(v))
        for f, v in fuel_devs.items()
        if len(v) >= MIN_SAMPLE_MULTIPLIER
    }
    return {
        "brand": brand_mult,
        "fuel": fuel_mult,
        "global_median_deviation": (
            round(statistics.median(all_devs), 4) if all_devs else None
        ),
        "n_used_for_multipliers": len(all_devs),
    }


def load_current_serwis_baza(csv_path: Path) -> dict:
    """Parse current serwis_baza.csv → {(samar_name, band): (aso, non_aso)}."""
    lookup: dict = {}
    if not csv_path.exists():
        return lookup
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if len(row) < 4:
                continue
            samar = row[0].strip().strip('"')
            try:
                band = int(row[1])
                aso = float(row[2].replace(",", "."))
                non_aso = float(row[3].replace(",", "."))
            except (ValueError, IndexError):
                continue
            lookup[(samar, band)] = (aso, non_aso)
    return lookup


def write_proposal_csv(rates: list[dict], out_path: Path) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(
            "Klasa SAMAR (FK),przebieg_do,stawka_aso_per_km,"
            "stawka_non_aso_per_km,n_nonaso,aso_premium_used,source\n"
        )
        for r in rates:
            f.write(
                f'"{r["samar_name"]}",{r["przebieg_do"]},'
                f'"{_fmt_pl(r["aso_rate"])}","{_fmt_pl(r["non_aso_rate"])}",'
                f'{r["n_nonaso"]},"{_fmt_pl(r["aso_premium_used"], 2)}",'
                f'"{r["source"]}"\n'
            )
    logger.info(f"Wrote {out_path}")


def write_diff_csv(
    new_rates: list[dict], current_lookup: dict, out_path: Path
) -> None:
    rows = []
    for r in new_rates:
        old = current_lookup.get((r["samar_name"], r["przebieg_do"]))
        old_aso, old_non = old if old else (None, None)
        new_aso = r["aso_rate"]
        new_non = r["non_aso_rate"]

        def delta(old_v, new_v):
            if old_v is None or new_v is None or old_v == 0:
                return None
            return round((new_v - old_v) / old_v * 100, 1)

        rows.append(
            {
                "samar_name": r["samar_name"],
                "band": r["przebieg_do"],
                "old_aso": old_aso,
                "new_aso": new_aso,
                "delta_aso_pct": delta(old_aso, new_aso),
                "old_nonaso": old_non,
                "new_nonaso": new_non,
                "delta_nonaso_pct": delta(old_non, new_non),
                "source": r["source"],
            }
        )

    rows.sort(
        key=lambda r: abs(r["delta_nonaso_pct"]) if r["delta_nonaso_pct"] is not None else -1,
        reverse=True,
    )

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(
            "samar_name,band,old_aso,new_aso,delta_aso_pct,"
            "old_nonaso,new_nonaso,delta_nonaso_pct,source\n"
        )
        for r in rows:
            f.write(
                f'"{r["samar_name"]}",{r["band"]},'
                f'"{_fmt_pl(r["old_aso"])}","{_fmt_pl(r["new_aso"])}",'
                f'"{_fmt_pl(r["delta_aso_pct"], 1) if r["delta_aso_pct"] is not None else ""}",'
                f'"{_fmt_pl(r["old_nonaso"])}","{_fmt_pl(r["new_nonaso"])}",'
                f'"{_fmt_pl(r["delta_nonaso_pct"], 1) if r["delta_nonaso_pct"] is not None else ""}",'
                f'"{r["source"]}"\n'
            )
    logger.info(f"Wrote {out_path}")


def write_multipliers_csv(multipliers: dict, out_path: Path) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write("layer,key,multiplier,n_sample\n")
        for b, (m, n) in sorted(multipliers.get("brand", {}).items()):
            f.write(f'brand,"{b}","{_fmt_pl(m)}",{n}\n')
        for fu, (m, n) in sorted(multipliers.get("fuel", {}).items()):
            f.write(f'fuel,"{fu}","{_fmt_pl(m)}",{n}\n')
    logger.info(f"Wrote {out_path} (DIAGNOSTIC ONLY — multipliers stay at 1.0 in prod)")


def write_validation_report(
    vehicles: list[dict],
    rates: list[dict],
    multipliers: dict,
    coverage: dict,
    unmapped: dict,
    aso_premium: float,
    input_file: str,
    out_path: Path,
) -> None:
    cost_values = [v["cost_per_km"] for v in vehicles]
    global_med = round(statistics.median(cost_values), 5) if cost_values else None
    global_mean = round(statistics.mean(cost_values), 5) if cost_values else None

    source_counts: Counter = Counter()
    for r in rates:
        for tag in ("qbi_band", "fallback_class", "cross_class_", "fallback_class_low_n", "missing"):
            if tag in r["source"]:
                source_counts[tag.rstrip("_")] += 1

    n_diesel = sum(1 for v in vehicles if v["fuel"] == "DIESEL (ON)")
    n_petrol = sum(1 for v in vehicles if v["fuel"] == "BENZYNA (PB)")
    n_bev = sum(1 for v in vehicles if v["fuel"] == "ELEKTRYCZNY (BEV)")
    n_drive_awd = sum(1 for v in vehicles if v["drive"] == "AWD")
    n_drive_fwd = sum(1 for v in vehicles if v["drive"] == "FWD")
    n_gearbox_at = sum(1 for v in vehicles if v["gearbox"] == "AUTOMATYCZNA")
    n_gearbox_mt = sum(1 for v in vehicles if v["gearbox"] == "MANUALNA")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_file": input_file,
        "methodology_caveat": (
            "BI 'Koszt techn./km' is a LIFETIME average per VIN (total cost / total km), "
            "NOT a marginal cost per band segment. Runtime calculator treats it as marginal. "
            "Lower bands underestimate, upper bands overestimate marginal cost. "
            "Same assumption as in build_service_cost_resource.py — not a regression. "
            "Fix would require raw cost-event records, not in this export."
        ),
        "aso_premium_used": aso_premium,
        "policy_reference_multipliers": (
            "Per memory feedback_service_multipliers_neutral.md: service multipliers "
            "(brand/fuel/drive/gearbox) stay at 1.0 in production. The computed values "
            "in multipliers_proposal_lifetime.csv are DIAGNOSTIC ONLY — do NOT apply to "
            "Supabase. All cost differentiation lives in base rates per (Klasa SAMAR x band)."
        ),
        "sample_size": {
            "vehicles_kept": len(vehicles),
            "global_median_cost_per_km": global_med,
            "global_mean_cost_per_km": global_mean,
            "n_diesel": n_diesel,
            "n_petrol": n_petrol,
            "n_bev": n_bev,
            "n_drive_awd": n_drive_awd,
            "n_drive_fwd": n_drive_fwd,
            "n_drive_unknown": len(vehicles) - n_drive_awd - n_drive_fwd,
            "n_gearbox_at": n_gearbox_at,
            "n_gearbox_mt": n_gearbox_mt,
            "n_gearbox_unknown": len(vehicles) - n_gearbox_at - n_gearbox_mt,
        },
        "sample_thresholds": {
            "MIN_SAMPLE_CELL": MIN_SAMPLE_CELL,
            "MIN_SAMPLE_CLASS": MIN_SAMPLE_CLASS,
            "MIN_SAMPLE_MULTIPLIER": MIN_SAMPLE_MULTIPLIER,
            "OUTLIER_REL_RANGE": OUTLIER_REL_RANGE,
        },
        "anchor_source_counts": dict(source_counts),
        "unmapped_fleet_codes": dict(unmapped),
        "coverage_per_class": coverage["n_per_class"],
        "multipliers_diagnostic": {
            "brand": {k: {"multiplier": m, "n": n} for k, (m, n) in multipliers["brand"].items()},
            "fuel": {k: {"multiplier": m, "n": n} for k, (m, n) in multipliers["fuel"].items()},
            "global_median_deviation": multipliers["global_median_deviation"],
            "n_used_for_multipliers": multipliers["n_used_for_multipliers"],
        },
        "total_rate_rows": len(rates),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"Wrote {out_path}")


def call_import_serwis_baza(csv_path: Path) -> int:
    logger.info(f"Calling import_serwis_baza with csv={csv_path}")
    result = subprocess.run(
        [sys.executable, "-m", "scripts.import_serwis_baza", "--csv", str(csv_path)],
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("xlsx_path", help="Path to lifetime nonASO BI export XLSX")
    parser.add_argument("--sheet", default="Pojazdy nonASO")
    parser.add_argument("--min-km", type=int, default=15000)
    parser.add_argument("--aso-premium", type=float, default=1.30)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--current-csv", default=str(DEFAULT_SERWIS_BAZA))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Overwrite serwis_baza.csv and run import_serwis_baza (default: dry-run)",
    )
    parser.add_argument(
        "--no-import-supabase",
        action="store_true",
        help="With --apply: write CSV but skip Supabase import",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    current_csv_path = Path(args.current_csv)

    if args.apply and not current_csv_path.exists():
        logger.error(f"--apply requires existing --current-csv at {current_csv_path}")
        return 2

    logger.info("Loading class mapping from gsheet (samar_classes tab)...")
    gc = _get_gspread_client()
    mapping = load_class_mapping(gc)
    logger.info(f"Loaded {len(mapping)} rental codes → SAMAR classes")

    vehicles = read_lifetime_xlsx(args.xlsx_path, args.sheet, args.min_km)
    current_lookup = load_current_serwis_baza(current_csv_path)

    rates, unmapped, coverage = compute_base_rates_lifetime(
        vehicles, mapping, args.aso_premium, preserve_lookup=current_lookup
    )
    multipliers = compute_multipliers_lifetime(vehicles, mapping)

    write_proposal_csv(rates, output_dir / "service_rates_proposal_lifetime.csv")
    write_diff_csv(rates, current_lookup, output_dir / "serwis_baza_diff.csv")
    write_multipliers_csv(multipliers, output_dir / "multipliers_proposal_lifetime.csv")
    write_validation_report(
        vehicles, rates, multipliers, coverage, unmapped, args.aso_premium,
        args.xlsx_path, output_dir / "validation_report_lifetime.json",
    )

    if unmapped:
        logger.warning(f"Unmapped fleet codes (skipped): {dict(unmapped)}")

    if args.apply:
        logger.info(f"--apply: overwriting {current_csv_path}")
        overwrite_serwis_baza_csv(rates, str(current_csv_path))
        if not args.no_import_supabase:
            rc = call_import_serwis_baza(current_csv_path)
            if rc != 0:
                logger.error(f"import_serwis_baza failed with rc={rc}")
                return rc
            logger.info("Supabase import OK.")
        else:
            logger.info("--no-import-supabase: skipping Supabase import.")
    else:
        logger.info(
            "Dry-run complete. Review files in %s. "
            "Re-run with --apply to overwrite CSV. "
            "Multipliers are DIAGNOSTIC ONLY — never auto-applied.",
            output_dir,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
