"""V3 PASS A — RAW extraction (Gemini Pro multimodal vision).

Pulls LITERAL quoted values from the PDF with grounding info (page + optional
bbox). No normalization, no VAT inference, no categorization — Pass B does that.

Two execution paths:
- DEFAULT (always works): direct `gemini_client.generate_content_with_retry`
  with `response_schema=RawExtractionResult` + `inline_data: application/pdf`.
  Gemini renders pages as images internally (multimodal vision).
- OPT-IN (`USE_LANGEXTRACT=1`): `langextract.extract()` for character-offset
  grounding. Only enable after passing `scripts/preflight_langextract_vlm.py`.

Output: `RawExtractionResult` Pydantic model (see extractor_models).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from google.genai import types

from core.extractor_models import RawExtractionResult
from core.gemini_client import (
    SAFETY_SETTINGS_PERMISSIVE,
    generate_content_with_retry,
    get_gemini_client,
)
from core.prompts_v3 import build_extraction_prompt

logger = logging.getLogger(__name__)


DEFAULT_PRO_MODEL = "gemini-2.5-pro"


def extract_raw_from_pdf(
    pdf_bytes: bytes,
    *,
    model: str = DEFAULT_PRO_MODEL,
    examples_name: str = "vat_inference",
    extra_hints: str | None = None,
) -> RawExtractionResult:
    """Run PASS A — RAW multimodal extraction on a PDF.

    Args:
        pdf_bytes: Raw bytes of the PDF document.
        model: Gemini model name. Default `gemini-2.5-pro` for vision quality.
        examples_name: Few-shot category name to load from
            `extraction_pipeline/few_shot/<name>.json`. Defaults to VAT
            examples; switch to "visual_dimensions" when extracting drawings.
        extra_hints: Optional caller-supplied hint text.

    Returns:
        A `RawExtractionResult` with literal price/option/dimension quotes.

    Notes:
        Multimodal: PDF bytes go to Gemini via `inline_data: application/pdf` →
        Gemini renders pages as images internally, so technical drawings ARE
        read visually. No OCR text-only mode.
    """
    if os.environ.get("USE_LANGEXTRACT") == "1":
        return _extract_via_langextract(pdf_bytes, examples_name=examples_name)

    return _extract_via_gemini_direct(
        pdf_bytes,
        model=model,
        examples_name=examples_name,
        extra_hints=extra_hints,
    )


def _extract_via_gemini_direct(
    pdf_bytes: bytes,
    *,
    model: str,
    examples_name: str,
    extra_hints: str | None,
) -> RawExtractionResult:
    """Default path: Gemini Pro multimodal vision via response_schema."""
    prompt = build_extraction_prompt(
        RawExtractionResult,
        examples_name=examples_name,
        extra_hints=extra_hints,
    )

    client = get_gemini_client()
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RawExtractionResult,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        system_instruction=prompt,
        temperature=0.0,
    )

    contents = [
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        "Wyciągnij RAW dane z tego PDF zgodnie z instrukcjami.",
    ]

    logger.info(
        "PASS A — RAW extraction via direct Gemini (%s, %d bytes PDF)",
        model,
        len(pdf_bytes),
    )

    response = generate_content_with_retry(
        client=client, model=model, contents=contents, config=config
    )

    # Parse JSON response into Pydantic model
    raw_text = response.text or "{}"
    try:
        payload: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("PASS A returned non-JSON response: %s", e)
        return RawExtractionResult()  # empty — pipeline_normalization handles gracefully

    try:
        return RawExtractionResult.model_validate(payload)
    except Exception as e:
        logger.error("PASS A JSON did not match RawExtractionResult schema: %s", e)
        return RawExtractionResult()


def _extract_via_langextract(
    pdf_bytes: bytes,
    *,
    examples_name: str,
) -> RawExtractionResult:
    """Opt-in path: langextract for character-offset grounding.

    Only enable after `scripts/preflight_langextract_vlm.py` confirms that
    langextract sends PDFs to Gemini in multimodal mode (reads drawings).
    """
    try:
        import langextract  # type: ignore
    except ImportError:
        logger.warning(
            "USE_LANGEXTRACT=1 but langextract not installed. Falling back to direct."
        )
        return _extract_via_gemini_direct(
            pdf_bytes,
            model=DEFAULT_PRO_MODEL,
            examples_name=examples_name,
            extra_hints=None,
        )

    from core.prompts_v3 import load_few_shot_examples

    examples = load_few_shot_examples(examples_name)
    logger.info(
        "PASS A — RAW extraction via langextract (%d examples loaded)", len(examples)
    )
    try:
        result = langextract.extract(  # type: ignore[attr-defined]
            pdf_bytes,
            schema=RawExtractionResult,
            examples=examples,
        )
    except Exception as e:
        logger.error("langextract.extract() failed: %s — falling back to direct", e)
        return _extract_via_gemini_direct(
            pdf_bytes,
            model=DEFAULT_PRO_MODEL,
            examples_name=examples_name,
            extra_hints=None,
        )

    # langextract returns a Pydantic instance if schema is a Pydantic model
    if isinstance(result, RawExtractionResult):
        return result
    # Otherwise it returned dict-like — coerce
    if isinstance(result, dict):
        return RawExtractionResult.model_validate(result)
    logger.warning("langextract returned unexpected type %s", type(result))
    return RawExtractionResult()
