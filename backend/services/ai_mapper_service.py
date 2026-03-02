import json
import os
from enum import Enum
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from typing import Dict, Any

from core.json_utils import clean_json_response


class FuelType(str, Enum):
    PB = "Benzyna (PB)"
    ON = "Diesel (ON)"
    PB_MHEV = "Benzyna mHEV (PB-mHEV)"
    ON_MHEV = "Diesel mHEV (ON-mHEV)"
    LPG = "Autogaz (LPG)"
    BEV = "Elektryczny (BEV)"
    HEV = "Hybryda (HEV)"
    PHEV = "Hybryda Plug-in (PHEV)"
    FCEV = "Wodór (FCEV)"


class VehicleTypeType(str, Enum):
    OSOBOWY = "Osobowy"
    CIEZAROWY = "Ciężarowy"


class MappedVehicleData(BaseModel):
    brand: str = Field(
        ..., description="Zmapowana marka pojazdu, np. Volkswagen, Toyota."
    )
    model: str = Field(
        ..., description="Zmapowany model pojazdu, np. Crafter, Corolla."
    )
    trim_level: str = Field(..., description="Wersja wyposażenia pojazdu.")
    fuel: FuelType = Field(
        ..., description="Rodzaj paliwa wybrany ściśle z dostępnej listy."
    )
    transmission: str = Field(
        ...,
        description="Skrzynia biegów i ewentualnie rodzaj napędu (np. Automatyczna AWD).",
    )
    vehicle_type: VehicleTypeType = Field(
        ..., description="Typ pojazdu (osobowy / ciężarowy)."
    )


SYSTEM_PROMPT = """Jesteś ekspertem ds. analizy danych motoryzacyjnych.
Twoim zadaniem jest na bazie przekazanego surowego JSONA z danymi pojazdu zwrócić obiekt zgodny ze schematem.
Masz zakaz halucynacji. Musisz zdeterminować `vehicle_type` na podstawie modelu (np. Volkswagen Crafter to zazwyczaj ciężarowy furgon, a Golf to osobowy) oraz danych w JSONie.
Paliwo `fuel` musi zostać kategorycznie zmapowane TYLKO do jednego z dozwolonych typów wyliczeniowych w systemie. Jeśli brakuje danych, zdedukuj najbardziej logiczny typ dla tego pojazdu, nie wolno Ci zwrócić NULL ani błędnego klucza. Zawsze musisz zwrócić kompletny JSON.
"""


def map_vehicle_data_flash(original_json: Dict[str, Any]) -> dict:
    """
    Takes original extracted JSON and forces Gemini Flash to map attributes
    strictly into the MappedVehicleData Pydantic schema to prevent hallucinations
    and enforce specific enums (e.g. Fuel Type).
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "express-handlorz")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(vertexai=True, project=project_id, location=location)

    flash_model_id = "gemini-2.5-flash"

    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=MappedVehicleData,
        system_instruction=SYSTEM_PROMPT,
    )

    prompt = f"Oryginalny JSON do zmapowania:\n{json.dumps(original_json, ensure_ascii=False)}"

    try:
        print("[AI MAPPER] Wysyłam zapytanie do Gemini API...")
        response = client.models.generate_content(
            model=flash_model_id,
            contents=[types.Part.from_text(text=prompt)],
            config=config,
        )

        print("[AI MAPPER] Otrzymano odpowiedź z Gemini API.")
        resp_text = getattr(response, "text", "{}") or "{}"
        mapped_data = json.loads(clean_json_response(str(resp_text)))
        print(
            f"[AI MAPPER] Pomyślnie zmapowano dane: {mapped_data.get('brand')} {mapped_data.get('model')}"
        )
        return mapped_data
    except Exception as e:
        print(f"Error mapping vehicle data with AI: {e}")
        # Return a fallback matching the schema to not break the frontend
        return {
            "brand": "Błąd mapowania",
            "model": "Brak",
            "trim_level": "Brak",
            "fuel": "Benzyna (PB)",
            "transmission": "Brak",
            "vehicle_type": "Osobowy",
        }
