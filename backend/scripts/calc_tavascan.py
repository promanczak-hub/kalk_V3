import sys
from pprint import pprint
import os

sys.path.append(os.path.abspath("."))
from core.LTRKalkulator import LTRKalkulator
from core.models.LTRModels import LTRInputData

# Tavascan parameters
input_data = LTRInputData(
    base_price_net=215284.55,
    discount_pct=21.0,
    wibor_pct=3.83,
    margin_pct=2.2,
    service_cost_type="nonASO",
    catalog_tire_class="Premium",
    samar_class_id=31,  # Assuming SUV C
    is_premium_class=False,
    engine_id=903,  # EV
    power_kw=250,
    vehicle_year="current",
    body_type="SUV",
    # factory options
    options_total_netto=42898.37,
    # others
    WartoscRynkowaOtwarty=0,
    CzynszProcent=0.0,
)

kalkulator = LTRKalkulator(input_data)
res = kalkulator.calculate_matrix(req_months=48, req_total_km=40000, only_exact=True)

print("--- Result ---")
pprint(res[0])
