"""Repair script for updating vehicle calculator metadata.

Synchronizes WIBOR/Margin from control_center and ensures Service/Tires
presets are correctly populated in vehicle_synthesis.
"""

import sys
import os
import logging

# Add backend to path so we can import core/api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def repair_metadata():
    # 1. Fetch current control center settings
    logger.info("Fetching control center settings...")
    cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
    if not cc_res.data:
        logger.error("Control center settings not found")
        return

    cc_data = cc_res.data[0]
    default_wibor = float(cc_data.get("default_wibor", 3.83))
    bank_spread = float(cc_data.get("bank_spread", 2.20))
    logger.info(f"Using WIBOR: {default_wibor}%, Bank Margin: {bank_spread}%")

    # 2. Fetch vehicles from vehicle_synthesis
    # We fetch all of them to ensure consistency, but we'll prioritize those with missing data.
    logger.info("Fetching vehicles from vehicle_synthesis...")
    v_res = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    vehicles = v_res.data or []
    logger.info(f"Found {len(vehicles)} vehicles in total")

    updated_count = 0

    for v in vehicles:
        vid = v["id"]
        sd = v.get("synthesis_data") or {}
        setup = sd.get("calculator_setup") or {}

        needs_update = False

        # Ensure service_cost_type is present
        if not setup.get("service_cost_type"):
            setup["service_cost_type"] = "ASO"
            needs_update = True

        # Ensure tire_params are present
        tire_params = setup.get("tire_params") or {}
        if not tire_params or not tire_params.get("tire_class"):
            tire_params.update(
                {
                    "tire_class": "Medium",
                    "rim_diameter": tire_params.get("rim_diameter") or 18,
                    "tire_count_mode": "auto",
                    "tire_cost_correction": 0,
                    "tire_cost_correction_enabled": True,
                }
            )
            setup["tire_params"] = tire_params
            needs_update = True

        # Ensure financial_params/toggles are present and synchronized
        fin = setup.get("financial_params") or {}
        if (
            fin.get("wibor_pct") != default_wibor
            or fin.get("margin_pct") != bank_spread
        ):
            fin["wibor_pct"] = default_wibor
            fin["margin_pct"] = bank_spread
            setup["financial_params"] = fin
            needs_update = True

        toggles = setup.get("toggles") or {}
        if not toggles:
            toggles = {
                "gps_required": True,
                "add_sales_prep": True,
                "replacement_car": True,
                "hook_installation": False,
                "include_servicing": True,
                "express_pays_insurance": True,
            }
            setup["toggles"] = toggles
            needs_update = True

        if needs_update:
            sd["calculator_setup"] = setup
            try:
                supabase.table("vehicle_synthesis").update({"synthesis_data": sd}).eq(
                    "id", vid
                ).execute()
                updated_count += 1
                if updated_count % 10 == 0:
                    logger.info(f"Updated {updated_count} vehicles...")
            except Exception as e:
                logger.error(f"Failed to update vehicle {vid}: {e}")

    logger.info(f"Repair complete. Updated {updated_count} vehicles.")


if __name__ == "__main__":
    repair_metadata()
