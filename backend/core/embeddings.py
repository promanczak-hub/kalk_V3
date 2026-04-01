"""Utilities for generating AI vector embeddings using Gemini."""

import logging
from google.genai.errors import APIError
from core.gemini_client import get_vertex_client

logger = logging.getLogger(__name__)

# Primary model for fast, high-quality 768d vectors.
# We must use text-multilingual-embedding-002 on Vertex AI since public API 004 fails.
EMBEDDING_MODEL = "text-multilingual-embedding-002"


def generate_embedding(text: str) -> list[float] | None:
    """Generate a vector embedding for a given text using Gemini.

    Returns a list of 768 floats, or None if the API fails or text is empty.
    """
    if not text or not text.strip():
        return None

    client = get_vertex_client()
    try:
        logger.debug(
            "Generating embedding using client id=%s, type=%s, model=%s",
            id(client),
            type(client),
            EMBEDDING_MODEL,
        )
        logger.debug("Text length: %d", len(text.strip()))
        response = client.models.embed_content(
            model=EMBEDDING_MODEL, contents=text.strip()
        )
        if response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
    except APIError as e:
        logger.error(f"Gemini API Error during embedding generation: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error during embedding generation: {e}")

    return None


def build_vehicle_document(brand: str, model: str, synthesis_data: dict) -> str:
    """Compile a rich text document for a vehicle to be vectorized.

    We combine all meaningful fields into a natural language/structured string
    so that semantic search can reliably find it.
    """
    parts = []

    # Base identity
    parts.append(f"Pojazd: {brand} {model}")

    cs = synthesis_data.get("card_summary", {})
    if cs:
        parts.append(f"Wersja: {cs.get('trim_level', '')}")
        parts.append(
            f"Typ nadwozia: {cs.get('body_style', '')} ({cs.get('vehicle_class', '')})"
        )
        parts.append(
            f"Silnik: {cs.get('fuel', '')} {cs.get('power_hp', '')} KM, napęd {cs.get('drive_type', '')}, skrzynia {cs.get('transmission', '')}"
        )

    # Equipment
    std = cs.get("standard_equipment", [])
    if std:
        parts.append(
            "Wyposażenie standardowe: " + ", ".join(std[:20])
        )  # take top 20 to avoid token bloat

    paid = cs.get("paid_options", [])
    if paid:
        opts = [o.get("name") for o in paid if isinstance(o, dict) and o.get("name")]
        if opts:
            parts.append("Wyposażenie dodatkowe: " + ", ".join(opts[:20]))

    mapped = synthesis_data.get("mapped_ai_data", {})
    if mapped:
        parts.append(f"Opis ogólny: {mapped.get('description', '')}")

    # Join into a single string
    return "\n".join(parts)
