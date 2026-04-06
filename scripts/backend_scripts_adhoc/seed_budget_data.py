"""Generate synthetic kalkulacje for Budget Finder testing.
Works without pojazdy_master — engine calculates from base_price_net alone.
"""

import os
import uuid
import random

os.environ.setdefault("GEMINI_API_KEY", "dummy")

from core.database import supabase

SYNTHETIC_CARS = [
    {
        "marka": "Volkswagen",
        "model": "Crafter 2.0 TDI Furgon",
        "cena": 189500,
        "fuel": "Diesel",
        "body": "Van",
        "trans": "Manual",
        "samar_cat": "VAN_D",
    },
    {
        "marka": "Volkswagen",
        "model": "Caddy 2.0 TDI Life",
        "cena": 112000,
        "fuel": "Diesel",
        "body": "MPV",
        "trans": "Automat",
        "samar_cat": "MPV_B",
    },
    {
        "marka": "Skoda",
        "model": "Octavia 1.5 TSI Style",
        "cena": 128000,
        "fuel": "Benzyna",
        "body": "Sedan",
        "trans": "Automat",
        "samar_cat": "SEDAN_C",
    },
    {
        "marka": "Skoda",
        "model": "Superb 2.0 TDI L&K",
        "cena": 198000,
        "fuel": "Diesel",
        "body": "Kombi",
        "trans": "Automat",
        "samar_cat": "KOMBI_D",
    },
    {
        "marka": "Skoda",
        "model": "Elroq 60",
        "cena": 156000,
        "fuel": "Elektryczny",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_C",
    },
    {
        "marka": "Ford",
        "model": "Transit Custom 2.0 EcoBlue",
        "cena": 165000,
        "fuel": "Diesel",
        "body": "Van",
        "trans": "Manual",
        "samar_cat": "VAN_C",
    },
    {
        "marka": "Ford",
        "model": "Ranger 2.0 Bi-Turbo Wildtrak",
        "cena": 245000,
        "fuel": "Diesel",
        "body": "Pickup",
        "trans": "Automat",
        "samar_cat": "SUV_D",
    },
    {
        "marka": "Toyota",
        "model": "Corolla 1.8 Hybrid Comfort",
        "cena": 118000,
        "fuel": "Hybryda",
        "body": "Sedan",
        "trans": "Automat",
        "samar_cat": "SEDAN_B",
    },
    {
        "marka": "Toyota",
        "model": "Proace City 1.5 D-4D",
        "cena": 99000,
        "fuel": "Diesel",
        "body": "Van",
        "trans": "Manual",
        "samar_cat": "VAN_B",
    },
    {
        "marka": "Toyota",
        "model": "RAV4 2.5 Hybrid AWD",
        "cena": 195000,
        "fuel": "Hybryda",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_C",
    },
    {
        "marka": "Volkswagen",
        "model": "T-Cross 1.0 TSI Style",
        "cena": 105000,
        "fuel": "Benzyna",
        "body": "SUV",
        "trans": "Manual",
        "samar_cat": "SUV_A",
    },
    {
        "marka": "Volkswagen",
        "model": "Tiguan 2.0 TDI R-Line",
        "cena": 215000,
        "fuel": "Diesel",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_D",
    },
    {
        "marka": "Skoda",
        "model": "Kamiq 1.0 TSI Ambition",
        "cena": 95000,
        "fuel": "Benzyna",
        "body": "SUV",
        "trans": "Manual",
        "samar_cat": "SUV_A",
    },
    {
        "marka": "Ford",
        "model": "Focus 1.0 EcoBoost Active",
        "cena": 108000,
        "fuel": "Benzyna",
        "body": "Hatchback",
        "trans": "Manual",
        "samar_cat": "HATCH_B",
    },
    {
        "marka": "Volkswagen",
        "model": "ID.4 Pro Performance",
        "cena": 199000,
        "fuel": "Elektryczny",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_C",
    },
    {
        "marka": "Skoda",
        "model": "Fabia 1.0 TSI Monte Carlo",
        "cena": 82000,
        "fuel": "Benzyna",
        "body": "Hatchback",
        "trans": "Manual",
        "samar_cat": "HATCH_A",
    },
    {
        "marka": "Toyota",
        "model": "Yaris Cross 1.5 Hybrid",
        "cena": 112000,
        "fuel": "Hybryda",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_B",
    },
    {
        "marka": "Ford",
        "model": "Kuga 2.5 PHEV ST-Line",
        "cena": 178000,
        "fuel": "Hybryda",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_C",
    },
    {
        "marka": "Volkswagen",
        "model": "Passat 2.0 TDI Elegance",
        "cena": 185000,
        "fuel": "Diesel",
        "body": "Kombi",
        "trans": "Automat",
        "samar_cat": "KOMBI_C",
    },
    {
        "marka": "Toyota",
        "model": "Hilux 2.8 D-4D Invincible",
        "cena": 238000,
        "fuel": "Diesel",
        "body": "Pickup",
        "trans": "Automat",
        "samar_cat": "SUV_D",
    },
    {
        "marka": "Skoda",
        "model": "Kodiaq 2.0 TDI L&K 7os",
        "cena": 225000,
        "fuel": "Diesel",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_D",
    },
    {
        "marka": "Ford",
        "model": "Tourneo Connect 1.5 EcoBlue",
        "cena": 128000,
        "fuel": "Diesel",
        "body": "MPV",
        "trans": "Automat",
        "samar_cat": "MPV_B",
    },
    {
        "marka": "Volkswagen",
        "model": "Golf 1.5 eTSI R-Line",
        "cena": 142000,
        "fuel": "Benzyna",
        "body": "Hatchback",
        "trans": "Automat",
        "samar_cat": "HATCH_C",
    },
    {
        "marka": "Ford",
        "model": "Puma 1.0 EcoBoost ST-Line X",
        "cena": 118000,
        "fuel": "Benzyna",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_B",
    },
    {
        "marka": "Toyota",
        "model": "Camry 2.5 Hybrid Executive",
        "cena": 168000,
        "fuel": "Hybryda",
        "body": "Sedan",
        "trans": "Automat",
        "samar_cat": "SEDAN_C",
    },
    {
        "marka": "Volkswagen",
        "model": "Transporter T7 2.0 TDI",
        "cena": 210000,
        "fuel": "Diesel",
        "body": "Van",
        "trans": "Manual",
        "samar_cat": "VAN_D",
    },
    {
        "marka": "Skoda",
        "model": "Scala 1.0 TSI Ambition",
        "cena": 89000,
        "fuel": "Benzyna",
        "body": "Hatchback",
        "trans": "Manual",
        "samar_cat": "HATCH_A",
    },
    {
        "marka": "Ford",
        "model": "Mustang Mach-E RWD",
        "cena": 235000,
        "fuel": "Elektryczny",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_D",
    },
    {
        "marka": "Toyota",
        "model": "bZ4X FWD",
        "cena": 189000,
        "fuel": "Elektryczny",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_C",
    },
    {
        "marka": "Skoda",
        "model": "Enyaq iV 60",
        "cena": 175000,
        "fuel": "Elektryczny",
        "body": "SUV",
        "trans": "Automat",
        "samar_cat": "SUV_C",
    },
]

