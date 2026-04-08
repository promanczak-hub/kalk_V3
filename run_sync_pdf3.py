import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path("d:/kalk_v3/backend").resolve()))

import tasks as my_tasks

pdf_path = r"C:\Users\proma\Downloads\car-card-CJ6WHFJY.pdf"
print(f"Running extract task synchronously for {pdf_path}")

try:
    # Run the task synchronously
    result = my_tasks.extract_pdf_pricelist_task(pdf_path)
    print("FINISHED SUCCESSFULLY")
    print(result)
except Exception:
    import traceback

    traceback.print_exc()
