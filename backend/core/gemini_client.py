"""Centralized Gemini client factory — single source of truth."""

import os

from google import genai
from google.genai import types


def get_gemini_client() -> genai.Client:
    """Create a Gemini client using API key or Vertex AI credentials."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return genai.Client(vertexai=True, project=project_id, location=location)


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
