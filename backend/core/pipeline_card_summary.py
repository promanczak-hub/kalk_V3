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
                if price_calc and (
                    "netto" not in extracted.lower()
                    and "brutto" not in extracted.lower()
                ):
                    calc_str = json.dumps(price_calc, ensure_ascii=False).lower()
                    if "netto" in calc_str:
                        extracted = f"{extracted} netto"
                    elif "brutto" in calc_str:
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
    # --- 6. Power HP & Power Range ---
    current_hp = card_summary.get("power_hp")
    if not current_hp:
        hp_val: int | None = None

        def _extract_and_sum_power(text: str) -> int | None:
            import re

            # Try KM sum: "163 + 14KM" or "163 KM + 14 KM"
            plus_match = re.search(
                r"(\d+)\s*(?:KM|HP|PS)?\s*\+\s*(\d+)\s*(?:KM|HP|PS)", text, re.IGNORECASE
            )
            if plus_match:
                return int(plus_match.group(1)) + int(plus_match.group(2))

            # Try kW sum: "120 kW + 10 kW" or "120 + 10kW"
            kw_plus_match = re.search(
                r"(\d+)\s*(?:kW)?\s*\+\s*(\d+)\s*kW", text, re.IGNORECASE
            )
            if kw_plus_match:
                return round(
                    (int(kw_plus_match.group(1)) + int(kw_plus_match.group(2))) * 1.36
                )

            km_match = re.search(r"(\d+)\s*(?:KM|HP|PS)", text, re.IGNORECASE)
            if km_match:
                return int(km_match.group(1))

            kw_match = re.search(r"(\d+)\s*kW", text, re.IGNORECASE)
            if kw_match:
                return round(int(kw_match.group(1)) * 1.36)

            return None

        # Try to extract from engine_performance max_power (e.g. "150 kW ...")
        max_power = _deep_get(
            digital_twin,
            "technical_data.engine_performance.max_power",
        )
        if max_power and isinstance(max_power, str):
            hp_val = _extract_and_sum_power(max_power)

        # Try model name as fallback (e.g. "150 kW(204 KM)")
        if not hp_val:
            model_name = _deep_get(
                digital_twin,
                "vehicle_summary.model_name",
                "model_name",
            )
            if model_name and isinstance(model_name, str):
                hp_val = _extract_and_sum_power(model_name)

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

    # --- 8. Power KW ---
    current_kw = card_summary.get("power_kw")
    if not current_kw:
        def _extract_and_sum_power_kw(text: str) -> int | None:
            import re

            kw_plus_match = re.search(
                r"(\d+)\s*(?:kW)?\s*\+\s*(\d+)\s*kW", text, re.IGNORECASE
            )
            if kw_plus_match:
                return int(kw_plus_match.group(1)) + int(kw_plus_match.group(2))

            kw_match = re.search(r"(\d+)\s*kW", text, re.IGNORECASE)
            if kw_match:
                return int(kw_match.group(1))

            return None

        kw_val: int | None = None
        # Try to extract from technical_data (if available in DT)
        raw_kw = _deep_get(digital_twin, "technical_data.power_kw")
        if raw_kw:
            kw_val = int(raw_kw) if str(raw_kw).isdigit() else _extract_and_sum_power_kw(str(raw_kw))

        if not kw_val:
            # Try to extract from engine_performance
            max_p_val = _deep_get(
                digital_twin, "technical_data.engine_performance.max_power"
            )
            if max_p_val and isinstance(max_p_val, str):
                kw_val = _extract_and_sum_power_kw(max_p_val)

        if kw_val:
            card_summary["power_kw"] = int(kw_val)
            print(f"[BACKFILL] power_kw: {kw_val} kW")

    # --- 9. Utility Features ---
    if not card_summary.get("utility_features"):
        # Try to extract from technical_data (if available in DT)
        uf = _deep_get(digital_twin, "technical_data.utility_features")
        if uf and isinstance(uf, list):
            card_summary["utility_features"] = uf
            print(f"[BACKFILL] utility_features: {len(uf)} items matched from DT")

    # --- 10. Deterministic paint type override ---
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
        print(f"[CARD SUMMARY ERROR] Błąd potoku Card Summary (Pro): {e}\n{tb}")
        # Safety net: even if Pro fails, try pages backfill
        digital_twin = pro_data.get("digital_twin", {})
        pages = digital_twin.get("pages")
        if isinstance(pages, list) and pages:
            print("[CARD SUMMARY FALLBACK] Pro failed — applying pages backfill")
            card_summary = pro_data.get("card_summary", {})
            pro_data["card_summary"] = _backfill_from_digital_twin(
                card_summary, digital_twin
            )
        return pro_data
