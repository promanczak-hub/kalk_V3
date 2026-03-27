
import os
import decimal

# --- Config ---
ASO_BASE = decimal.Decimal("0.0623")
NON_ASO_BASE = decimal.Decimal("0.057")

ENGINE_MULTIPLIERS = {
    1: decimal.Decimal("1.0"),    # Benzyna (PB)
    2: decimal.Decimal("1.02"),   # Diesel (ON)
    3: decimal.Decimal("1.03"),   # Benzyna mHEV (PB-mHEV)
    4: decimal.Decimal("1.05"),   # Diesel mHEV (ON-mHEV)
    5: decimal.Decimal("1.09"),   # Hybryda (HEV)
    6: decimal.Decimal("1.15"),   # Plug-in Hybrid (PHEV)
    7: decimal.Decimal("0.6"),    # Elektryczny (BEV)
    8: decimal.Decimal("1.2"),    # Wodór (FCEV)
    9: decimal.Decimal("1.1"),    # LPG
}

POWER_BAND_MULTIPLIERS = {
    "LOW": decimal.Decimal("1.0"),
    "MID": decimal.Decimal("1.15"),
    "HIGH": decimal.Decimal("1.3"),
}

def generate_sql():
    sql = "INSERT INTO samar_service_costs (samar_class_id, engine_type_id, power_band, cost_aso_per_km, cost_non_aso_per_km) VALUES\n"
    values = []
    
    # 33 Classes
    for class_id in range(1, 34):
        # 9 Engines
        for eng_id, eng_mult in ENGINE_MULTIPLIERS.items():
            # 3 Power Bands
            for p_band, p_mult in POWER_BAND_MULTIPLIERS.items():
                final_aso = (ASO_BASE * eng_mult * p_mult).quantize(decimal.Decimal("0.0001"))
                final_non_aso = (NON_ASO_BASE * eng_mult * p_mult).quantize(decimal.Decimal("0.0001"))
                
                values.append(f"({class_id}, {eng_id}, '{p_band}', {final_aso}, {final_non_aso})")
    
    sql += ",\n".join(values)
    sql += "\nON CONFLICT (samar_class_id, engine_type_id, power_band) DO UPDATE SET\n"
    sql += "    cost_aso_per_km = EXCLUDED.cost_aso_per_km,\n"
    sql += "    cost_non_aso_per_km = EXCLUDED.cost_non_aso_per_km;"
    
    with open("migrate_service_costs.sql", "w", encoding="utf-8") as f:
        f.write(sql)
    
    print(f"Generated SQL with {len(values)} records.")

if __name__ == "__main__":
    generate_sql()
