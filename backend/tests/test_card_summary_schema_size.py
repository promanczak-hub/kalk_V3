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
- 2026-05-19 +ext-specs: CardSummary≈30820 (+option_code),
  VehicleExtractionSchema≈7406 (+EquipmentItem.code). Rich optional specs
  (tire labels, engine/towing/chassis detail, offer metadata) live in the
  SEPARATE ExtendedVehicleSpecs schema (own Gemini state budget) — see
  pipeline_extended_specs — precisely to avoid pushing the two schemas above
  past Gemini's "too many states" threshold.
- 2026-05-19 structural-slim: CardSummary≈24600. Char count was UNDER the
  ceiling (28679<32000) yet Gemini STILL rejected the schema (400 "too many
  states") on real offers. Char count is necessary but INSUFFICIENT — the
  dominant FSA drivers are enums + deeply nested arrays-of-objects, not text.
  Fix: SkipJsonSchema on backend-/HITL-filled fields (source_offsets grounding,
  conversion_source, rabat_* HITL choices) so they stay at runtime but leave
  the LLM schema. Pinned by test_card_summary_schema_excludes_backend_grounding.
"""

from __future__ import annotations

import json

from core.extractor_models import CardSummary
from core.pipeline_digital_twin import VehicleExtractionSchema
from core.pipeline_extended_specs import ExtendedVehicleSpecs


CARD_SUMMARY_CEILING_CHARS = 32_000
VEHICLE_EXTRACTION_CEILING_CHARS = 8_000
# ExtendedVehicleSpecs is a standalone structured-output schema with its own
# state budget. Keep it under the same generous ceiling as VehicleExtractionSchema
# (both succeed with Gemini at ~7.4k); a future PR that bloats it gets caught here.
EXTENDED_SPECS_CEILING_CHARS = 8_000


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
        "MASTER_PROMPT_V2. For NEW optional specs prefer ExtendedVehicleSpecs "
        "(separate schema, separate state budget) over bloating this one."
    )


def test_extended_specs_schema_under_ceiling() -> None:
    schema = json.dumps(ExtendedVehicleSpecs.model_json_schema())
    assert len(schema) < EXTENDED_SPECS_CEILING_CHARS, (
        f"ExtendedVehicleSpecs JSON schema is {len(schema)} chars — over the "
        f"{EXTENDED_SPECS_CEILING_CHARS} ceiling. This is the isolated specs "
        "pass; if it grows large, split it further rather than risking Gemini's "
        "'too many states' rejection on a single structured call."
    )


def _collect_enums(schema: object) -> list[list]:
    """Recursively gather every `enum` list anywhere in a JSON schema."""
    found: list[list] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if "enum" in node:
                found.append(node["enum"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    return found


def test_card_summary_schema_excludes_backend_grounding() -> None:
    """The Gemini response_schema must contain ONLY what the LLM produces.

    Char count is a NECESSARY but INSUFFICIENT trip-wire: the schema once sat
    at 28 679 chars (under the 32k ceiling) yet Gemini still rejected it with
    400 "too many states". The real state-machine drivers are enum members and
    deeply nested arrays-of-objects — not text length.

    Backend-/HITL-filled fields are SkipJsonSchema'd so they exist at runtime
    but never enter the LLM schema. This pins that: if a future PR drops
    SkipJsonSchema and the OffsetSpan/FieldOffset grounding nesting or the
    conversion_source / rabat_* Literals leak back in, the FSA re-explodes and
    extraction silently dies in prod.
    """
    schema = CardSummary.model_json_schema()
    blob = json.dumps(schema)

    # 3-level nested array-of-objects = the worst "too many states" multiplier.
    for forbidden in ("OffsetSpan", "FieldOffset"):
        assert forbidden not in blob, (
            f"{forbidden} leaked into the CardSummary response_schema. It's a "
            "backend-filled grounding model — wrap the field in SkipJsonSchema. "
            "Nested arrays-of-objects are the dominant 'too many states' driver."
        )

    # Only DiscountExtractionMethod (LLM-produced) should survive. The HITL/
    # backend Literals (conversion_source ×3, rabat_type, rabat_basis,
    # discount_scope) are SkipJsonSchema'd out — re-adding them was the 7-enum
    # state explosion that triggered the 2026-05-19 incident.
    enums = _collect_enums(schema)
    assert len(enums) <= 2, (
        f"CardSummary schema has {len(enums)} enums: {enums}. Each enum member "
        "is a state in Gemini's FSA. Only LLM-produced enums belong here; "
        "HITL/backend Literals must be SkipJsonSchema'd."
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
