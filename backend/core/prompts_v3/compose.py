"""Top-level extraction prompt composer.

Combines:
- GENERIC_EXTRACTION_FRAME (language-agnostic, brand-agnostic)
- Auto-generated field instructions from the Pydantic schema
- Optional few-shot examples loaded from JSON
- Optional extra hints passed by the caller

Output is a single string ready to be passed to Gemini's `system_instruction`
or `contents[0].parts[0].text` slot. Deterministic — same inputs produce
identical output (stable for Anthropic prompt caching too).
"""

from __future__ import annotations

from pydantic import BaseModel

from core.prompts_v3.few_shot_loader import (
    load_few_shot_examples,
    render_few_shot_section,
)
from core.prompts_v3.field_doc_generator import build_field_instructions
from core.prompts_v3.frame import GENERIC_EXTRACTION_FRAME


def build_extraction_prompt(
    schema: type[BaseModel],
    examples_name: str | None = None,
    extra_hints: str | None = None,
    *,
    recurse_depth: int = 1,
) -> str:
    """Assemble a complete extraction prompt for a given Pydantic schema.

    Args:
        schema: Output schema (CardSummary, RawExtractionResult, etc.)
        examples_name: Few-shot category name (file
            `extraction_pipeline/few_shot/<name>.json`). None to skip examples.
        extra_hints: Free-form additional instructions appended at the end
            (e.g. context about the specific PDF being processed).
        recurse_depth: How deep to expand nested Pydantic models in the
            schema instructions section.

    Returns:
        A single prompt string. Order: frame → field docs → few-shot → hints.
    """
    sections: list[str] = [GENERIC_EXTRACTION_FRAME.strip(), ""]

    sections.append(build_field_instructions(schema, recurse_depth=recurse_depth))

    if examples_name:
        examples = load_few_shot_examples(examples_name)
        rendered = render_few_shot_section(examples)
        if rendered:
            sections.append(rendered)

    if extra_hints:
        sections.append("## Dodatkowe wskazówki")
        sections.append(extra_hints.strip())

    return "\n".join(sections).rstrip() + "\n"
