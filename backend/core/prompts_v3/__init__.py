"""Composable, schema-first extraction prompts for the V3 pipeline.

Replaces hardcoded ~4000-word MASTER_PROMPT_V2 in `core.prompts` with a
builder that:

1. Loads a generic, language-agnostic frame (see `frame.GENERIC_EXTRACTION_FRAME`).
2. Auto-generates field-by-field instructions from a Pydantic schema
   (see `field_doc_generator.build_field_instructions`). Single source of
   truth = the model's `Field(description=...)`.
3. Optionally pulls versioned few-shot examples from
   `backend/extraction_pipeline/few_shot/*.json`.
4. Composes everything into one prompt string with `build_extraction_prompt`.

Zero hardcoded brand/model names — the prompt is the same for any vehicle.
"""

from __future__ import annotations

from core.prompts_v3.compose import build_extraction_prompt
from core.prompts_v3.few_shot_loader import load_few_shot_examples
from core.prompts_v3.field_doc_generator import build_field_instructions
from core.prompts_v3.frame import GENERIC_EXTRACTION_FRAME

__all__ = [
    "GENERIC_EXTRACTION_FRAME",
    "build_extraction_prompt",
    "build_field_instructions",
    "load_few_shot_examples",
]
