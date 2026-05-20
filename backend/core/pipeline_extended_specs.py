"""Extended vehicle specs — isolated, purely-informational Flash extraction pass.

WHY a separate pass (decision 2026-05-19):
  The primary `VehicleExtractionSchema` (pipeline_digital_twin) sits at ~7.2k/8k
  chars of its Gemini structured-output budget. Pushing it past the "too many
  states" threshold makes EVERY extraction hard-fail to status=error (there is
  no free-form fallback — see pipeline_digital_twin._call_gemini_pro). So the
  rich-but-optional data the user wants (tire labels, engine RPM/torque, towing
  limits, chassis, offer metadata) is extracted in a SECOND, isolated Flash call
  with its OWN schema and OWN state budget. It can never break the primary twin.

CONTRACT:
  - NON-FATAL: any failure (rejection, timeout, parse) returns {} and is logged.
    The caller merges into digital_twin.extended_specs only when non-empty.
  - INFORMATIONAL ONLY: nothing here feeds the 12-stage calculation. The calc
    reads card_summary fields explicitly (ltr_vehicle_resolvers), and this data
    lives under digital_twin.extended_specs — never copied into the calc payload.

Feature flag: EXTRACTION_EXTENDED_SPECS (default "1" = on; "0" = skip the call).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from google.genai import types
from pydantic import BaseModel, Field

from core.gemini_client import (
    SAFETY_SETTINGS_PERMISSIVE,
    generate_content_with_retry,
    resolve_max_output_tokens,
)
from core.json_utils import clean_json_response

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Schema (own state budget — independent of VehicleExtractionSchema)
# ─────────────────────────────────────────────────────────────────────


class TireLabelSpec(BaseModel):
    """Etykieta opony EU 2020/740 — wyłącznie informacyjna."""

    manufacturer: Optional[str] = Field(None, description="Producent, np. Bridgestone")
    name: Optional[str] = Field(None, description="Nazwa handlowa, np. Turanza 6")
    size: Optional[str] = Field(None, description="Rozmiar, np. 235/45 R18 98Y")
    fuel_class: Optional[str] = Field(None, description="Klasa efektywności paliwowej A-E")
    wet_grip_class: Optional[str] = Field(None, description="Klasa przyczepności na mokrym A-E")
    noise_class: Optional[str] = Field(None, description="Klasa hałasu A-C")
    noise_db: Optional[int] = Field(None, description="Hałas zewnętrzny w dB")
    snow: Optional[bool] = Field(None, description="Opona zimowa (3PMSF)")
    ice: Optional[bool] = Field(None, description="Przyczepność na lodzie")


class EngineSpec(BaseModel):
    cylinders: Optional[int] = Field(None, description="Liczba cylindrów")
    max_torque_nm: Optional[int] = Field(None, description="Maks. moment obrotowy (Nm)")
    max_power_rpm: Optional[str] = Field(None, description="Obroty maks. mocy, np. '3900-6000'")
    max_torque_rpm: Optional[str] = Field(None, description="Obroty maks. momentu obrotowego")
    top_speed_kmh: Optional[int] = Field(None, description="Prędkość maksymalna (km/h)")
    acceleration_0_100_s: Optional[float] = Field(None, description="Przyspieszenie 0-100 km/h (s)")
    emission_standard: Optional[str] = Field(None, description="Norma emisji, np. Euro 6e")


class TransmissionSpec(BaseModel):
    name: Optional[str] = Field(None, description="Nazwa handlowa, np. '7-biegowa DSG'")
    gears: Optional[int] = Field(None, description="Liczba biegów")
    clutch: Optional[str] = Field(None, description="Typ sprzęgła")


class TowingSpec(BaseModel):
    """Holowanie — informacyjne, brak wpływu na kalkulację."""

    trailer_braked_kg: Optional[int] = Field(None, description="Maks. masa przyczepy z hamulcem (kg)")
    trailer_unbraked_kg: Optional[int] = Field(None, description="Maks. masa przyczepy bez hamulca (kg)")
    roof_load_kg: Optional[int] = Field(None, description="Maks. obciążenie dachu (kg)")
    hitch_load_kg: Optional[int] = Field(None, description="Maks. nacisk pionowy na hak (kg)")


class ChassisSpec(BaseModel):
    turning_radius_m: Optional[float] = Field(None, description="Średnica zawracania (m)")
    front_suspension: Optional[str] = Field(None, description="Zawieszenie przednie")
    rear_suspension: Optional[str] = Field(None, description="Zawieszenie tylne")


class WltpSpec(BaseModel):
    """Zużycie wg cykli WLTP (l/100km lub kWh/100km dla EV)."""

    low: Optional[float] = Field(None, description="Cykl niski")
    medium: Optional[float] = Field(None, description="Cykl średni")
    high: Optional[float] = Field(None, description="Cykl wysoki")
    very_high: Optional[float] = Field(None, description="Cykl bardzo wysoki")
    combined: Optional[float] = Field(None, description="Cykl mieszany")


class ExtendedVehicleSpecs(BaseModel):
    """Dodatkowe, czysto informacyjne specyfikacje pojazdu.

    Wyciągane osobnym przebiegiem Flash i zapisywane do
    digital_twin.extended_specs. NIE wpływa na kalkulację.
    """

    model_year: Optional[int] = Field(None, description="Rok modelowy")
    production_year: Optional[int] = Field(None, description="Rok produkcji")
    offer_valid_until: Optional[str] = Field(None, description="Data ważności oferty (jak w dokumencie)")
    salesperson: Optional[str] = Field(None, description="Handlowiec: imię, telefon, e-mail")
    client_name: Optional[str] = Field(None, description="Nazwa klienta z oferty")
    configurator_url: Optional[str] = Field(None, description="URL konfiguracji producenta")
    engine: Optional[EngineSpec] = Field(None, description="Szczegóły techniczne silnika")
    transmission: Optional[TransmissionSpec] = Field(None, description="Szczegóły skrzyni biegów")
    towing: Optional[TowingSpec] = Field(None, description="Parametry holowania")
    chassis: Optional[ChassisSpec] = Field(None, description="Podwozie / zawieszenie")
    wltp: Optional[WltpSpec] = Field(None, description="Zużycie wg cykli WLTP")
    tire_labels: list[TireLabelSpec] = Field(
        default_factory=list, description="Etykiety opon EU 2020/740 (jeśli obecne)"
    )


# ─────────────────────────────────────────────────────────────────────
# Prompt — language-agnostic, extract-if-present, never invent
# ─────────────────────────────────────────────────────────────────────

_EXTENDED_SPECS_PROMPT = (
    "Jesteś ekstraktorem dodatkowych, czysto informacyjnych danych technicznych "
    "pojazdu z dokumentu (oferta / konfiguracja / cennik). Wypełnij pola schematu "
    "WYŁĄCZNIE wartościami widocznymi wprost w dokumencie (tekst lub rysunki/tabele). "
    "Nie zgaduj, nie wnioskuj, nie obliczaj — jeśli danej wartości nie ma, zostaw null "
    "(lub pustą listę dla tire_labels). Przepisuj liczby dokładnie. Działaj dla dowolnej "
    "marki i dowolnego języka oferty. Etykiety opon (EU 2020/740) wyciągaj tylko jeśli "
    "fizycznie są w dokumencie — mogą być 1-4 różne opony, każda jako osobny wpis."
)


def extract_extended_specs(client: Any, contents: list[Any]) -> dict[str, Any]:
    """Run the isolated Flash extended-specs pass on already-built `contents`.

    Args:
        client: Gemini client (reused from the primary digital-twin call).
        contents: the SAME parts list (markdown text + PDF bytes) the primary
            extraction used — avoids re-encoding the document.

    Returns:
        Parsed ExtendedVehicleSpecs as a plain dict, or {} on any failure / when
        disabled via EXTRACTION_EXTENDED_SPECS=0. NEVER raises.
    """
    if (os.environ.get("EXTRACTION_EXTENDED_SPECS") or "1").strip().lower() in ("0", "off", "false"):
        return {}

    config = types.GenerateContentConfig(
        temperature=0.0,
        seed=42,
        max_output_tokens=resolve_max_output_tokens(),
        response_mime_type="application/json",
        response_schema=ExtendedVehicleSpecs,
        system_instruction=_EXTENDED_SPECS_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )
    try:
        response = generate_content_with_retry(
            client=client,
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )
        raw = getattr(response, "text", "{}") or "{}"
        data = json.loads(clean_json_response(raw))
        if not isinstance(data, dict):
            return {}
        logger.info("[EXTENDED SPECS] extracted %d top-level keys", len(data))
        return data
    except Exception as e:  # noqa: BLE001 — isolation is the whole point
        # NON-FATAL by contract: extended specs must never break the primary twin.
        logger.warning("[EXTENDED SPECS] non-fatal failure, skipping: %s", e)
        return {}
