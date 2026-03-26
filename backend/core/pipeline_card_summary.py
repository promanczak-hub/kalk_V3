import json
import logging
import re
import traceback
from typing import Any
from google import genai
from google.genai import types

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

from core.json_utils import clean_json_response
from core.extractor_models import (
    CardSummary,
    OtherDocumentSummary,
)
from core.prompts import (
    DOC_TYPE_PROMPT,
    CARD_SUMMARY_PROMPT,
    OTHER_DOC_SUMMARY_PROMPT,
)

logger = logging.getLogger(__name__)


def _extract_price_str(raw: Any) -> str:
    """Normalize a raw price value into a display string like '295 700 PLN brutto'."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s or s.lower() in ("brak", "none", "null", "0"):
        return ""
    return s


def _deep_get(d: dict, *paths: str) -> Any:
    """Try multiple dot-separated paths, return first non-None hit."""
    for path in paths:
        val: Any = d
        for key in path.split("."):
            if isinstance(val, dict):
                val = val.get(key)
            else:
                val = None
                break
        if val is not None:
            return val
    return None


_BODY_KEYWORDS: dict[str, str] = {
    "touring": "Touring (Kombi)",
    "sedan": "Sedan",
    "limousine": "Sedan",
    "gran coupe": "Gran Coupé",
    "coupe": "Coupé",
    "cabrio": "Kabriolet",
    "suv": "SUV",
    "hatchback": "Hatchback",
    "kombi": "Kombi",
    "van": "Van",
    "furgon": "Furgon",
    "chassis": "Chassis (Podwozie)",
    "podwozi": "Chassis (Podwozie)",
    "pickup": "Pickup",
    "dostawcz": "Dostawczy",
    "platforma": "Platforma",
    "skrzyniow": "Skrzyniowy",
    "minibus": "Minibus",
    "bus": "Bus",
}


def _detect_body_style(model_name: str, result: dict) -> None:
    """Detect body_style from model name using keyword matching."""
    lower_name = model_name.lower()
    for keyword, style in _BODY_KEYWORDS.items():
        if keyword in lower_name:
            result.setdefault("body_style", style)
            return


def _extract_from_pages(pages: list) -> dict:
    """
    Deterministic extraction from pages-based digital_twin.

    Scans content items across all pages for pricing, technical data,
    equipment, wheels, emissions, and color. Returns a dict of
    extracted fields that can be merged into card_summary.
    """
    result: dict[str, Any] = {}
    std_equipment: list[str] = []
    paid_options: list[dict[str, str]] = []

    for page in pages:
        content_items = page.get("content", [])
        if not isinstance(content_items, list):
            continue

        # Flatten nested content[]: VW nests items inside
        # section.content[] (e.g. pricing_summary inside a section).
        flat_items: list[dict] = []
        queue = list(content_items)
        while queue:
            item = queue.pop(0)
            if not isinstance(item, dict):
                continue
            flat_items.append(item)
            nested = item.get("content", [])
            if isinstance(nested, list):
                queue.extend(nested)

        for item in flat_items:
            item_type = item.get("type", "")
            title = (item.get("title") or "").strip().upper()

            # --- Pricing ---
            if item_type == "pricing_summary":
                currency = item.get("currency", "PLN")
                # Format A: price_components (BMW/Audi)
                for comp in item.get("price_components", []):
                    label = (comp.get("item") or "").lower()
                    price = comp.get("price", "")
                    if not price:
                        continue
                    price_str = f"{price} {currency} brutto"
                    if "bazow" in label or "modelu" in label:
                        result.setdefault("base_price", price_str)
                    elif "opcjonaln" in label or "wyposażeni" in label:
                        result.setdefault("options_price", price_str)
                    elif "całkowit" in label or "zapłat" in label:
                        result.setdefault("total_price", price_str)
                # Format B: items[].details[] (VW commercial)
                for summary_item in item.get("items", []):
                    category = (summary_item.get("category") or "").lower()
                    total_str = summary_item.get("total", "")
                    if total_str and ("katalog" in category or "łączn" in category):
                        result.setdefault(
                            "total_price",
                            f"{total_str}",
                        )
                    for detail in summary_item.get("details", []):
                        d_item = (detail.get("item") or "").lower()
                        d_price = detail.get("price", "")
                        if not d_price:
                            continue
                        if "bazow" in d_item or "samochód" in d_item:
                            result.setdefault("base_price", d_price)
                        elif (
                            "opcjonaln" in d_item
                            or "wyposażeni" in d_item
                            or "dodatkow" in d_item
                        ):
                            result.setdefault("options_price", d_price)
                    # VW: "Cena samochodu bazowego ..." in category
                    if "obniżk" in category or "samochod" in category:
                        price_val = summary_item.get("price", "")
                        if price_val:
                            result.setdefault("total_price", price_val)

            # --- Technical data table ---
            # Format A: technical_data_table (BMW/Audi)
            tech_table = item.get("technical_data_table", [])
            # Format B: subsections[].data[] (VW commercial)
            # VW puts semantic info in subsection titles (e.g.
            # "WLTP Emisja CO2") while data labels are generic
            # ("Cykl mieszany"). Combine title + label for matching.
            subsections = item.get("subsections", [])
            if isinstance(subsections, list) and subsections:
                for sub in subsections:
                    sub_title = (sub.get("title") or "").strip().lower()
                    for row in sub.get("data", []):
                        if isinstance(row, dict):
                            enriched = dict(row)
                            orig_lbl = enriched.get("label", "")
                            enriched["label"] = f"{sub_title} {orig_lbl}"
                            tech_table.append(enriched)
            # Also check section-level data[] (e.g. Wymiary, Siedzenia)
            section_data = item.get("data", [])
            if isinstance(section_data, list) and section_data:
                sec_title = (item.get("title") or "").strip().lower()
                for r in section_data:
                    if isinstance(r, dict):
                        enriched = dict(r)
                        orig_lbl = enriched.get("label", "")
                        enriched["label"] = f"{sec_title} {orig_lbl}"
                        tech_table.append(enriched)
            if isinstance(tech_table, list) and tech_table:
                for row in tech_table:
                    if not isinstance(row, dict):
                        continue
                    lbl = (row.get("label") or "").strip().lower()
                    val = (row.get("value") or "").strip()
                    if not val:
                        continue
                    # Order matters: specific checks before generic ones.
                    if "zużyci" in lbl and "paliw" in lbl:
                        result.setdefault("fuel_consumption", val)
                    elif "emisj" in lbl and "co2" in lbl:
                        result.setdefault("emissions", val)
                    elif "liczba" in lbl and "siedz" in lbl:
                        result.setdefault("number_of_seats", val)
                    elif (
                        ("paliw" in lbl or "rodzaj" in lbl)
                        and "zużyci" not in lbl
                        and "emisj" not in lbl
                    ):
                        result.setdefault("fuel", val)
                    elif "skrzyni" in lbl or "bieg" in lbl:
                        result.setdefault("transmission", val)
                    elif "pojemno" in lbl and "silnik" in lbl:
                        result.setdefault("engine_capacity", val)
                    elif "cylindr" in lbl:
                        result.setdefault("cylinders", val)
                    elif any(
                        k in lbl
                        for k in [
                            "długoś",
                            "szeroko",
                            "wysoko",
                            "rozstaw",
                            "ładowno",
                            "masa",
                            "pojemno",
                            "wymiar",
                        ]
                    ):
                        uf_list = result.setdefault("utility_features", [])
                        uf_list.append({"name": row.get("label", ""), "value": val})

            # --- Emissions from vehicle config ---
            vehicle = item.get("vehicle", {})
            if isinstance(vehicle, dict):
                em = vehicle.get("emissions", {})
                if isinstance(em, dict) and em.get("value"):
                    result.setdefault("emissions", em["value"])

            # --- Wheels (OBRĘCZE) ---
            if "OBRĘ" in title or "FELG" in title or "WHEEL" in title:
                for wi in item.get("items", []):
                    if isinstance(wi, dict):
                        name = wi.get("name", "")
                        size_match = re.search(r'(\d{2})["″\'\s]', name)
                        if size_match:
                            result.setdefault("wheels", size_match.group(1))

            # --- Standard equipment ---
            is_std_equip = ("STANDARD" in title and "WYPOSAŻ" in title) or (
                "WYBRAN" in title and "STANDARD" in title
            )
            if is_std_equip:
                for ei in item.get("items", []):
                    if isinstance(ei, dict):
                        desc = ei.get("description") or ei.get("name", "")
                        if desc:
                            std_equipment.append(desc.strip())
                    elif isinstance(ei, str) and ei.strip():
                        std_equipment.append(ei.strip())
                # VW format: subsections with items (dict or str)
                for sub in item.get("subsections", []):
                    if isinstance(sub, dict):
                        for ei in sub.get("items", []):
                            if isinstance(ei, dict):
                                desc = ei.get("description") or ei.get("name", "")
                                if desc:
                                    std_equipment.append(desc.strip())
                            elif isinstance(ei, str) and ei.strip():
                                std_equipment.append(ei.strip())

            # --- Optional equipment ---
            is_opt_equip = (
                ("OPCJONALN" in title and "WYPOSAŻ" in title)
                or ("DODATKOW" in title and "WYPOSAŻ" in title)
                or ("WYPOSAŻENIE DODATKOWE" in title)
            )
            if is_opt_equip:
                currency = item.get("currency", "PLN")
                # Direct items
                for oi in item.get("items", []):
                    if isinstance(oi, dict):
                        name = oi.get("name", "")
                        price = oi.get("price", "0")
                        if name:
                            paid_options.append(
                                {
                                    "name": name.strip(),
                                    "price": f"{price} {currency}",
                                    "category": "Fabryczna",
                                }
                            )
                # VW format: options_table inside content[]
                for ci in item.get("content", []):
                    if isinstance(ci, dict) and ci.get("type") == "options_table":
                        for oi in ci.get("items", []):
                            if isinstance(oi, dict):
                                name = oi.get("name", "")
                                price = oi.get("price", "0")
                                if name:
                                    paid_options.append(
                                        {
                                            "name": name.strip(),
                                            "price": f"{price} {currency}",
                                            "category": "Fabryczna",
                                        }
                                    )

            # --- Exterior color (NADWOZIE / LAKIER / OPCJE WYKOŃCZENIA) ---
            is_color_section = (
                "NADWOZI" in title
                or "LAKIER" in title
                or "KOLOR" in title
                or "WYKOŃCZENI" in title
            )
            if is_color_section:
                for ci in item.get("items", []):
                    if isinstance(ci, dict):
                        name = (ci.get("name") or ci.get("description") or "").strip()
                        if name and not result.get("exterior_color"):
                            price = ci.get("price", "")
                            if price and price != "0,00":
                                result["exterior_color"] = f"{name} ({price} PLN)"
                            else:
                                result["exterior_color"] = name
                # VW format: finishes_table inside content[]
                for ci in item.get("content", []):
                    if isinstance(ci, dict) and ci.get("type") == "finishes_table":
                        for row in ci.get("rows", []):
                            if isinstance(row, list):
                                for cell in row:
                                    if isinstance(cell, dict):
                                        name = (cell.get("name") or "").strip()
                                        if name and not result.get("exterior_color"):
                                            price = cell.get("price", "")
                                            if price and price != "0,00":
                                                result["exterior_color"] = (
                                                    f"{name} ({price} PLN)"
                                                )
                                            else:
                                                result["exterior_color"] = name

            # --- Body style from WYBRANY MODEL (e.g. "BMW 320i Touring") ---
            if "MODEL" in title and "WYBRANY" in title:
                for mi in item.get("items", []):
                    if isinstance(mi, dict):
                        model_name = (mi.get("name") or "").strip()
                        if model_name:
                            _detect_body_style(model_name, result)

    # --- Construct powertrain from tech data ---
    capacity = result.get("engine_capacity", "")
    fuel = result.get("fuel", "")
    transmission = result.get("transmission", "")
    if capacity or fuel:
        parts = [p for p in [capacity, fuel, transmission] if p]
        result.setdefault("powertrain", " / ".join(parts))

    if std_equipment:
        result["standard_equipment"] = std_equipment
    if paid_options:
        result["paid_options"] = paid_options

    if result:
        print(
            f"[BACKFILL-PAGES] Wyciągnięto {len(result)} pól "
            f"z formatu pages: {list(result.keys())}"
        )
    return result


def classify_document_type(pro_data: dict, client: genai.Client, model_id: str) -> str:
    """
    Classifies the document type based on the extracted digital twin.
    """
    pro_response_text = json.dumps(pro_data, ensure_ascii=False)

    doc_type_config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=8192,
        response_mime_type="text/plain",
        system_instruction=DOC_TYPE_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    doc_type_response = client.models.generate_content(
        model=model_id,
        contents=[types.Part.from_text(text=pro_response_text)],
        config=doc_type_config,
    )

    doc_type_str = getattr(doc_type_response, "text", "Oferta na samochód")
    if doc_type_str is None:
        doc_type_str = "Oferta na samochód"
    else:
        doc_type_str = doc_type_str.strip()

    # Safety net: If AI says "Inny dokument" but we see real brand/model values,
    # force it back to Offer. Check VALUE, not just key existence.
    has_brand = bool((pro_data.get("brand") or "").strip())
    has_model = bool((pro_data.get("model") or "").strip())
    if "Inny dokument" in doc_type_str and has_brand and has_model:
        logger.info(
            "[DOC TYPE] AI said '%s' but brand='%s', model='%s' present. "
            "Forcing 'Oferta na samochód'.",
            doc_type_str,
            pro_data.get("brand"),
            pro_data.get("model"),
        )
        doc_type_str = "Oferta na samochód"

    return doc_type_str


def generate_card_summary_from_twin(pro_data: dict) -> dict:
    """
    Given a raw JSON digital twin, generates a structured summary using Gemini Pro.
    Returns the pro_data augmented with "card_summary" and doc type metadata.
    """
    client = get_gemini_client()

    pro_model_id = "gemini-2.5-pro"
    pro_response_text = json.dumps(pro_data, ensure_ascii=False)

    try:
        # Step 1: Classify document
        doc_type_str = classify_document_type(pro_data, client, pro_model_id)

        # Step 2: Extract specific summaries based on type
        chosen_schema: Any
        if doc_type_str == "Oferta na samochód":
            chosen_schema = CardSummary
            instruction = CARD_SUMMARY_PROMPT

            # Wstrzyknięcie historii poprawek (Few-Shot Prompting)
            brand = pro_data.get("brand")
            model = pro_data.get("model")

            if brand:
                try:
                    from core.database import supabase

                    query = (
                        supabase.table("extraction_corrections")
                        .select("*")
                        .eq("brand", brand)
                    )
                    if model:
                        query = query.eq("model", model)

                    corrections_res = (
                        query.order("created_at", desc=True).limit(5).execute()
                    )

                    if corrections_res.data:
                        injection = "\n\n=== HISTORICAL USER CORRECTIONS ===\n"
                        injection += "To help prevent repeated mistakes, here are previous corrections made by human verifiers for this brand/model:\n"
                        for c in corrections_res.data:
                            field = c.get("field_name", "Unknown")
                            old_v = str(c.get("old_value") or "None")
                            new_v = str(c.get("new_value") or "None")
                            notes = c.get("context_notes")

                            notes_str = f" Context/Notes: {notes}" if notes else ""
                            injection += f"- Field '{field}': AI previously extracted '{old_v}', but human corrected it to '{new_v}'.{notes_str}\n"

                        injection += "\nPlease keep these past mistakes in mind and DO NOT repeat them for similar documents. If you see the same ambiguous pattern in the text, assume the human's 'new_value' logic.\n"
                        instruction += injection
                except Exception as e:
                    logger.warning(
                        f"Could not load historical corrections for prompt injection: {e}"
                    )

        else:
            chosen_schema = OtherDocumentSummary
            instruction = OTHER_DOC_SUMMARY_PROMPT

        summary_config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=chosen_schema,
            system_instruction=instruction,
            safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        )

        summary_contents: list[types.Part] = [
            types.Part.from_text(text=pro_response_text)
        ]

        summary_response = client.models.generate_content(
            model=pro_model_id,
            contents=summary_contents,
            config=summary_config,
        )

        summary_json_str = getattr(summary_response, "text", "{}") or "{}"
        summary_data = json.loads(clean_json_response(str(summary_json_str)))

        # Merge the CardSummary into the main output
        pro_data["card_summary"] = summary_data

        # Ensure digital_twin metadata exists
        if "digital_twin" not in pro_data:
            pro_data["digital_twin"] = {}
        if "metadata" not in pro_data["digital_twin"]:
            pro_data["digital_twin"]["metadata"] = {}

        pro_data["digital_twin"]["metadata"]["document_type"] = doc_type_str

        return pro_data

    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f"[CARD SUMMARY ERROR] Błąd generatywnego tworzenia CardSummary (Structured Output) - wygenerowano pustą kartę, operacja zatrzymana. Log: {str(e)}\nTraceback:\n{tb}"
        logger.error(error_msg)
        
        # In a strict Enterprise setup, we do not fallback to half-baked dictionaries when schema matching fails.
        # We ensure a dict is present so the pipeline does not completely crash if downstream systems are resilient,
        # but we strictly abandon deterministic backfills.
        if "card_summary" not in pro_data:
             pro_data["card_summary"] = {}

        return pro_data
