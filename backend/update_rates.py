import sys
import os

# Add backend dir to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.database import supabase

print("--- Updating Control Center GSM Rates ---")
update_data = {
    'cost_gsm_subscription_monthly': 2.5,
    'cost_gsm_device': 971.25,
    'cost_gsm_installation': 0.0
}
res = supabase.table('control_center').update(update_data).eq('id', 1).execute()
print('Control center updated:', res.data)

print("\n--- Updating Service Rates (Scale down) ---")
scale_factor = 9288 / 43400
costs_res = supabase.table('samar_service_costs').select('*').execute()
if costs_res.data:
    updated = 0
    for row in costs_res.data:
        new_aso = round(row['cost_aso_per_km'] * scale_factor, 4)
        new_non_aso = round(row['cost_non_aso_per_km'] * scale_factor, 4)
        supabase.table('samar_service_costs').update({
            'cost_aso_per_km': new_aso,
            'cost_non_aso_per_km': new_non_aso
        }).eq('id', row['id']).execute()
        updated += 1
    print(f'Updated {updated} service rates (Scaled by {scale_factor:.4f})')
else:
    print('No service rates found.')
