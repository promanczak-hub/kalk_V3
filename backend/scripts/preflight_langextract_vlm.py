"""Pre-flight check for langextract VLM compatibility.

Purpose: verify that `langextract` (Google's structured extraction lib) actually
sends PDFs to Gemini in MULTIMODAL VISION mode — i.e. with page images so the
model can read dimensions from technical drawings, not just OCR text.

Decision: blocking. Run this BEFORE wiring langextract into pipeline_raw_extraction.

Usage:
    poetry run python scripts/preflight_langextract_vlm.py /path/to/test.pdf

Expected: a PDF whose dimensions appear ONLY on a technical drawing (no text
layer). If langextract returns those dimensions correctly → integrate it.
If it fails → keep the direct-Gemini-Vision fallback path (already implemented
in pipeline_raw_extraction).

The PDF you should test against is something like a cargo van offer with
a side-view diagram showing L/W/H mm values as drawing annotations.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


def main(pdf_path: str) -> int:
    path = Path(pdf_path)
    if not path.is_file():
        print(f"ERROR: PDF not found: {path}", file=sys.stderr)
        return 1

    # ── Step 1: import langextract (must be opt-in installed) ──
    try:
        import langextract  # type: ignore
    except ImportError:
        print(
            "langextract NOT installed. To run preflight:\n"
            "  poetry add langextract\n"
            "  poetry run python scripts/preflight_langextract_vlm.py <pdf>\n"
            "\n"
            "If you skip this, pipeline_raw_extraction will use the direct "
            "Gemini Vision fallback (already implemented). LangExtract is the "
            "OPT-IN path for character-offset grounding.",
            file=sys.stderr,
        )
        return 2

    # ── Step 2: build a minimal schema for cargo dimensions ──
    from pydantic import BaseModel, Field

    class CargoTestSchema(BaseModel):
        length_mm: Optional[int] = Field(
            default=None, description="Vehicle length in mm from a drawing"
        )
        width_mm: Optional[int] = Field(
            default=None, description="Vehicle width in mm from a drawing"
        )
        height_mm: Optional[int] = Field(
            default=None, description="Vehicle height in mm from a drawing"
        )

    # ── Step 3: run langextract on the PDF ──
    print(f"Testing langextract VLM on: {path}")
    pdf_bytes = path.read_bytes()
    try:
        result = langextract.extract(  # type: ignore[attr-defined]
            pdf_bytes,
            schema=CargoTestSchema,
        )
    except Exception as e:
        print(f"langextract.extract() raised: {e!r}", file=sys.stderr)
        return 3

    print("Result:")
    print(result)

    # ── Step 4: judge ──
    has_dimensions = any(
        getattr(result, attr, None) for attr in ("length_mm", "width_mm", "height_mm")
    )
    if has_dimensions:
        print("\nDECISION: VLM CAPABLE. Proceed with langextract integration.")
        print("Next: add `langextract` to backend/pyproject.toml main group,")
        print("      then set USE_LANGEXTRACT=1 in pipeline_raw_extraction.")
        return 0
    else:
        print(
            "\nDECISION: VLM FAILED (no dimensions extracted from drawing).",
            "\nKeep using the direct-Gemini-Vision fallback in pipeline_raw_extraction.",
        )
        return 4


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
