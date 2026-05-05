from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Any
import logging

from core.database import get_fresh_client
from core.embeddings import generate_embedding
from core.celery_app import celery_app
from tasks.enrichment_tasks import generate_embedding_for_vehicle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/semantic", tags=["Semantic Search"])


class SemanticSearchRequest(BaseModel):
    query: str = Field(
        ..., description="Treść zapytania, np. 'samochód dla rodziny 2+2'"
    )
    limit: int = Field(10, description="Maksymalna liczba wyników", ge=1, le=50)
    duration_months: int | None = Field(
        None, description="Opcjonalny filtr okresu finansowania"
    )
    annual_mileage: int | None = Field(None, description="Opcjonalny filtr przebiegu")
    fuel_type: str | None = Field(None, description="Twardy filtr: Rodzaj paliwa")
    body_style: str | None = Field(None, description="Twardy filtr: Typ nadwozia")
    transmission: str | None = Field(None, description="Twardy filtr: Skrzynia biegów")
    samar_category: str | None = Field(
        None, description="Twardy filtr: Segment z systemu SAMAR"
    )


class SemanticSyncRequest(BaseModel):
    batch_size: int = Field(
        50, description="Ilość aut do zsynchronizowania w jednym przebiegu"
    )
    force_all: bool = Field(False, description="Czy nadpisać istniejące wektory?")


@router.post("/search")
async def search_vehicles_semantic(request: SemanticSearchRequest) -> dict[str, Any]:
    """Wyszukiwanie samochodów za pomocą zapytań tekstowych (Semantic Search)."""
    try:
        # 1. Wygeneruj embedding dla zapytania
        query_vector = generate_embedding(request.query)
        if not query_vector:
            raise HTTPException(
                status_code=500, detail="Nie udało się wygenerować wektora zapytania"
            )

        # 2. Strzał do Supabase RPC by znaleźć podobne auta
        vector_str = "[" + ",".join(f"{x:.6f}" for x in query_vector) + "]"

        response = (
            get_fresh_client()
            .rpc(
                "rpc_search_vehicles_by_text",
                {
                    "p_query_embedding": vector_str,
                    "p_limit": request.limit,
                    "p_duration_months": request.duration_months,
                    "p_annual_mileage": request.annual_mileage,
                    "p_fuel": request.fuel_type,
                    "p_body_style": request.body_style,
                    "p_transmission": request.transmission,
                    "p_samar_category": request.samar_category,
                },
            )
            .execute()
        )

        return {"status": "success", "query": request.query, "results": response.data}

    except Exception as e:
        logger.error(f"Error in semantic search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


_MISSING_EMBEDDINGS_OR_FILTER = (
    "semantic_embedding.is.null,"
    "vector_use_case.is.null,"
    "vector_specs.is.null,"
    "vector_equipment.is.null"
)


@celery_app.task(name="background_sync_semantic_task")
def background_sync_task(batch_size: int, force_all: bool):
    """Background task: regenerate semantic + multi-vector embeddings for a batch.
    Delegates per-vehicle work to `generate_embedding_for_vehicle` so all four
    vector columns stay in sync."""
    try:
        client = get_fresh_client()

        query = client.table("vehicle_synthesis").select("id")
        if not force_all:
            query = query.or_(_MISSING_EMBEDDINGS_OR_FILTER)

        response = query.limit(batch_size).execute()
        vehicles = response.data

        if not vehicles:
            logger.info("Brak pojazdów do zsynchronizowania (Semantic Search).")
            return

        success_count = 0
        for v in vehicles:
            try:
                res = generate_embedding_for_vehicle(v["id"])
                if res.get("status") == "success":
                    success_count += 1
            except Exception as inner_e:
                logger.error(
                    f"Błąd podczas wektoryzacji pojazdu {v.get('id')}: {inner_e}"
                )

        logger.info(
            f"Zakończono synchronizację semantyczną: {success_count}/{len(vehicles)} udanych wektoryzacji."
        )

    except Exception as e:
        logger.error(f"Błąd podczas wykonywania background_sync_task: {e}")


@router.post("/sync-all")
async def sync_all_semantic_embeddings(
    request: SemanticSyncRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """
    Endpoint inicjujący przeliczenie embeddingów dla istniejących pojazdów w bazie.
    Zamiast blokować wątek, zadanie wykona się asynchronicznie w tle (FastAPI Background Tasks).
    """
    try:
        db_client = get_fresh_client()
        # Liczymy ile pojazdów ma jakikolwiek brakujący wektor (semantic LUB którykolwiek z 3 multi).
        query = db_client.table("vehicle_synthesis").select("id", count="exact")
        if not request.force_all:
            query = query.or_(_MISSING_EMBEDDINGS_OR_FILTER)

        response = query.execute()
        total_remaining = response.count if response.count is not None else 0

        if total_remaining == 0:
            return {
                "status": "success",
                "message": "Nie ma aut wymagających wektoryzacji.",
            }

        # Zlecamy wykonanie w tle do Kolejki Celery co zabezpiecza przed wyłączeniem poda
        background_sync_task.delay(request.batch_size, request.force_all)

        return {
            "status": "success",
            "message": f"Zlecono przetworzenie paczki {request.batch_size} aut.",
            "total_remaining": total_remaining,
        }
    except Exception as e:
        logger.error(f"Error in sync-all API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
