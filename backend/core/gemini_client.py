"""Centralized Gemini client factory — single source of truth."""

import logging
import os
from typing import Optional, Any

from google import genai
from google.genai import types

from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


def get_vertex_client() -> genai.Client:
    """Force creation of a Vertex AI client. Essential for Embeddings
    because public GEMINI_API_KEY fails with 404 on text-embedding-004.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        http_options=types.HttpOptions(
            timeout=600000.0
        ),  # 10 minut Max (w milisekundach)
    )


def get_gemini_client() -> genai.Client:
    """Create a Gemini client using API key or Vertex AI credentials.

    Priority:
    1. GEMINI_API_KEY env var → API key authentication
    2. Vertex AI (GOOGLE_CLOUD_PROJECT) → ADC / service account

    Raises
    ------
    RuntimeError
        If neither API key nor valid Google Cloud credentials are available.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=600000.0
            ),  # 10 minut Max (w milisekundach)
        )

    try:
        # Use the dedicated get_vertex_client function
        client = get_vertex_client()
        logger.info(
            "Gemini client created via Vertex AI (project=%s, location=%s)",
            os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz"),
            os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
        return client
    except Exception as e:
        raise RuntimeError(
            "Brak konfiguracji Gemini! Ustaw zmienną GEMINI_API_KEY lub "
            "skonfiguruj Google Cloud credentials (gcloud auth application-default login). "
            f"Szczegóły: {e}"
        ) from e


@retry(
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def generate_content_with_retry(
    client: genai.Client,
    model: str,
    contents: Any,
    config: Optional[types.GenerateContentConfig] = None,
    **kwargs,
) -> types.GenerateContentResponse:
    """Wrapper bazujący na tenacity do obsługi 503/429 z API Gemini."""
    return client.models.generate_content(
        model=model, contents=contents, config=config, **kwargs
    )


# ── Shared safety settings to prevent content blocking on business docs ──

SAFETY_SETTINGS_PERMISSIVE: list[types.SafetySetting] = [
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="BLOCK_ONLY_HIGH",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_ONLY_HIGH",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="BLOCK_ONLY_HIGH",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="BLOCK_ONLY_HIGH",
    ),
]
