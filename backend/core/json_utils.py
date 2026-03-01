import re


def clean_json_response(text: str) -> str:
    """
    Cleans up LLM responses that might contain markdown formatting around the JSON payload.
    It strips leading/trailing whitespaces and removes ```json and ``` blocks.
    """
    if not text:
        return "{}"

    text = text.strip()

    # Remove markdown code block syntax if present
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    return text
