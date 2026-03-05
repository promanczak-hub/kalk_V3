import json
from typing import Any
from google import genai
from google.genai import types

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

from core.json_utils import clean_json_response
from core.extractor_models import (
    CardSummary,
    BrochureSummary,
    OtherDocumentSummary,
)
from core.prompts import (
    DOC_TYPE_PROMPT,
    CARD_SUMMARY_PROMPT,
    BROCHURE_SUMMARY_PROMPT,
    OTHER_DOC_SUMMARY_PROMPT,
)


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


def _backfill_from_digital_twin(card_summary: dict, digital_twin: dict) -> dict:
    """
    Deterministic fallback: fill missing card_summary fields
    directly from digital_twin structure.
    Handles both nested (equipment.standard_equipment) and flat layouts.
    """
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

    # Safety net: If AI says "Inny dokument" but we see brand/model, force Offer.
    if "Inny dokument" in doc_type_str and "brand" in pro_data and "model" in pro_data:
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
        elif doc_type_str == "Cennik ogólny modelu":
            chosen_schema = BrochureSummary
            instruction = BROCHURE_SUMMARY_PROMPT
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
        print(f"Błąd w podczas działanie potoku Card Summary (Flash): {e}")
        return pro_data
