import os
import sys

# Add backend to path so imports work
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "d/kalk_v3/backend"))
)

from core.database import supabase
from tasks.matrix_tasks import process_kalkulacja_matrix_task


def run():
    print("Fetching all calculations from ltr_kalkulacje...")

    # We paginate or just fetch all if it's not a huge table.
    # Supabase select limits to 1000 by default usually, so let's do batches if needed,
    # but for typical usage 1000 might be enough. Let's do a loop just in case.
    all_ids = []
    page_size = 1000
    offset = 0

    while True:
        res = (
            supabase.table("ltr_kalkulacje")
            .select("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not res.data:
            break
        all_ids.extend([row["id"] for row in res.data])
        offset += page_size
        if len(res.data) < page_size:
            break

    print(f"Found {len(all_ids)} calculations.")

    queued_count = 0
    for kalk_id in all_ids:
        print(f"Queueing matrix build for {kalk_id}...")
        process_kalkulacja_matrix_task.delay(kalk_id)
        queued_count += 1

    print(f"Successfully queued {queued_count} tasks in Celery!")


if __name__ == "__main__":
    run()
