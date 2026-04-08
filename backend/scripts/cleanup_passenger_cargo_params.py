"""Cleanup script to remove commercial cargo params from passenger vehicles."""

import asyncio
from supabase.client import create_client, ClientOptions
from core.settings import SUPABASE_URL, SUPABASE_KEY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_passenger_cargo_params() -> None:
    """Remove commercial cargo parameters from passenger vehicles."""
    sb_public = create_client(SUPABASE_URL, SUPABASE_KEY)
    sb_rs = create_client(
        SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(schema="reverse_search")
    )

    logger.info("Fetching passenger vehicles...")

    # 1. First, find all vehicles in vehicle_synthesis that are passenger cars
    # Use samar_classes logic: Passenger classes are <= 127
    car_resp = (
        sb_public.table("vehicle_synthesis")
        .select("id, synthesis_data, document_category")
        .execute()
    )

    passenger_vehicle_ids = set()
    for row in car_resp.data:
        vid = row["id"]
        doc_cat = row.get("document_category")
        syn = row.get("synthesis_data") or {}

        is_commercial = False
        if doc_cat:
            is_commercial = doc_cat == "commercial"
        else:
            v_class_lower = syn.get("card_summary", {}).get("vehicle_class", "").lower()
            b_style_lower = syn.get("card_summary", {}).get("body_style", "").lower()
            comm_kws = [
                "dostawcz",
                "van",
                "furgon",
                "pick-up",
                "skrzyni",
                "kontener",
                "chłodnia",
                "izoterma",
                "plandeka",
                "podwozie",
                "autolaweta",
            ]
            pass_kws = ["minivan", "microvan", "kombivan"]
            has_comm = any(k in v_class_lower or k in b_style_lower for k in comm_kws)
            has_pass = any(k in v_class_lower or k in b_style_lower for k in pass_kws)
            is_commercial = has_comm and not has_pass

        if not is_commercial:
            passenger_vehicle_ids.add(vid)

    logger.info(f"Found {len(passenger_vehicle_ids)} passenger vehicles.")

    if not passenger_vehicle_ids:
        logger.info("No passenger vehicles to clean.")
        return

    # 2. Delete erroneous evidence rows
    v_ids = list(passenger_vehicle_ids)
    evidence_keys_to_remove = [
        "ilość_europalet",
        "m2",
        "kubatura_przestrzeni_ładunkowej_w_m3",
    ]

    # Process in batches of 100 to avoid request URL length limits
    batch_size = 100
    deleted_evidence_count = 0

    for i in range(0, len(v_ids), batch_size):
        batch = v_ids[i : i + batch_size]
        try:
            del_resp = (
                sb_rs.table("vehicle_feature_evidence")
                .delete()
                .in_("vehicle_id", batch)
                .in_("feature_key", evidence_keys_to_remove)
                .execute()
            )
            deleted_evidence_count += len(del_resp.data)
        except Exception as e:
            logger.error(f"Error deleting evidence for batch {i}: {e}")

    logger.info(
        f"Deleted {deleted_evidence_count} false cargo evidence records from passenger vehicles."
    )

    # 3. Clean up vehicle_specs_normalized feature_jsonb
    logger.info("Cleaning up vehicle_specs_normalized.features_jsonb...")

    # Fetch existing normalized specs for these vehicles
    updated_specs_count = 0
    for i in range(0, len(v_ids), batch_size):
        batch = v_ids[i : i + batch_size]
        try:
            specs_resp = (
                sb_rs.table("vehicle_specs_normalized")
                .select("vehicle_id, features")
                .in_("vehicle_id", batch)
                .execute()
            )

            for row in specs_resp.data:
                vid = row["vehicle_id"]
                feats = row.get("features") or {}
                needs_update = False

                for key in evidence_keys_to_remove:
                    if key in feats:
                        del feats[key]
                        needs_update = True

                if needs_update:
                    sb_rs.table("vehicle_specs_normalized").update(
                        {"features": feats}
                    ).eq("vehicle_id", vid).execute()
                    updated_specs_count += 1

        except Exception as e:
            logger.error(f"Error updating normalized specs for batch {i}: {e}")

    logger.info(f"Updated {updated_specs_count} vehicle_specs_normalized records.")
    logger.info("Cleanup completed successfully.")


if __name__ == "__main__":
    asyncio.run(cleanup_passenger_cargo_params())
