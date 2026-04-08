import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path("d:/kalk_v3/backend").resolve()))

from core.pdf_pipeline.tasks import extract_pdf_pricelist_task
import celery.app.task

# Mock update_state to avoid celery backend errors on sync run
original_update_state = celery.app.task.Task.update_state


def mock_update_state(self, *args, **kwargs):
    pass


celery.app.task.Task.update_state = mock_update_state
extract_pdf_pricelist_task.update_state = mock_update_state

pdf_path = r"C:\Users\proma\Downloads\car-card-CJ6WHFJY.pdf"
print(f"Running extract task synchronously for {pdf_path}")

try:
    # Run the task synchronously
    result = extract_pdf_pricelist_task(pdf_path)
    print("FINISHED SUCCESSFULLY")
    print(result)
except Exception:
    import traceback

    traceback.print_exc()
