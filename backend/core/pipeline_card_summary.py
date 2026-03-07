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

        for item in content_items:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type", "")
            title = (item.get("title") or "").strip().upper()

            # --- Pricing ---
            if item_type == "pricing_summary":
                currency = item.get("currency", "PLN")
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

            # --- Technical data table ---
            tech_table = item.get("technical_data_table", [])
            if isinstance(tech_table, list) and tech_table:
                for row in tech_table:
                    if not isinstance(row, dict):
                        continue
                    lbl = (row.get("label") or "").strip().lower()
                    val = (row.get("value") or "").strip()
                    if not val:
                        continue
                    if "paliw" in lbl or "rodzaj" in lbl:
                        result.setdefault("fuel", val)
                    elif "skrzyni" in lbl or "bieg" in lbl:
                        result.setdefault("transmission", val)
                    elif "pojemno" in lbl and "silnik" in lbl:
                        result.setdefault("engine_capacity", val)
                    elif "emisj" in lbl and "co2" in lbl:
                        result.setdefault("emissions", val)

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
            if "STANDARD" in title and "WYPOSAŻ" in title:
                for ei in item.get("items", []):
                    if isinstance(ei, dict):
                        desc = ei.get("description") or ei.get("name", "")
                        if desc:
                            std_equipment.append(desc.strip())

            # --- Optional equipment ---
            if "OPCJONALN" in title and "WYPOSAŻ" in title:
                currency = item.get("currency", "PLN")
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

            # --- Exterior color (NADWOZIE / LAKIER) ---
            if "NADWOZI" in title or "LAKIER" in title or "KOLOR" in title:
                for ci in item.get("items", []):
                    if isinstance(ci, dict):
                        name = (ci.get("name") or ci.get("description") or "").strip()
                        if name and not result.get("exterior_color"):
                            price = ci.get("price", "")
                            if price and price != "0,00":
                                result["exterior_color"] = f"{name} ({price} PLN)"
                            else:
                                result["exterior_color"] = name

            # --- Body style from WYBRANY MODEL (e.g. "BMW 320i Touring") ---
            if "MODEL" in title and "WYBRANY" in title:
                for mi in item.get("items", []):
                    if isinstance(mi, dict):
                        model_name = (mi.get("name") or "").strip()
                        if model_name:
                            body_keywords = {
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
                            }
                            lower_name = model_name.lower()
                            for keyword, style in body_keywords.items():
                                if keyword in lower_name:
                                    result.setdefault("body_style", style)
                                    break

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


