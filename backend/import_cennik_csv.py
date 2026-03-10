import os
"""
Import tire prices from cennikopon (1).csv into koszty_opon table.

Strategy:
1. Filter ONLY rows where Marka = 'Budżet' (planned budget prices).
2. For missing category/size combos, EXTRAPOLATE proportionally.
3. ENFORCE MONOTONIC INCREASE — only on non-CSV values.
4. ZERO OUT stale values for 13-14" wielosezon_wzmocnione.
5. Import all values into the database.
"""

import math

import pandas as pd
from sqlalchemy import create_engine, text


CLASS_TO_COL: dict[str, str] = {
    "budget": "budget",
    "medium": "medium",
    "premium": "premium",
    "wzmocnione budget": "wzmocnione_budget",
    "wzmocnione medium": "wzmocnione_medium",
    "wzmocnione premium": "wzmocnione_premium",
    "wielosezonowe budget": "wielosezon_budget",
    "wielosezonowe medium": "wielosezon_medium",
    "wielosezonowe premium": "wielosezon_premium",
    "wielosezonowe wzmocnione budget": "wielosezon_wzmocnione_budget",
    "wielosezonowe wzmocnione medium": "wielosezon_wzmocnione_medium",
    "wielosezonowe wzmocnione premium": "wielosezon_wzmocnione_premium",
}

VALID_SIZES: list[int] = list(range(13, 24))
REFERENCE_CLASS = "medium"


def load_budzet_prices(csv_path: str) -> dict[int, dict[str, float]]:
    """Load CSV, filter Budżet rows, return {size: {class: netto_price}}."""
    df = pd.read_csv(csv_path, sep=";")
    df["Netto"] = df["Netto"].astype(str).str.replace(",", ".").astype(float)
    df["KlasaOpon"] = df["KlasaOpon"].astype(str).str.strip().str.lower()
    df["Marka"] = df["Marka"].astype(str).str.strip()
    df["srednica"] = pd.to_numeric(df["RozmiarSrednica"], errors="coerce")

    budzet_mask = df["Marka"].str.lower() == "budżet"
    budzet_df = df[budzet_mask].copy()
    budzet_df = budzet_df.dropna(subset=["srednica", "Netto", "KlasaOpon"])
    budzet_df["srednica"] = budzet_df["srednica"].astype(int)
    budzet_df = budzet_df[budzet_df["srednica"].isin(VALID_SIZES)]

    prices: dict[int, dict[str, float]] = {}
    for _, row in budzet_df.iterrows():
        size = int(row["srednica"])
        klasa = row["KlasaOpon"]
        netto = row["Netto"]

        if klasa not in CLASS_TO_COL or netto <= 0:
            continue

        if size not in prices:
            prices[size] = {}
        prices[size][klasa] = netto

    return prices


def extrapolate_missing(
    prices: dict[int, dict[str, float]],
    csv_sources: dict[int, set[str]],
) -> dict[int, dict[str, float]]:
    """Fill in missing categories using proportional extrapolation."""
    all_classes: set[str] = set()
    for size_data in prices.values():
        all_classes.update(size_data.keys())

    sorted_sizes = sorted(prices.keys())

    for target_size in sorted_sizes:
        ref_value = prices[target_size].get(REFERENCE_CLASS)
        if ref_value is None:
            continue

        for klasa in sorted(all_classes):
            if klasa in prices[target_size]:
                continue

            ratio = _find_ratio(prices, klasa, target_size, sorted_sizes)
            if ratio is not None:
                extrapolated = math.ceil(ref_value * ratio)
                prices[target_size][klasa] = extrapolated
                print(
                    f'  EXTRAPOLATED {target_size}" {klasa} = '
                    f"{extrapolated} (ratio {ratio:.3f} × medium {ref_value})"
                )

    return prices


def _find_ratio(
    prices: dict[int, dict[str, float]],
    klasa: str,
    target_size: int,
    sorted_sizes: list[int],
) -> float | None:
    """Find ratio of klasa/reference at the nearest smaller size."""
    for size in reversed(sorted_sizes):
        if size >= target_size:
            continue
        class_val = prices[size].get(klasa)
        ref_val = prices[size].get(REFERENCE_CLASS)
        if class_val is not None and ref_val is not None and ref_val > 0:
            return class_val / ref_val
    return None


def enforce_monotonic_increase(
    prices: dict[int, dict[str, float]],
    csv_sources: dict[int, set[str]],
) -> dict[int, dict[str, float]]:
    """Ensure prices never decrease as tire size grows.

    ONLY fixes values that were NOT in the original CSV.
    CSV values are treated as ground truth and left untouched.
    """
    sorted_sizes = sorted(prices.keys())
    all_classes: set[str] = set()
    for size_data in prices.values():
        all_classes.update(size_data.keys())

    for klasa in sorted(all_classes):
        # Collect growth rates from CSV-sourced monotonic segments
        prev_value: float | None = None
        growth_rates: list[float] = []

        for size in sorted_sizes:
            current = prices[size].get(klasa)
            if current is None:
                continue
            is_csv = klasa in csv_sources.get(size, set())
            if prev_value is not None and current > prev_value and is_csv:
                growth_rates.append(current / prev_value)
            prev_value = current

        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 1.10

        # Second pass: enforce monotonic (skip CSV values)
        prev_value = None
        for size in sorted_sizes:
            current = prices[size].get(klasa)
            if current is None:
                continue

            is_csv = klasa in csv_sources.get(size, set())

            if prev_value is not None and current <= prev_value and not is_csv:
                fixed = math.ceil(prev_value * avg_growth)
                print(
                    f'  MONOTONIC FIX {size}" {klasa}: '
                    f"{current:.0f} → {fixed} (prev={prev_value:.0f}, "
                    f"growth={avg_growth:.3f})"
                )
                prices[size][klasa] = fixed
                current = fixed
            elif prev_value is not None and current <= prev_value and is_csv:
                print(
                    f'  ⚠️ CSV ANOMALY {size}" {klasa}: '
                    f"{current:.0f} ≤ prev {prev_value:.0f} "
                    f"(CSV value kept as-is)"
                )

            prev_value = current

    return prices


