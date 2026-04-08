import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(str(Path("d:/kalk_v3/backend/.env").resolve()))
sys.path.insert(0, str(Path("d:/kalk_v3/backend").resolve()))

try:
    from celery.result import AsyncResult
    from core.celery_app import celery_app

    print("Connecting to Redis...")
    task_result = AsyncResult("some_fake_id", app=celery_app)
    print("State:", task_result.state)
except Exception:
    import traceback

    traceback.print_exc()
