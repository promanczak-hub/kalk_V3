import json
import os
from typing import Union
from google import genai
from google.genai import types

from core.json_utils import clean_json_response
from core.prompts import SERVICE_OPTION_DIGITAL_TWIN_PROMPT
from core.extractor_models import ServiceOptionDigitalTwin


def extract_service_option_from_pdf(
    document_data: Union[str, bytes], mime_type: str = "application/pdf"
) -> dict:
    """
    Extracts a ServiceOptionDigitalTwin representation of the document using Gemini.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(vertexai=True, project=project_id, location=location)

    # Use gemini-2.5-pro or flash depending on requirements, flash usually sufficient for simple extraction
    model_id = "gemini-2.5-flash"

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=ServiceOptionDigitalTwin,
        system_instruction=SERVICE_OPTION_DIGITAL_TWIN_PROMPT,
    )

    if isinstance(document_data, bytes):
        contents: list[types.Part] = [
            types.Part.from_bytes(data=document_data, mime_type=mime_type),
        ]
    else:
        contents = [types.Part.from_text(text=document_data)]

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=config,
        )

        response_text = getattr(response, "text", "{}") or "{}"
        data = json.loads(clean_json_response(response_text))
        return data

    except Exception as e:
        print(f"Error in extract_service_option_from_pdf: {e}")
        return {}
