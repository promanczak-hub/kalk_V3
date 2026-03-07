"""Utilities for cleaning LLM responses containing JSON payloads."""

import logging
import re

logger = logging.getLogger(__name__)


def clean_json_response(text: str) -> str:
    """Clean up LLM responses that may contain markdown or preamble text.

    Handles:
    1. Markdown code blocks: ```json {...} ```
    2. Text preamble before JSON: "Here is the result:\n{...}"
    3. Empty / None responses → "{}"
    """
    if not text:
        return "{}"

    text = text.strip()

    # 1. Remove markdown code block syntax if present
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. Strip preamble: find first { or [ (JSON object / array start)
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            if i > 0:
                logger.debug(
                    "[JSON UTILS] Stripped %d-char preamble from LLM response",
                    i,
                )
            return text[i:]

    # 3. Return as-is (might be a plain value or error)
    return text
