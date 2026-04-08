import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(str(Path("d:/kalk_v3/backend/.env").resolve()))
sys.path.insert(0, str(Path("d:/kalk_v3/backend").resolve()))

from core.pdf_pipeline.tasks import extract_pdf_pricelist_task


def mock_update_state(*args, **kwargs):
    pass


extract_pdf_pricelist_task.update_state = mock_update_state

pdf_path = str(Path("d:/kalk_v3/test.pdf").resolve())
print(f"Running extract task synchronously for {pdf_path}")

try:
    result = extract_pdf_pricelist_task(pdf_path)
    print("FINISHED SUCCESSFULLY")
    print(f"Success: {result.get('is_successful')}")
    if not result.get("is_successful"):
        print(result.get("error_message"))
except BaseException as e:
    import traceback

    traceback.print_exc()
    print(f"FAILED WITH Exception: {e}")
