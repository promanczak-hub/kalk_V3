"""Endpointy edycji/generowania zdjęć broszury przez nano-banana.

Wywoływane wyłącznie z kreatora broszury na akcję użytkownika.
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.nano_banana_service import (
    QuotaExceeded,
    edit_image,
    generate_image,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ImageGenerateRequest(BaseModel):
    vehicle_id: str = Field(description="ID pojazdu — do naliczania limitu i ścieżki w storage.")
    prompt: str = Field(min_length=1, description="Opis zdjęcia do wygenerowania.")


class ImageEditRequest(BaseModel):
    vehicle_id: str
    image_url: str = Field(description="URL istniejącego zdjęcia do przetworzenia.")
    prompt: str = Field(min_length=1, description="Instrukcja edycji, np. 'wyczyść tło, białe studio'.")


class ImageResponse(BaseModel):
    url: str
    ai_generated: bool = True


@router.post("/image/generate", response_model=ImageResponse)
def image_generate(req: ImageGenerateRequest) -> ImageResponse:
    try:
        url = generate_image(req.prompt, req.vehicle_id)
        return ImageResponse(url=url)
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logger.exception("[nano-banana] generate failed")
        raise HTTPException(status_code=502, detail=f"Błąd generowania zdjęcia: {e}")


@router.post("/image/edit", response_model=ImageResponse)
async def image_edit(req: ImageEditRequest) -> ImageResponse:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(req.image_url)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Nie można pobrać zdjęcia źródłowego (status {resp.status_code}).",
                )
            image_bytes = resp.content
            src_mime = resp.headers.get("content-type", "image/png")
            if not src_mime.startswith("image/"):
                src_mime = "image/png"

        url = edit_image(image_bytes, src_mime, req.prompt, req.vehicle_id)
        return ImageResponse(url=url)
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[nano-banana] edit failed")
        raise HTTPException(status_code=502, detail=f"Błąd edycji zdjęcia: {e}")
