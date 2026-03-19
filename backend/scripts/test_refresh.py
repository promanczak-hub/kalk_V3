import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.matrix_cache_job import refresh_matrix_cache_for_vehicles

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    # Cupra Terramar GOS-26-059093
    test_id = "2a016435-f3a5-4092-9b4f-a73ccce14a01"
    print(f"Refreshing cache for {test_id}...")
    refresh_matrix_cache_for_vehicles([test_id])
    print("Done.")
