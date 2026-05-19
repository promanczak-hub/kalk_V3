"""Tests for prompts_v3 package — composable prompt-as-data builder.

Schema-first principle: prompt is BUILT from Pydantic Field descriptions
+ generic frame + few-shot examples. No hardcoded brand/model strings.
"""

from __future__ import annotations

from typing import Optional

import pytest
from pydantic import BaseModel, Field

from core.prompts_v3 import (
    GENERIC_EXTRACTION_FRAME,
    build_extraction_prompt,
    build_field_instructions,
    load_few_shot_examples,
)


# ═══════════════════════════════════════════════════════════════════
# build_field_instructions — Pydantic schema → markdown
# ═══════════════════════════════════════════════════════════════════


class SimpleSchema(BaseModel):
    name: str = Field(description="The name of the thing")
    price: Optional[float] = Field(
        default=None, description="Price in PLN, null if unknown"
    )


class NestedSchema(BaseModel):
    main: SimpleSchema
    extras: list[SimpleSchema] = Field(
        default_factory=list, description="Extra items"
    )


class TestBuildFieldInstructions:
    def test_includes_every_field_name(self) -> None:
        instructions = build_field_instructions(SimpleSchema)
        assert "name" in instructions
        assert "price" in instructions

    def test_includes_descriptions(self) -> None:
        instructions = build_field_instructions(SimpleSchema)
        assert "The name of the thing" in instructions
        assert "Price in PLN, null if unknown" in instructions

    def test_marks_required_vs_optional(self) -> None:
        instructions = build_field_instructions(SimpleSchema)
        # `name` is required (no default), `price` is optional
        # Look for marker — convention: "(required)" / "(optional)" or "*"
        name_section = _section_for(instructions, "name")
        price_section = _section_for(instructions, "price")
        assert "required" in name_section.lower() or "*" in name_section
        assert "optional" in price_section.lower() or "default" in price_section.lower()

    def test_handles_nested_model(self) -> None:
        instructions = build_field_instructions(NestedSchema)
        # Should mention the nested type
        assert "main" in instructions
        assert "extras" in instructions

    def test_zero_brand_names_hardcoded(self) -> None:
        """The instruction text must NOT contain hardcoded brands.

        Schema descriptions live in extractor_models.py — they should be
        generic, not 'For BMW, do X; for Audi, do Y'.
        """
        instructions = build_field_instructions(SimpleSchema)
        forbidden = ["BMW", "Audi", "Mercedes", "Skoda", "VW", "Volkswagen", "Ford"]
        for brand in forbidden:
            assert brand not in instructions, (
                f"Hardcoded brand {brand!r} leaked into prompt"
            )


def _section_for(text: str, field_name: str) -> str:
    """Extract the snippet around a field name from rendered markdown."""
    lower = text.lower()
    idx = lower.find(field_name.lower())
    if idx < 0:
        return ""
    return text[idx : idx + 200]


# ═══════════════════════════════════════════════════════════════════
# GENERIC_EXTRACTION_FRAME — language-agnostic frame
# ═══════════════════════════════════════════════════════════════════


class TestGenericFrame:
    def test_frame_is_non_empty(self) -> None:
        assert len(GENERIC_EXTRACTION_FRAME) > 100

    def test_frame_mentions_no_invent_rule(self) -> None:
        lower = GENERIC_EXTRACTION_FRAME.lower()
        # Should contain "literally" or "do not invent" or "verbatim"
        assert any(
            keyword in lower
            for keyword in ("literal", "verbatim", "do not invent", "zero halucynacji")
        )

    def test_frame_mentions_multimodal_vision(self) -> None:
        lower = GENERIC_EXTRACTION_FRAME.lower()
        # Should reference looking at drawings, diagrams, technical images
        assert any(
            kw in lower for kw in ("drawing", "rysunek", "diagram", "visual", "wizualny")
        )

    def test_frame_zero_brand_names(self) -> None:
        forbidden = ["BMW", "Audi", "Skoda", "Mercedes", "Volkswagen", "Ford"]
        for brand in forbidden:
            assert brand not in GENERIC_EXTRACTION_FRAME

    def test_frame_mentions_multi_language(self) -> None:
        lower = GENERIC_EXTRACTION_FRAME.lower()
        # Should mention language-agnostic / multi-language
        assert any(
            kw in lower
            for kw in ("language", "język", "languages", "multi-language", "polski")
        )


# ═══════════════════════════════════════════════════════════════════
# load_few_shot_examples
# ═══════════════════════════════════════════════════════════════════


class TestLoadFewShotExamples:
    def test_returns_list(self) -> None:
        # Empty/missing example set returns empty list, not crash
        result = load_few_shot_examples("nonexistent_category_xyz")
        assert result == []

    def test_loads_existing_set_if_present(self, tmp_path, monkeypatch) -> None:
        # Create a temporary few-shot directory and example file
        fs_dir = tmp_path / "few_shot"
        fs_dir.mkdir()
        (fs_dir / "test_set.json").write_text(
            '[{"input_snippet": "test input", "expected": {"x": 1}}]',
            encoding="utf-8",
        )
        monkeypatch.setenv("KALK_FEW_SHOT_DIR", str(fs_dir))
        result = load_few_shot_examples("test_set")
        assert len(result) == 1
        assert result[0]["input_snippet"] == "test input"
        assert result[0]["expected"] == {"x": 1}

    def test_malformed_json_raises_clear_error(self, tmp_path, monkeypatch) -> None:
        fs_dir = tmp_path / "few_shot"
        fs_dir.mkdir()
        (fs_dir / "bad.json").write_text("{not valid json", encoding="utf-8")
        monkeypatch.setenv("KALK_FEW_SHOT_DIR", str(fs_dir))
        with pytest.raises((ValueError, Exception)):
            load_few_shot_examples("bad")


# ═══════════════════════════════════════════════════════════════════
# build_extraction_prompt — top-level composer
# ═══════════════════════════════════════════════════════════════════


class TestBuildExtractionPrompt:
    def test_includes_frame_and_field_instructions(self) -> None:
        prompt = build_extraction_prompt(SimpleSchema)
        # Should include the generic frame
        assert GENERIC_EXTRACTION_FRAME.strip().split("\n")[0] in prompt
        # Should include field instructions
        assert "name" in prompt
        assert "price" in prompt

    def test_few_shot_examples_optional(self) -> None:
        # No examples_name → no example section
        prompt = build_extraction_prompt(SimpleSchema, examples_name=None)
        # We don't fail when examples are absent
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_extra_hints_appended(self) -> None:
        prompt = build_extraction_prompt(
            SimpleSchema, extra_hints="Custom hint about extraction"
        )
        assert "Custom hint about extraction" in prompt

    def test_no_hardcoded_brand_in_output(self) -> None:
        prompt = build_extraction_prompt(SimpleSchema, extra_hints="extra")
        forbidden = ["BMW", "Audi", "Mercedes", "Skoda", "Volkswagen", "Ford"]
        for brand in forbidden:
            assert brand not in prompt

    def test_deterministic_output(self) -> None:
        # Same inputs → same output (stable for prompt-caching)
        a = build_extraction_prompt(SimpleSchema)
        b = build_extraction_prompt(SimpleSchema)
        assert a == b
