import pandas as pd
from sqlalchemy import create_engine, text
import math


def import_tire_prices():
    engine = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
    df = pd.read_csv(r"C:\Users\proma\Downloads\cennikopon (1).csv", sep=";")

    # Data cleanup
    # Replace comma with dot in Netto and Brutto columns
    df["Netto"] = df["Netto"].astype(str).str.replace(",", ".").astype(float)

    # Clean up classes
    df["KlasaOpon"] = df["KlasaOpon"].astype(str).str.strip().str.lower()

    # Map classes to columns
    class_mapping = {
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

    # Extract diameter
    df["srednica"] = pd.to_numeric(df["RozmiarSrednica"], errors="coerce")
    df = df.dropna(subset=["srednica", "Netto", "KlasaOpon"])
    df["srednica"] = df["srednica"].astype(int)

    # Filter to valid sizes only
    valid_sizes = list(range(13, 24))
    df = df[df["srednica"].isin(valid_sizes)]

    # Group by diameter and class, calculate mean Netto price
    # CRITICAL FIX: The CSV already contains prices for a full SET (komplet), so DO NOT multiply by 4.
    grouped = df.groupby(["srednica", "KlasaOpon"])["Netto"].mean().reset_index()
    grouped["koszt_kompletu"] = grouped["Netto"].apply(math.ceil)

    # Prepare data for insertion/update
    updates = {}
    for _, row in grouped.iterrows():
        s = row["srednica"]
        c = row["KlasaOpon"]
        k = row["koszt_kompletu"]

        if c in class_mapping:
            col = class_mapping[c]
            if s not in updates:
                updates[s] = {}
            updates[s][col] = k

    with engine.begin() as conn:
        for size, cols in updates.items():
            # Update specific values
            set_clauses = ", ".join([f"{col} = :{col}" for col in cols.keys()])
            if not set_clauses:
                continue

            query = text(f"""
                UPDATE koszty_opon
                SET {set_clauses}
                WHERE srednica = :size
            """)

            params = cols.copy()
            params["size"] = size

            conn.execute(query, params)
            print(f"Updated size {size} with values: {cols}")

    print(
        "Populated real-world SET prices (Netto) into koszty_opon table successfully."
    )


if __name__ == "__main__":
    import_tire_prices()