def zero_stale_categories(
    prices: dict[int, dict[str, float]],
    csv_sources: dict[int, set[str]],
) -> dict[int, dict[str, float]]:
    """Zero out wielosezon_wzmocnione for sizes where CSV has NO such entries.

    Explicitly adds zero entries so they get written to DB,
    overwriting old stale values.
    """
    wzmocnione_classes = {
        "wielosezonowe wzmocnione budget",
        "wielosezonowe wzmocnione medium",
        "wielosezonowe wzmocnione premium",
    }

    for size in sorted(prices.keys()):
        csv_classes = csv_sources.get(size, set())
        has_any_wzmocnione_in_csv = bool(csv_classes & wzmocnione_classes)

        if has_any_wzmocnione_in_csv:
            continue  # CSV has at least one — extrapolation is valid

        # Zero ALL wielosezon_wzmocnione (including ones not in prices dict)
        for klasa in wzmocnione_classes:
            old_val = prices[size].get(klasa, -1)
            prices[size][klasa] = 0
            if old_val > 0:
                print(f'  ZEROED {size}" {klasa} = {old_val:.0f} → 0')
            else:
                print(f'  ZEROED {size}" {klasa} (explicit DB override → 0)')

    return prices


def fix_csv_anomalies(
    prices: dict[int, dict[str, float]],
) -> dict[int, dict[str, float]]:
    """Fix CSV anomalies where prices decrease with size.

    E.g. 21" budget = 2280 < 20" budget = 3060.
    Interpolates between previous and next values.
    """
    sorted_sizes = sorted(prices.keys())
    all_classes: set[str] = set()
    for size_data in prices.values():
        all_classes.update(size_data.keys())

    for klasa in sorted(all_classes):
        prev_value: float | None = None
        for size in sorted_sizes:
            current = prices[size].get(klasa)
            if current is None or current == 0:
                continue
            if prev_value is not None and current < prev_value:
                # Find next higher value
                next_value: float | None = None
                for ns in sorted_sizes:
                    if ns <= size:
                        continue
                    nv = prices[ns].get(klasa)
                    if nv is not None and nv > prev_value:
                        next_value = nv
                        break

                if next_value is not None:
                    fixed = math.ceil((prev_value + next_value) / 2)
                else:
                    fixed = math.ceil(prev_value * 1.10)

                print(
                    f'  ANOMALY FIX {size}" {klasa}: '
                    f"{current:.0f} → {fixed} "
                    f"(interpolated between {prev_value:.0f} "
                    f"and {next_value or 'N/A'})"
                )
                prices[size][klasa] = fixed
                current = fixed

            prev_value = current

    return prices


def import_to_database(
    prices: dict[int, dict[str, float]],
    db_url: str,
) -> None:
    """Write final prices into koszty_opon table."""
    engine = create_engine(db_url)
    with engine.begin() as conn:
        for size in sorted(prices.keys()):
            cols = {
                CLASS_TO_COL[k]: v for k, v in prices[size].items() if k in CLASS_TO_COL
            }
            if not cols:
                continue

            set_clauses = ", ".join(f"{col} = :{col}" for col in cols)
            query = text(f"UPDATE koszty_opon SET {set_clauses} WHERE srednica = :size")
            params = {**cols, "size": size}
            conn.execute(query, params)
            print(f'  DB updated size {size}"')


def main() -> None:
    csv_path = r"C:\Users\proma\Downloads\cennikopon (1).csv"
    db_url = os.environ.get("DATABASE_URL")

    print("1. Loading Budżet prices from CSV...")
    prices = load_budzet_prices(csv_path)
    csv_sources: dict[int, set[str]] = {
        size: set(data.keys()) for size, data in prices.items()
    }
    for size in sorted(prices.keys()):
        print(f'  {size}": {sorted(prices[size].keys())}')

    print(f"\n2. Extrapolating missing categories (ref: {REFERENCE_CLASS})...")
    prices = extrapolate_missing(prices, csv_sources)

    print("\n3. Fixing CSV anomalies (price decreases with size)...")
    prices = fix_csv_anomalies(prices)

    print("\n4. Enforcing monotonic increase (extrapolated only)...")
    prices = enforce_monotonic_increase(prices, csv_sources)

    print("\n5. Zeroing stale wielosezon_wzmocnione (no CSV base)...")
    prices = zero_stale_categories(prices, csv_sources)

    print("\n5. Final price matrix:")
    for size in sorted(prices.keys()):
        row = prices[size]
        line = " | ".join(f"{k}={v:.0f}" for k, v in sorted(row.items()))
        print(f'  {size}": {line}')

    print("\n6. Importing to database...")
    import_to_database(prices, db_url)

    print("\nDone!")


if __name__ == "__main__":
    main()
