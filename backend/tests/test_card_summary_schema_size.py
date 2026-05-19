"""Schema-size pin for CardSummary / VehicleExtractionSchema.

Gemini's structured-output engine rejects schemas that produce a constraint
state machine with "too many states for serving" (400 INVALID_ARGUMENT).
Long descriptions, large enums, and complex nested Literal unions all
contribute. CardSummary previously exceeded this threshold for some
documents, silently degrading to empty card_summary + Frankenstein
backfills.

This test pins schema size below a generous ceiling so a future PR that
re-adds a multi-paragraph description / 9-member enum gets caught in CI
instead of in production. The ceiling is intentionally loose — it's a
trip-wire, not an upper bound on what's "OK".

Historical baselines (chars in `json.dumps(model.model_json_schema())`):
- 2026-05-19 pre-slim:  CardSummary=34658, VehicleExtractionSchema=7228
- 2026-05-19 post-slim: CardSummary≈30600, VehicleExtractionSchema=7228
"""

from __future__ import annotations

import json

from core.extractor_models import CardSummary
from core.pipeline_digital_twin import VehicleExtractionSchema


CARD_SUMMARY_CEILING_CHARS = 32_000
VEHICLE_EXTRACTION_CEILING_CHARS = 8_000


def test_card_summary_schema_under_ceiling() -> None:
    schema = json.dumps(CardSummary.model_json_schema())
    assert len(schema) < CARD_SUMMARY_CEILING_CHARS, (
        f"CardSummary JSON schema is {len(schema)} chars — over the "
        f"{CARD_SUMMARY_CEILING_CHARS} ceiling. Adding fields with long "
        "Polish descriptions or 5+ member enums pushes Gemini into '400 "
        "INVALID_ARGUMENT: too many states for serving'. Move extraction "
        "rules into CARD_SUMMARY_PROMPT (core/prompts.py) instead of "
        "description= on the Pydantic field, and prefer `str` over enums "
        "where downstream code doesn't switch on enum members."
    )


def test_vehicle_extraction_schema_under_ceiling() -> None:
    schema = json.dumps(VehicleExtractionSchema.model_json_schema())
    assert len(schema) < VEHICLE_EXTRACTION_CEILING_CHARS, (
        f"VehicleExtractionSchema JSON schema is {len(schema)} chars — over "
        f"the {VEHICLE_EXTRACTION_CEILING_CHARS} ceiling. Same root cause as "
        "CardSummary — keep field descriptions short, push rules into "
        "MASTER_PROMPT_V2."
    )


def test_card_summary_accepts_arbitrary_engine_category() -> None:
    """engine_category was migrated from Optional[NapedTyp] to Optional[str]
    to reduce schema state count. Downstream code does string comparison,
    so we accept any string here intentionally — validation now lives in
    the prompt + post-processing, not in Pydantic.
    """
    schema = CardSummary.model_json_schema()
    engine_cat_schema = schema["properties"]["engine_category"]
    # Must allow any string (and null), NOT be a fixed enum
    assert "enum" not in engine_cat_schema, (
        "engine_category re-grew an enum — that's exactly what we removed. "
        "Keep as Optional[str] and document valid values in the description."
    )
