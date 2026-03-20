import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status

from celery.result import AsyncResult

from core.pdf_pipeline.tasks import extract_pdf_pricelist_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf-pipeline", tags=["PDF Extraction Pipeline"])


@router.post("/extract")
async def extract_pdf_pricelist(file: UploadFile = File(...)):
    """
    Endpoint that accepts a PDF file and triggers extraction pipeline in Celery.
    Returns a task_id for frontend to poll status.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tylko pliki PDF są obsługiwane",
        )

    temp_file_path = None
    try:
        # Create a temporary file to save the uploaded PDF
        fd, temp_file_path = tempfile.mkstemp(suffix=".pdf")

        # Write chunks to disk to avoid memory overflow on huge PDFs
        with os.fdopen(fd, "wb") as f:
            while chunk := await file.read(8192):
                f.write(chunk)

        logger.info(
            f"Otrzymano plik {file.filename}, przekazuję ścieżkę {temp_file_path} do zadania w tle (Celery)"
        )

        # Trigger background task
        task = extract_pdf_pricelist_task.delay(temp_file_path)

        return {"task_id": task.id, "status": "processing"}

    except Exception as e:
        logger.exception("Błąd podczas inicjacji taska PDF:")
        # Cleanup in case of failure before task starts
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return {
            "is_successful": False,
            "error_message": f"Błąd inicjacji procesu ekstrakcji: {str(e)}",
        }


@router.get("/extract/status/{task_id}")
async def get_extraction_status(task_id: str):
    """
    Sprawdza status zadania Celery. Zwraca aktualny stan przetwarzania
    lub ustrukturyzowane wyniki w przypadku sukcesu.
    """
    task_result = AsyncResult(task_id)

    if task_result.state == "PENDING":
        return {
            "task_id": task_id,
            "state": task_result.state,
            "status": "Zadanie w kolejce...",
        }
    elif task_result.state == "PROCESSING":
        return {
            "task_id": task_id,
            "state": task_result.state,
            "info": task_result.info,
        }
    elif task_result.state == "SUCCESS":
        # Result is already a dict (model_dumped ExtractorPipelineResult from tasks.py)
        return {
            "task_id": task_id,
            "state": task_result.state,
            "result": task_result.result,
        }
    elif task_result.state == "FAILURE":
        return {
            "task_id": task_id,
            "state": task_result.state,
            "error": str(task_result.info),
        }
    else:
        return {"task_id": task_id, "state": task_result.state}
