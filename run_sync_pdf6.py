import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path("d:/kalk_v3/backend").resolve()))

from core.pdf_pipeline.tasks import extract_pdf_pricelist_task


def mock_update_state(*args, **kwargs):
    pass


extract_pdf_pricelist_task.update_state = mock_update_state

pdf_path = r"C:\Users\proma\Downloads\car-card-CJ6WHFJY.pdf"
print(f"Running extract task synchronously for {pdf_path}")

try:
    # Run the task synchronously
    result = extract_pdf_pricelist_task(pdf_path)
    print("FINISHED SUCCESSFULLY")
    import json

    print(json.dumps(result, indent=2))
except Exception:
    import traceback

    traceback.print_exc()
