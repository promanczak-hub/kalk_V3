"""Utilities for generating AI vector embeddings using Gemini."""

import logging
from google.genai.errors import APIError

logger = logging.getLogger(__name__)

# Primary model for fast, high-quality 768d vectors.
# We must use text-multilingual-embedding-002 on Vertex AI since public API 004 fails.
EMBEDDING_MODEL = "text-multilingual-embedding-002"


def generate_embedding(text: str) -> list[float] | None:
    """Generate a vector embedding for a given text using Gemini.

    Returns a list of 768 floats, or None if the API fails or text is empty.
    """
    if not text or not text.strip():
        return None

    # Use the standard client which will pick up the Vertex Express API Key
    from core.gemini_client import get_gemini_client

    client = get_gemini_client()
    from google.genai import types

    # Zmieniamy model na dostępny w puli API Key
    model_name = "gemini-embedding-001"
    try:
        logger.debug(
            "Generating embedding using client id=%s, type=%s, model=%s",
            id(client),
            type(client),
            model_name,
        )
        logger.debug("Text length: %d", len(text.strip()))

        response = client.models.embed_content(
            model=model_name,
            contents=text.strip(),
            config=types.EmbedContentConfig(output_dimensionality=768),
        )

        if response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
    except APIError as e:
        logger.error(f"Gemini API Error during embedding generation: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error during embedding generation: {e}")

    return None


def _safe_str(v: object) -> str:
    if v is None:
        return ""
    return str(v).strip()


def build_use_case_text(brand: str, model: str, synthesis_data: dict) -> str:
    """What the vehicle IS — segment, type, character. Embedded as `vector_use_case`.
    Optimized for queries like 'duży SUV rodzinny', 'miejski hatchback', 'premium kombi'."""
    cs = synthesis_data.get("card_summary") or {}
    mapped = synthesis_data.get("mapped_ai_data") or {}
    parts: list[str] = []

    head = " ".join(filter(None, [_safe_str(brand), _safe_str(model), _safe_str(cs.get("trim_level"))]))
    if head:
        parts.append(f"Pojazd: {head}")

    body = _safe_str(mapped.get("body_style") or cs.get("body_style"))
    vclass = _safe_str(cs.get("vehicle_class") or mapped.get("vehicle_type"))
    if body or vclass:
        parts.append(f"Typ nadwozia: {body or '—'} ({vclass or '—'})")

    samar = _safe_str(mapped.get("samar_category"))
    if samar:
        parts.append(f"Klasa SAMAR: {samar}")

    drive = _safe_str(mapped.get("drive_type") or cs.get("drive_type"))
    if drive:
        parts.append(f"Napęd: {drive}")

    fuel = _safe_str(mapped.get("fuel") or cs.get("fuel"))
    fam = _safe_str(mapped.get("powertrain_family"))
    if fuel or fam:
        parts.append(f"Paliwo/silnik: {fuel or '—'} ({fam or '—'})")

    pwr_range = _safe_str(cs.get("power_range"))
    if pwr_range:
        parts.append(f"Zakres mocy: {pwr_range}")

    return "\n".join(parts)


