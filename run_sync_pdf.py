import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path("d:/kalk_v3/backend").resolve()))

from tasks import extract_pdf_pricelist_task

pdf_path = r"C:\Users\proma\Downloads\car-card-CJ6WHFJY.pdf"
print(f"Running extract task synchronously for {pdf_path}")

try:
    # Run the task synchronously (this bypasses celery serialization but executes the function code in current process)
    result = extract_pdf_pricelist_task(pdf_path)
    print("FINISHED SUCCESSFULLY")
    print(result)
except Exception:
    import traceback

    traceback.print_exc()