inserted = 0
for car in SYNTHETIC_CARS:
    price_variance = random.uniform(0.95, 1.05)
    cena = round(car["cena"] * price_variance, 2)
    discount = round(random.uniform(0, 15), 1)

    stan_json = {
        "vehicle_id": "",
        "base_price_net": cena,
        "discount_pct": discount,
        "vehicle_mapped": {
            "fuel_type": car["fuel"],
            "body_type": car["body"],
            "transmission": car["trans"],
        },
        "samar_category": car["samar_cat"],
        "factory_options": [],
        "service_options": [],
    }

    dane_pojazdu = f"{car['marka']} {car['model']}"

    try:
        numer = f"SEED-{inserted + 1:03d}"
        supabase.table("ltr_kalkulacje").insert(
            {
                "id": str(uuid.uuid4()),
                "numer_kalkulacji": numer,
                "dane_pojazdu": dane_pojazdu,
                "cena_netto": cena,
                "stan_json": stan_json,
            }
        ).execute()
        inserted += 1
        print(f"  OK: {dane_pojazdu} @ {cena:.0f} PLN (rabat {discount}%)")
    except Exception as e:
        print(f"  FAIL: {dane_pojazdu}: {e}")

print(f"\n=== Wstawiono {inserted} syntetycznych kalkulacji ===")