def build_specs_text(brand: str, model: str, synthesis_data: dict) -> str:
    """Concrete technical parameters. Embedded as `vector_specs`.
    Optimized for queries like 'diesel z automatem', 'moc >200 KM', 'długość 4.7m'."""
    cs = synthesis_data.get("card_summary") or {}
    mapped = synthesis_data.get("mapped_ai_data") or {}
    dims = cs.get("dimensions") or {}
    parts: list[str] = []

    head = " ".join(filter(None, [_safe_str(brand), _safe_str(model)])) or "Pojazd"
    powertrain = _safe_str(cs.get("powertrain") or cs.get("powertrain_raw_legacy"))
    fuel = _safe_str(mapped.get("fuel") or cs.get("fuel"))
    pwr_hp = cs.get("power_hp")
    pwr_kw = cs.get("power_kw")
    pwr_str = ""
    if pwr_hp is not None:
        pwr_str = f"{pwr_hp} KM"
        if pwr_kw is not None:
            pwr_str += f" / {pwr_kw} kW"
    transmission = _safe_str(mapped.get("transmission") or cs.get("transmission"))
    drive = _safe_str(mapped.get("drive_type") or cs.get("drive_type"))

    engine_line = ", ".join(filter(None, [
        powertrain, fuel, pwr_str,
        f"skrzynia {transmission}" if transmission else "",
        f"napęd {drive}" if drive else "",
    ]))
    if engine_line:
        parts.append(f"{head}: {engine_line}")

    cap = _safe_str(cs.get("engine_capacity"))
    desig = _safe_str(cs.get("engine_designation"))
    if cap or desig:
        parts.append(f"Pojemność/oznaczenie silnika: {cap or '—'} {desig}".strip())

    dim_bits: list[str] = []
    if dims.get("length_mm") and dims.get("width_mm") and dims.get("height_mm"):
        dim_bits.append(f"{dims['length_mm']}×{dims['width_mm']}×{dims['height_mm']} mm")
    if dims.get("wheelbase_mm"):
        dim_bits.append(f"rozstaw osi {dims['wheelbase_mm']} mm")
    if dims.get("curb_weight_kg"):
        dim_bits.append(f"masa własna {dims['curb_weight_kg']} kg")
    if dims.get("payload_kg"):
        dim_bits.append(f"ładowność {dims['payload_kg']} kg")
    if dims.get("gross_vehicle_weight_kg"):
        dim_bits.append(f"DMC {dims['gross_vehicle_weight_kg']} kg")
    if dims.get("fuel_tank_capacity_l"):
        dim_bits.append(f"zbiornik {dims['fuel_tank_capacity_l']} l")
    if dims.get("cargo_volume_m3"):
        dim_bits.append(f"objętość ładunkowa {dims['cargo_volume_m3']} m³")
    if dim_bits:
        parts.append("Wymiary: " + ", ".join(dim_bits))

    emissions = _safe_str(cs.get("emissions"))
    if emissions:
        parts.append(f"Emisje/zużycie: {emissions}")

    wheels = _safe_str(cs.get("wheels"))
    if wheels:
        parts.append(f"Felgi: {wheels}\"")

    seats = cs.get("number_of_seats")
    if seats:
        parts.append(f"Liczba miejsc: {seats}")

    return "\n".join(parts)


def build_equipment_text(brand: str, model: str, synthesis_data: dict) -> str:
    """What's installed/included. Embedded as `vector_equipment`.
    Optimized for queries like 'z hakiem', 'kamera cofania', 'adaptive cruise'."""
    cs = synthesis_data.get("card_summary") or {}
    parts: list[str] = []
    head = " ".join(filter(None, [_safe_str(brand), _safe_str(model)])) or "Pojazd"
    parts.append(head)

    std = cs.get("standard_equipment") or []
    std_names = [_safe_str(x) for x in std if _safe_str(x)]
    if std_names:
        parts.append("Wyposażenie standardowe: " + "; ".join(std_names))

    paid = cs.get("paid_options") or []
    paid_names = [
        _safe_str(o.get("name"))
        for o in paid
        if isinstance(o, dict) and _safe_str(o.get("name"))
    ]
    if paid_names:
        parts.append("Opcje płatne: " + "; ".join(paid_names))

    if cs.get("has_tow_hook"):
        parts.append("Hak holowniczy: tak")
    if cs.get("has_automatic_ac"):
        parts.append("Klimatyzacja automatyczna: tak")

    color = _safe_str(cs.get("exterior_color"))
    if color:
        parts.append(f"Kolor: {color}")

    return "\n".join(parts)


def build_vehicle_document(brand: str, model: str, synthesis_data: dict) -> str:
    """Compile a rich text document for a vehicle to be vectorized.

    We combine all meaningful fields into a natural language/structured string
    so that semantic search can reliably find it.
    """
    parts = []

    # Base identity
    parts.append(f"Pojazd: {brand} {model}")

    cs = synthesis_data.get("card_summary", {})
    if cs:
        parts.append(f"Wersja: {cs.get('trim_level', '')}")
        parts.append(
            f"Typ nadwozia: {cs.get('body_style', '')} ({cs.get('vehicle_class', '')})"
        )
        parts.append(
            f"Silnik: {cs.get('fuel', '')} {cs.get('power_hp', '')} KM, napęd {cs.get('drive_type', '')}, skrzynia {cs.get('transmission', '')}"
        )

    # Equipment
    std = cs.get("standard_equipment", [])
    if std:
        parts.append(
            "Wyposażenie standardowe: " + ", ".join(std[:20])
        )  # take top 20 to avoid token bloat

    paid = cs.get("paid_options", [])
    if paid:
        opts = [o.get("name") for o in paid if isinstance(o, dict) and o.get("name")]
        if opts:
            parts.append("Wyposażenie dodatkowe: " + ", ".join(opts[:20]))

    mapped = synthesis_data.get("mapped_ai_data", {})
    if mapped:
        parts.append(f"Opis ogólny: {mapped.get('description', '')}")

    # Join into a single string
    return "\n".join(parts)
