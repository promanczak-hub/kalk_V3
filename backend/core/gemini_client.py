"""Centralized Gemini client factory — single source of truth."""

import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


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
        return genai.Client(api_key=api_key)

    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(vertexai=True, project=project_id, location=location)
        logger.info(
            "Gemini client created via Vertex AI (project=%s, location=%s)",
            project_id,
            location,
        )
        return client
    except Exception as e:
        raise RuntimeError(
            "Brak konfiguracji Gemini! Ustaw zmienną GEMINI_API_KEY lub "
            "skonfiguruj Google Cloud credentials (gcloud auth application-default login). "
            f"Szczegóły: {e}"
        ) from e


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
