import json
from typing import Any, Union

from google.genai import types

from core.extractor_models import ServiceOptionExtractionResult
from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE
from core.json_utils import clean_json_response
from core.prompts import SERVICE_OPTION_DIGITAL_TWIN_PROMPT


SECOND_PASS_BODYWORK_HINT = """
SECOND PASS (BODYWORK ONLY):
- Extract only options that modify body shape/homologation/load area.
- Ignore purely financial/accessory items like mats, insurance, warranty, inspections.
- If the document includes container/refrigerated/box/tarp/crane build-up, it must appear in output.
- If no explicit price is visible for a body build-up, still return it with net_price=0.
"""


BODYWORK_KEYWORDS = (
    "kontener",
    "zabudow",
    "izoterm",
    "chlodni",
    "chłodni",
    "skrzyn",
    "plandek",
    "autolawet",
    "lawet",
    "hds",
    "furgon",
)


def _contains_bodywork_keyword(text: str) -> bool:
    haystack = (text or "").lower()
    return any(keyword in haystack for keyword in BODYWORK_KEYWORDS)


def _parse_net_price(value: Any) -> float:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    if isinstance(value, str):
        cleaned = (
            value.replace(" ", "")
            .replace("PLN", "")
            .replace("zl", "")
            .replace(",", ".")
        )
        out = ""
        for ch in cleaned:
            if ch.isdigit() or ch in {".", "-"}:
                out += ch
        try:
            return round(float(out), 2) if out else 0.0
        except Exception:
            return 0.0
    return 0.0


def _is_bodywork_option(item: dict[str, Any]) -> bool:
    effects = item.get("effects")
    if isinstance(effects, dict):
        if effects.get("override_samar_class") or effects.get("override_homologation"):
            return True

    if _contains_bodywork_keyword(str(item.get("name") or "")):
        return True

    components = item.get("description_or_components")
    if isinstance(components, list):
        for comp in components:
            if _contains_bodywork_keyword(str(comp or "")):
                return True

    return False


def _normalize_service_option_payload(payload: Any) -> dict:
    """Normalize Gemini output to {"service_options": [ ... ]}."""
    if not isinstance(payload, dict):
        return {"service_options": []}

    raw_options: list[Any] = []

    options = payload.get("service_options")
    if isinstance(options, list):
        raw_options = options
    elif "name" in payload:
        raw_options = [payload]
    else:
        alt_options = payload.get("options")
        if isinstance(alt_options, list):
            raw_options = alt_options

    normalized: list[dict[str, Any]] = []
    for item in raw_options:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name") or "").strip()
        if not name:
            continue

        net_price = _parse_net_price(item.get("net_price"))
        if net_price <= 0:
            net_price = _parse_net_price(item.get("price_net"))

        normalized_item = dict(item)
        normalized_item["name"] = name
        normalized_item["net_price"] = net_price

        effects = normalized_item.get("effects")
        if effects is not None and not isinstance(effects, dict):
            effects = None
        if not isinstance(effects, dict):
            effects = {}

        # Keep structural options even if model omitted explicit effects.
        if _is_bodywork_option(normalized_item):
            effects.setdefault("is_financial_only", False)

        normalized_item["effects"] = effects if effects else None
        normalized.append(normalized_item)

    return {"service_options": normalized}


def _build_config(system_instruction: str) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=ServiceOptionExtractionResult,
        system_instruction=system_instruction,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )


def _extract_once(
    client: Any,
    model_id: str,
    contents: list[types.Part],
    system_instruction: str,
) -> dict:
    response = client.models.generate_content(
        model=model_id,
        contents=contents,
        config=_build_config(system_instruction),
    )
    response_text = getattr(response, "text", "{}") or "{}"
    raw = json.loads(clean_json_response(response_text))
    return _normalize_service_option_payload(raw)


def _has_bodywork_option(options: list[dict[str, Any]]) -> bool:
    for item in options:
        if not isinstance(item, dict):
            continue
        if _is_bodywork_option(item):
            return True
    return False


def _merge_options(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()

    for option in [*primary, *secondary]:
        if not isinstance(option, dict):
            continue

        name = str(option.get("name") or "").strip().lower()
        try:
            net_price = round(float(option.get("net_price") or 0.0), 2)
        except Exception:
            net_price = 0.0

        if not name:
            continue

        key = (name, net_price)
        if key in seen:
            continue

        seen.add(key)
        merged.append(option)

    return merged


def extract_service_option_from_pdf(
    document_data: Union[str, bytes], mime_type: str = "application/pdf"
) -> dict:
    """
    Extracts service options/build-ups from a document using Gemini.
    Returns shape: {"service_options": [ServiceOptionDigitalTwin, ...]}
    """
    client = get_gemini_client()
    model_id = "gemini-2.5-flash"

    if isinstance(document_data, bytes):
        contents: list[types.Part] = [
            types.Part.from_bytes(data=document_data, mime_type=mime_type),
        ]
    else:
        contents = [types.Part.from_text(text=document_data)]

    try:
        first_pass = _extract_once(
            client=client,
            model_id=model_id,
            contents=contents,
            system_instruction=SERVICE_OPTION_DIGITAL_TWIN_PROMPT,
        )

        first_options = first_pass.get("service_options") or []
        if not isinstance(first_options, list):
            first_options = []

        # Always run focused second pass and merge; this minimizes misses for build-ups
        # when the first pass over-indexes on accessories.
        second_pass = _extract_once(
            client=client,
            model_id=model_id,
            contents=contents,
            system_instruction=(
                SERVICE_OPTION_DIGITAL_TWIN_PROMPT + "\n\n" + SECOND_PASS_BODYWORK_HINT
            ),
        )
        second_options = second_pass.get("service_options") or []
        if not isinstance(second_options, list):
            second_options = []

        merged = _merge_options(first_options, second_options)

        if merged:
            return {"service_options": merged}

        # Fallback to first pass output shape if second pass failed unexpectedly.
        return {"service_options": first_options}

    except Exception as e:
        print(f"Error in extract_service_option_from_pdf: {e}")
        return {"service_options": []}
