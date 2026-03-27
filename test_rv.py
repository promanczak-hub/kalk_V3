import os
import sys
import json
sys.path.append(r"d:\kalk_v3\backend")

from core.samar_rv import SamarRVCalculator, RVInput

# Based on DSKODAON, fuel ON
input_data = RVInput(
    samar_class_id=103,
    engine_id=2, # ON
    brand_name="SKODA",
    model_name="Superb",
    months=48,
    total_km=140000,
    catalog_base_net=247850.0 / 1.23,  # Net from Gross catalog
    catalog_options_net=34500.0 / 1.23, # Net from Gross catalog
    paint_type_id=None,
    is_metalic=True,
    body_type_id=None,
    rocznik="bieżący",
    zabudowa_apr_wr=False,
    zabudowa_type_id=None,
    manual_wr_correction=0.0
)

calc = SamarRVCalculator(input_data)
out = calc.calculate()

print("Output WR:", out.wr_net)
print("Output WR %:", out.wr_percent)
print("Debug:", json.dumps(out.debug, indent=2, ensure_ascii=False))

