import json
import os
from typing import Union
from google import genai
from google.genai import types

from core.json_utils import clean_json_response
from core.prompts import MASTER_PROMPT_V2


def extract_digital_twin_from_pdf(
    document_data: Union[str, bytes], mime_type: str = "application/pdf"
) -> dict:
    """
    Extracts a raw JSON digital twin representation of the document using Gemini 2.5 Pro.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(vertexai=True, project=project_id, location=location)

    model_id = "gemini-2.5-pro"

    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        system_instruction=MASTER_PROMPT_V2,
    )

    if isinstance(document_data, bytes):
        contents: list[types.Part] = [
            types.Part.from_bytes(data=document_data, mime_type=mime_type),
        ]
    else:
        contents = [types.Part.from_text(text=document_data)]

    response = client.models.generate_content(
        model=model_id,
        contents=contents,
        config=config,
    )

    pro_response_text = getattr(response, "text", "{}") or "{}"

    try:
        pro_data = json.loads(clean_json_response(pro_response_text))
    except json.JSONDecodeError:
        pro_data = {}

    return pro_data
