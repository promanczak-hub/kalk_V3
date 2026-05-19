"""Lazy loader for versioned few-shot examples (JSON files).

Convention: each category lives in
`backend/extraction_pipeline/few_shot/<name>.json` as a JSON list of
`{"input_snippet": str, "expected": {...}}` entries.

Override the search directory via `KALK_FEW_SHOT_DIR` env var (used in tests
and shadow runs).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# prompts_v3/few_shot_loader.py is at backend/core/prompts_v3/few_shot_loader.py
# Default few-shot dir: backend/core/extraction_pipeline/few_shot/
_DEFAULT_DIR = (
    Path(__file__).resolve().parent.parent / "extraction_pipeline" / "few_shot"
)


def _resolve_dir() -> Path:
    override = os.environ.get("KALK_FEW_SHOT_DIR")
    if override:
        return Path(override)
    return _DEFAULT_DIR


def load_few_shot_examples(name: str) -> list[dict[str, Any]]:
    """Load a named few-shot example set from disk.

    Returns an empty list if the file doesn't exist (graceful fallback —
    prompts work without examples, just less guided).

    Raises ValueError if the file is present but malformed.
    """
    directory = _resolve_dir()
    path = directory / f"{name}.json"
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Few-shot file {path} is not valid JSON: {e}"
        ) from e
    if not isinstance(data, list):
        raise ValueError(
            f"Few-shot file {path} must contain a JSON list at top level, "
            f"got {type(data).__name__}"
        )
    return data


def render_few_shot_section(examples: list[dict[str, Any]]) -> str:
    """Render a few-shot list as markdown for inclusion in a prompt."""
    if not examples:
        return ""
    parts = ["## Few-shot examples", ""]
    for i, ex in enumerate(examples, start=1):
        parts.append(f"### Example {i}")
        snippet = ex.get("input_snippet", "")
        expected = ex.get("expected", {})
        parts.append("**Input snippet:**")
        parts.append(f"```\n{snippet}\n```")
        parts.append("**Expected JSON:**")
        try:
            rendered = json.dumps(expected, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            rendered = str(expected)
        parts.append(f"```json\n{rendered}\n```")
        parts.append("")
    return "\n".join(parts)
