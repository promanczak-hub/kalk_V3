"""Nano-banana (Gemini 2.5 Flash Image) — edycja i generowanie zdjęć do broszury.

Generowanie obrazu jest WYŁĄCZNIE akcją użytkownika (przycisk w kreatorze
broszury) — nic nie odpala się automatycznie w pipeline. Koszt ~$0.04/obraz,
więc obowiązuje limit per pojazd per dzień (konfigurowalny w control_center).
"""

import logging
import os
import uuid
from datetime import date
from typing import Tuple

from google.genai import types

from core.control_center import fetch_control_center_value
from core.database import supabase
from core.gemini_client import SAFETY_SETTINGS_PERMISSIVE, get_gemini_client
from core.redis_cache import _PREFIX, _get_client

logger = logging.getLogger(__name__)

# nano-banana. Zmienna środowiskowa pozwala podmienić wariant (preview/GA) bez zmiany kodu.
NANO_BANANA_MODEL = os.getenv("NANO_BANANA_MODEL", "gemini-2.5-flash-image")
# Publiczny bucket pojazdów (ten sam, w którym leżą raw PDF-y i wyciągnięte zdjęcia).
BUCKET = "raw-vehicle-pdfs"
_QUOTA_TTL_SECONDS = 86_400  # 24h


class QuotaExceeded(Exception):
    """Przekroczono dzienny limit generacji nano-banana dla pojazdu."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"Limit {limit} generacji/dzień dla tego pojazdu został wyczerpany.")


def _quota_limit() -> int:
    raw = fetch_control_center_value("nano_banana.limit_per_vehicle_session", default=10)
    try:
        value = int(raw)
        return value if value > 0 else 10
    except (TypeError, ValueError):
        return 10


def _quota_key(vehicle_id: str) -> str:
    return f"{_PREFIX}nano_banana:{vehicle_id}:{date.today().isoformat()}"


def reserve_quota(vehicle_id: str) -> None:
    """Atomowo rezerwuje jedną generację. Rzuca QuotaExceeded po przekroczeniu.

    Gdy Redis jest niedostępny — degraduje do „przepuść" (limit to zabezpieczenie
    kosztowe best-effort, twardą barierą jest to, że generacja wymaga akcji usera).
    """
    client = _get_client()
    if client is None:
        logger.warning("[nano-banana] Redis niedostępny — pomijam limit kosztowy dla %s", vehicle_id)
        return
    key = _quota_key(vehicle_id)
    used = client.incr(key)
    if used == 1:
        client.expire(key, _QUOTA_TTL_SECONDS)
    limit = _quota_limit()
    if used > limit:
        client.decr(key)  # cofnij rezerwację — ta próba nie weszła
        raise QuotaExceeded(limit)


def _extract_image(response: types.GenerateContentResponse) -> Tuple[bytes, str]:
    for candidate in response.candidates or []:
        content = candidate.content
        for part in (content.parts or []) if content else []:
            blob = part.inline_data
            if blob and blob.data:
                return blob.data, (blob.mime_type or "image/png")
    raise ValueError("Model nano-banana nie zwrócił obrazu (sprawdź prompt / safety).")


def _upload(image_bytes: bytes, mime: str, vehicle_id: str) -> str:
    ext = "png" if "png" in mime else "jpg"
    path = f"brochure-ai/{vehicle_id}/{uuid.uuid4().hex}.{ext}"
    supabase.storage.from_(BUCKET).upload(
        path=path,
        file=image_bytes,
        file_options={"content-type": mime},
    )
    return supabase.storage.from_(BUCKET).get_public_url(path)


def _generate(contents: list, vehicle_id: str) -> str:
    client = get_gemini_client()
    response = client.models.generate_content(
        model=NANO_BANANA_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        ),
    )
    image_bytes, mime = _extract_image(response)
    return _upload(image_bytes, mime, vehicle_id)


def generate_image(prompt: str, vehicle_id: str) -> str:
    """Tworzy nowe zdjęcie od zera z promptu. Zwraca publiczny URL w Supabase."""
    reserve_quota(vehicle_id)
    return _generate([prompt], vehicle_id)


def edit_image(image_bytes: bytes, src_mime: str, prompt: str, vehicle_id: str) -> str:
    """Edytuje istniejące zdjęcie wg promptu (image-to-image). Zwraca publiczny URL."""
    reserve_quota(vehicle_id)
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=src_mime),
        types.Part.from_text(text=prompt),
    ]
    return _generate(contents, vehicle_id)
