
import os
import sys

# Correct path for backend
backend_path = r"d:\kalk_v3\backend"
if backend_path not in sys.path:
    sys.path.append(backend_path)

# Set environment variables if needed (SUPABASE_URL, etc.)
# These should be in .env but for script to work we might need them or assume they are picked up.

from api.calculator_core_routes import readiness_check

# Mock parameters
samar_class_name = "Podstawowa - C NIŻSZA ŚREDNIA"
engine_name = "Benzyna mHEV (PB-mHEV)"
brand_name = "SKODA"
vehicle_id = "92d56268-aa4e-42b1-a795-d90bb8a9883b"
body_type_name = "Kombi"
paint_type_name = "Metalizowany"

print(f"Testing readiness_check for {samar_class_name}, {engine_name}, {brand_name}...")

try:
    result = readiness_check(
        samar_class_name=samar_class_name,
        engine_name=engine_name,
        brand_name=brand_name,
        vehicle_id=vehicle_id,
        body_type_name=body_type_name,
        paint_type_name=paint_type_name
    )
    print("SUCCESS")
    print(result)
except Exception as e:
    import traceback
    print("FAILED")
    traceback.print_exc()
