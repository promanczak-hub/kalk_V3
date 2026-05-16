"""Admin routes — webhook target dla Supabase Database Webhook.

Po edycji w Supabase Dashboard (Table Editor / SQL Editor), Supabase
Database Webhook (Database → Webhooks) wywołuje
`POST /api/admin/invalidate-cache` aby zmiany w tabelach referencyjnych
(SOT) były widoczne w aplikacji bez czekania na TTL Redis.

Auth: bearer token z env `ADMIN_CACHE_TOKEN`. Jeśli env nie ustawiony,
endpoint zwraca 503 (deliberately disabled) — żeby nie istniał otwarty
endpoint czyszczący cache bez autoryzacji.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from core.redis_cache import cache_invalidate_pattern, is_redis_available

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# Prefiksy Redis kluczy do invalidacji. Stan na 2026-05-15:
# - `initial:*`              — GET /api/scoring-search/initial-data (1h TTL)
# - `ltr_fetchers:*`         — LTR DB lookups w core/ltr_db_fetchers.py (30min)
# - `search:*`               — multi-vector search (2min)
# - `similar:*`              — single-vehicle similar (3h)
# - `batch_similar_v2:*`     — batch similar (3h)
# - `model_normalizer:*`     — lazy-loaded SOT body types (after refactor)
DEFAULT_PATTERNS: tuple[str, ...] = (
    "initial:*",
    "ltr_fetchers:*",
    "search:*",
    "similar:*",
    "batch_similar_v2:*",
    "model_normalizer:*",
)


class InvalidateCacheResponse(BaseModel):
    """Odpowiedź endpointu invalidacji."""

    ok: bool
    redis_available: bool
    deleted_per_pattern: dict[str, int]
    total_deleted: int


def _check_admin_auth(authorization: str | None) -> None:
    """Walidacja `Authorization: Bearer <token>` przeciw `ADMIN_CACHE_TOKEN`."""
    expected = os.environ.get("ADMIN_CACHE_TOKEN", "")
    if not expected:
        # Brak konfiguracji = endpoint wyłączony. Inny niż 401, żeby było
        # jasne że to misconfiguration a nie zły token.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Endpoint wyłączony: brak `ADMIN_CACHE_TOKEN` w env. "
                "Ustaw zmienną i restartuj backend."
            ),
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagany nagłówek `Authorization: Bearer <token>`.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token.",
        )


@router.post(
    "/invalidate-cache",
    response_model=InvalidateCacheResponse,
    summary="Czyści Redis cache po edycji danych SOT w nakładce UI",
)
def invalidate_cache(
    authorization: str | None = Header(default=None),
) -> InvalidateCacheResponse:
    """Czyści wszystkie kluczowe prefixy Redis cache.

    Wywoływane przez Supabase Database Webhook po insert/update/delete w tabelach
    referencyjnych (body_types, samar_classes, samar_class_service_rates, …).

    Również wycieram lru_cache dla SOT body types (po refactorze
    model_normalizer.py).
    """
    _check_admin_auth(authorization)

    redis_ok = is_redis_available()
    deleted_per_pattern: dict[str, int] = {}

    for pattern in DEFAULT_PATTERNS:
        try:
            n = cache_invalidate_pattern(pattern)
            deleted_per_pattern[pattern] = n
        except Exception as exc:
            logger.warning("Błąd przy invalidacji '%s': %s", pattern, exc)
            deleted_per_pattern[pattern] = -1

    # Wyczyść lru_cache dla model_normalizer (lazy SOT body types).
    try:
        from core.model_normalizer import get_sot_body_types

        get_sot_body_types.cache_clear()
        logger.info("Wyczyszczono lru_cache: get_sot_body_types")
    except Exception as exc:
        logger.debug("Nie udało się wyczyścić lru_cache model_normalizer: %s", exc)

    total = sum(v for v in deleted_per_pattern.values() if v > 0)
    logger.info(
        "Cache invalidate: redis=%s, deleted=%d, per_pattern=%s",
        redis_ok,
        total,
        deleted_per_pattern,
    )
    return InvalidateCacheResponse(
        ok=True,
        redis_available=redis_ok,
        deleted_per_pattern=deleted_per_pattern,
        total_deleted=total,
    )


@router.get("/health", summary="Health check endpointu admina (bez autoryzacji)")
def admin_health() -> dict[str, str | bool]:
    """Lekki check — bez autoryzacji, żeby UI mogło sprawdzać że endpoint żyje."""
    return {
        "status": "ok",
        "redis_available": is_redis_available(),
        "auth_configured": bool(os.environ.get("ADMIN_CACHE_TOKEN")),
    }
