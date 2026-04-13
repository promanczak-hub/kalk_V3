import sys
import os

sys.path.append(os.path.abspath("d:/kalk_v3/backend"))

from tasks.enrichment_tasks import backfill_vehicle_embeddings

if __name__ == "__main__":
    print("Starting backfill...")
    result = backfill_vehicle_embeddings()
    print("Backfill result:", result)