def _backfill_from_digital_twin(card_summary: dict, digital_twin: dict) -> dict:
    """
    Deterministic fallback: fill missing card_summary fields
    directly from digital_twin structure.
    Handles pages-based (v2.0) and legacy structured layouts.
    """
    # --- 0. Pages-based extraction (v2.0 digital twin) ---
    pages = digital_twin.get("pages")
    if isinstance(pages, list) and pages:
        extracted = _extract_from_pages(pages)
        for key, value in extracted.items():
            current = card_summary.get(key)
            if (
                not current
                or (
                    isinstance(current, str)
                    and current.strip().lower() in ("", "brak", "none", "null")
                )
                or (isinstance(current, list) and len(current) == 0)
            ):
                card_summary[key] = value

    # --- 1. standard_equipment ---
    existing_std = card_summary.get("standard_equipment")
    if not existing_std or (isinstance(existing_std, list) and len(existing_std) == 0):
        raw_std = _deep_get(
            digital_twin,
            "equipment.standard_equipment",
            "standard_equipment",
        )
        if isinstance(raw_std, list) and len(raw_std) > 0:
            names: list[str] = []
            for item in raw_std:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    if name:
                        names.append(name)
                elif isinstance(item, str) and item.strip():
                    names.append(item.strip())
            if names:
                card_summary["standard_equipment"] = names
                print(
                    f"[BACKFILL] standard_equipment: "
                    f"uzupełniono {len(names)} pozycji z digital_twin"
                )

    # --- 2. paid_options ---
    existing_po = card_summary.get("paid_options")
    if not existing_po or (isinstance(existing_po, list) and len(existing_po) == 0):
        raw_opts = _deep_get(
            digital_twin,
            "equipment.additional_equipment",
            "equipment.optional_equipment",
            "optional_equipment",
            "additional_equipment",
        )
        if isinstance(raw_opts, list) and len(raw_opts) > 0:
            options: list[dict[str, str]] = []
            for item in raw_opts:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    price = item.get("price", item.get("price_gross", "0 PLN"))
                    category = item.get("category", "Fabryczna")
                    if name:
                        options.append(
                            {"name": name, "price": str(price), "category": category}
                        )
                elif isinstance(item, str) and item.strip():
                    options.append(
                        {
                            "name": item.strip(),
                            "price": "0 PLN",
                            "category": "Fabryczna",
                        }
                    )
            if options:
                card_summary["paid_options"] = options
                print(
                    f"[BACKFILL] paid_options: "
                    f"uzupełniono {len(options)} pozycji z digital_twin"
                )

    # --- 3. Pricing ---
    price_fields = {
        "base_price": [
            "financial_summary.price_calculation.CENA MODELU",
            "financial_summary.price_calculation.Cena modelu",
            "pricing.base_price",
            "base_price",
        ],
        "options_price": [
            "financial_summary.price_calculation.Cena wyposażenia dodatkowego",
            "financial_summary.price_calculation.Cena wyposaenia dodatkowego",
            "financial_summary.price_calculation.Cena wyposa\u017cenia dodatkowego",
            "pricing.options_price",
            "options_price",
        ],
        "total_price": [
            "financial_summary.price_calculation.Cena finalna z VAT",
            "financial_summary.price_calculation.Cena samochodu z VAT",
            "financial_summary.price_calculation.Cena końcowa",
            "pricing.total_price",
            "total_price",
        ],
    }
    for field, paths in price_fields.items():
        current = _extract_price_str(card_summary.get(field))
        if not current or current.lower() == "brak":
            raw_val = _deep_get(digital_twin, *paths)
            extracted = _extract_price_str(raw_val)
            if extracted:
                # Normalize: ensure PLN suffix
                if "PLN" not in extracted.upper():
                    extracted = f"{extracted} PLN"
                # Try to determine netto/brutto from context
                price_calc = _deep_get(
                    digital_twin, "financial_summary.price_calculation"
                )
                if price_calc:
                    calc_str = json.dumps(price_calc, ensure_ascii=False).lower()
                    if "netto" in calc_str:
                        if (
                            "netto" not in extracted.lower()
                            and "brutto" not in extracted.lower()
                        ):
                            extracted = f"{extracted} brutto"
                    elif (
                        "brutto" not in extracted.lower()
                        and "netto" not in extracted.lower()
                    ):
                        extracted = f"{extracted} brutto"
                card_summary[field] = extracted
                print(f"[BACKFILL] {field}: '{extracted}' z digital_twin")

    # --- 4. Powertrain ---
    current_pt = str(card_summary.get("powertrain", "")).strip()
    if not current_pt or current_pt.lower() in ("brak", "none", "null"):
        # Try engine_performance first
        ep = _deep_get(
            digital_twin,
            "technical_data.engine_performance",
            "technical.power",
        )
        if isinstance(ep, dict):
            power = ep.get("max_power", "")
            capacity = ep.get("engine_capacity", "")
            parts = []
            if capacity:
                parts.append(str(capacity).replace(",", "."))
            if power:
                parts.append(str(power))
            if parts:
                card_summary["powertrain"] = " / ".join(parts)
                print(
                    f"[BACKFILL] powertrain: '{card_summary['powertrain']}' z digital_twin"
                )
        elif isinstance(ep, str) and ep:
            card_summary["powertrain"] = ep
            print(f"[BACKFILL] powertrain: '{ep}' z digital_twin")

        # Still empty? Try model_name
        if not str(card_summary.get("powertrain", "")).strip():
            model_name = _deep_get(
                digital_twin,
                "vehicle_summary.model_name",
                "model_name",
            )
            if model_name and isinstance(model_name, str):
                card_summary["powertrain"] = model_name
                print(f"[BACKFILL] powertrain (from model): '{model_name}'")

    # --- 5. Fuel ---
    current_fuel = str(card_summary.get("fuel", "")).strip()
    if not current_fuel or current_fuel.lower() in ("brak", "none", "null"):
        raw_fuel = _deep_get(
            digital_twin,
            "technical_data.engine_performance.fuel_type",
            "technical.fuel_type",
        )
        if raw_fuel and isinstance(raw_fuel, str):
            card_summary["fuel"] = raw_fuel
            print(f"[BACKFILL] fuel: '{raw_fuel}' z digital_twin")

    # --- 6. Power HP & Power Range ---
    current_hp = card_summary.get("power_hp")
    if not current_hp:
        hp_val: int | None = None

        # Try to extract from engine_performance max_power (e.g. "150 kW ...")
        max_power = _deep_get(
            digital_twin,
            "technical_data.engine_performance.max_power",
        )
        if max_power and isinstance(max_power, str):
            import re

            kw_match = re.search(r"(\d+)\s*kW", max_power, re.IGNORECASE)
            km_match = re.search(r"(\d+)\s*(?:KM|HP|PS)", max_power, re.IGNORECASE)
            if km_match:
                hp_val = int(km_match.group(1))
            elif kw_match:
                hp_val = round(int(kw_match.group(1)) * 1.36)

        # Try model name as fallback (e.g. "150 kW(204 KM)")
        if not hp_val:
            model_name = _deep_get(
                digital_twin,
                "vehicle_summary.model_name",
                "model_name",
            )
            if model_name and isinstance(model_name, str):
                import re

                km_match = re.search(r"(\d+)\s*(?:KM|HP|PS)", model_name, re.IGNORECASE)
                kw_match = re.search(r"(\d+)\s*kW", model_name, re.IGNORECASE)
                if km_match:
                    hp_val = int(km_match.group(1))
                elif kw_match:
                    hp_val = round(int(kw_match.group(1)) * 1.36)

        if hp_val and hp_val > 0:
            card_summary["power_hp"] = hp_val
            print(f"[BACKFILL] power_hp: {hp_val} KM")

            # Compute power_range
            if hp_val <= 130:
                card_summary["power_range"] = "LOW (do 130 KM)"
            elif hp_val <= 200:
                card_summary["power_range"] = "MID (131 - 200 KM)"
            else:
                card_summary["power_range"] = "HIGH (201 KM i więcej)"
            print(f"[BACKFILL] power_range: '{card_summary['power_range']}'")

    # --- 7. Deterministic paint type override ---
    # AI sometimes misclassifies metallic paint as non-metallic.
    # Override is_metalic_paint based on keywords in exterior_color.
    exterior_color = str(card_summary.get("exterior_color", "")).strip().lower()
    if exterior_color and exterior_color not in ("brak", "none", "null"):
        metallic_keywords = (
            "metalik",
            "metalic",
            "metallic",
            "metalizow",
            "perłow",
            "pearl",
            "xirallic",
            "mica",
            "special efekt",
            "dwuwarstwow",
        )
        is_keyword_metallic = any(kw in exterior_color for kw in metallic_keywords)

        nonmetallic_keywords = ("solido", "uni ", "akrylow", "jednowarstwow")
        is_keyword_nonmetallic = any(
            kw in exterior_color for kw in nonmetallic_keywords
        )

        current_flag = card_summary.get("is_metalic_paint")

        if is_keyword_metallic and current_flag is not True:
            card_summary["is_metalic_paint"] = True
            print(
                f"[BACKFILL] is_metalic_paint: OVERRIDE → True "
                f"(keyword w exterior_color: '{exterior_color}')"
            )
        elif is_keyword_nonmetallic and current_flag is not False:
            card_summary["is_metalic_paint"] = False
            print(
                f"[BACKFILL] is_metalic_paint: OVERRIDE → False "
                f"(keyword w exterior_color: '{exterior_color}')"
            )

    return card_summary


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
    Given a raw JSON digital twin, generates a structured summary using Gemini Flash.
    Returns the pro_data augmented with "card_summary" and doc type metadata.
    """
    client = get_gemini_client()

    flash_model_id = "gemini-2.5-flash"
    pro_response_text = json.dumps(pro_data, ensure_ascii=False)

    try:
        # Step 1: Classify document
        doc_type_str = classify_document_type(pro_data, client, flash_model_id)

        # Step 2: Extract specific summaries based on type
        chosen_schema: Any
        if doc_type_str == "Oferta na samochód":
            chosen_schema = CardSummary
            instruction = CARD_SUMMARY_PROMPT
        else:
            chosen_schema = OtherDocumentSummary
            instruction = OTHER_DOC_SUMMARY_PROMPT

        flash_config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=chosen_schema,
            system_instruction=instruction,
            safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        )

        flash_contents: list[types.Part] = [
            types.Part.from_text(text=pro_response_text)
        ]

        flash_response = client.models.generate_content(
            model=flash_model_id,
            contents=flash_contents,
            config=flash_config,
        )

        flash_json_str = getattr(flash_response, "text", "{}") or "{}"
        flash_data = json.loads(clean_json_response(str(flash_json_str)))

        # --- AI FALLBACK FOR MISSING DATA ---
        if doc_type_str == "Oferta na samochód":
            base_price = flash_data.get("base_price", "Brak")
            options_price = flash_data.get("options_price", "Brak")
            powertrain = flash_data.get("powertrain", "Brak")

            if base_price == "Brak" or options_price == "Brak" or powertrain == "Brak":
                print(
                    "Brak podstawowych danych. Uruchamiam model PRO dla uzupełnienia."
                )
                pro_model_id = "gemini-2.5-pro"
                try:
                    pro_response = client.models.generate_content(
                        model=pro_model_id,
                        contents=[types.Part.from_text(text=pro_response_text)],
                        config=flash_config,
                    )
                    pro_json_str = getattr(pro_response, "text", "{}") or "{}"
                    pro_extracted_data = json.loads(
                        clean_json_response(str(pro_json_str))
                    )

                    # Merge ONLY if Flash failed, to preserve the rest
                    for key in [
                        "base_price",
                        "options_price",
                        "powertrain",
                        "total_price",
                        "fuel",
                    ]:
                        val = str(flash_data.get(key, "Brak")).strip()
                        if val in ["Brak", "", "None", "null"]:
                            pro_val = pro_extracted_data.get(key, "Brak")
                            if pro_val:
                                flash_data[key] = pro_val

                    print("PRO FALLBACK uzupełnił dane.")
                except Exception as pro_e:
                    print(
                        f"Błąd podczas wyciągania brakujących danych modelem PRO: {pro_e}"
                    )
        # ----------------------------------------

        # Merge the CardSummary into the main output
        pro_data["card_summary"] = flash_data

        # Deterministic backfill: fill gaps from digital_twin
        digital_twin = pro_data.get("digital_twin", {})
        if digital_twin:
            pro_data["card_summary"] = _backfill_from_digital_twin(
                pro_data["card_summary"], digital_twin
            )

        # Ensure digital_twin metadata exists
        if "digital_twin" not in pro_data:
            pro_data["digital_twin"] = {}
        if "metadata" not in pro_data["digital_twin"]:
            pro_data["digital_twin"]["metadata"] = {}

        pro_data["digital_twin"]["metadata"]["document_type"] = doc_type_str

        return pro_data

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[CARD SUMMARY ERROR] Błąd potoku Card Summary (Flash): {e}\n{tb}")
        # Safety net: even if Flash fails, try pages backfill
        digital_twin = pro_data.get("digital_twin", {})
        pages = digital_twin.get("pages")
        if isinstance(pages, list) and pages:
            print("[CARD SUMMARY FALLBACK] Flash failed — applying pages backfill")
            card_summary = pro_data.get("card_summary", {})
            pro_data["card_summary"] = _backfill_from_digital_twin(
                card_summary, digital_twin
            )
        return pro_data
