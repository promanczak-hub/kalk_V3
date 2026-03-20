import logging
from html import escape
from typing import List, Dict, Any, cast, Tuple
from core.database import supabase
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony
from core.LTRSubCalculatorFinanse import FinanseCalculator, FinanseInput
from core.LTRSubCalculatorUbezpieczenie import InsuranceCalculator
from core.LTRSubCalculatorSamochodZastepczy import ReplacementCarCalculator
from core.LTRSubCalculatorKosztyDodatkowe import AdditionalCostsCalculator
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput
from core.LTRSubCalculatorCenaZakupu import (
    PurchasePriceCalculator,
    PurchasePriceInput,
    PurchasePriceOption,
)
from core.LTRSubCalculatorAmortyzacja import (
    AmortyzacjaCalculator,
    AmortyzacjaInput,
)
from core.LTRSubCalculatorBudzetMarketingowy import (
    BudzetMarketingowyCalculator,
    BudzetMarketingowyInput,
)
from core.LTRSubCalculatorKosztDzienny import (
    KosztDziennyCalculator,
    KosztDziennyInput,
)
from core.LTRSubCalculatorStawka import (
    StawkaCalculator,
    StawkaInput,
)
from functools import lru_cache


_ENGINE_CATEGORY_TO_ID: Dict[str, int] = {
    "BENZYNA": 1,
    "PB": 1,
    "DIESEL": 2,
    "ON": 2,
    "BENZYNA MHEV": 3,
    "PB-MHEV": 3,
    "DIESEL MHEV": 4,
    "ON-MHEV": 4,
    "HYBRYDA": 5,
    "HEV": 5,
    "PHEV": 6,
    "HYBRYDA PLUG-IN": 6,
    "ELEKTRYCZNY": 7,
    "BEV": 7,
    "FCEV": 8,
    "WODĂ“R": 8,
    "LPG": 9,
}


def _resolve_engine_type_id(engine_category: str) -> int:
    """Map engine_category string to engines.id used by DB tables."""
    if not engine_category:
        raise ValueError("Brak parametru engine_category.")

    upper = engine_category.strip().upper()

    # Most specific aliases first.
    if "PHEV" in upper or "PLUG-IN" in upper:
        return 6
    if "MHEV" in upper and ("DIESEL" in upper or "ON" in upper):
        return 4
    if "MHEV" in upper and ("BENZYNA" in upper or "PB" in upper):
        return 3
    if "FCEV" in upper or "WODOR" in upper or "WODĂ“R" in upper:
        return 8
    if "HEV" in upper or "HYBRYDA" in upper:
        return 5
    if "ELEKTR" in upper or "BEV" in upper or upper == "EV":
        return 7
    if "LPG" in upper:
        return 9
    if "DIESEL" in upper or "ON" in upper:
        return 2
    if "BENZYNA" in upper or "PB" in upper:
        return 1

    for key, eid in _ENGINE_CATEGORY_TO_ID.items():
        if key in upper:
            return eid

    raise ValueError(
        f"Nieznana kategoria silnika: '{engine_category}'. Brak mapowania na engine_type_id."
    )


@lru_cache(maxsize=256)
def _resolve_samar_class_id_from_name(samar_category: str) -> int:
    if not samar_category:
        return 0

    from core.database import supabase

    cls_res = supabase.table("samar_classes").select("id, name").execute()

    def _norm_samar(s: str) -> str:
        return s.strip().upper().replace("KLASA ", "").replace("SAMAR: ", "").strip()

    cat_norm = _norm_samar(samar_category)
    for cls_row in cls_res.data or []:
        db_name = str(cls_row.get("name", ""))
        if _norm_samar(db_name) == cat_norm:
            return int(cls_row["id"])
    return 0


@lru_cache(maxsize=256)
def _resolve_body_type_id_from_name(body_type_name: str) -> int | None:
    if not body_type_name:
        return None
    try:
        from core.body_type_matcher import match_body_type

        match = match_body_type(body_type_name)
        return int(match.matched_body_type_id) if match.matched_body_type_id else None
    except Exception:
        return None


_PL_CHARS_TRANSLATION = str.maketrans(
    {
        "\u0104": "A",
        "\u0106": "C",
        "\u0118": "E",
        "\u0141": "L",
        "\u0143": "N",
        "\u00d3": "O",
        "\u015a": "S",
        "\u0179": "Z",
        "\u017b": "Z",
    }
)

_ZABUDOWA_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "KONTENER": ("KONTENER", "BOX", "BOX BODY"),
    "IZOTERMA": ("IZOTERMA", "ISOTHERM"),
    "CHLODNIA": ("CHLODNIA", "CHLODNI", "CHILLER", "REEFER"),
    "SKRZYNIA": ("SKRZYNIA", "SKRZYNI", "DROPSIDE"),
    "PLANDEKA": ("PLANDEKA", "TARPAULIN"),
    "AUTOLAWETA": ("AUTOLAWETA", "LAWETA", "CAR CARRIER"),
    "PODWOZIE": ("PODWOZIE", "CHASSIS", "PLATFORM"),
}


def _norm_lookup_key(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .upper()
        .translate(_PL_CHARS_TRANSLATION)
        .replace("-", " ")
        .replace("_", " ")
    )


@lru_cache(maxsize=1)
def _load_zabudowa_types_map() -> Dict[str, int]:
    try:
        from core.database import supabase

        resp = supabase.table("body_types").select("id, name").execute()
        rows = resp.data or []
        out: Dict[str, int] = {}
        for row in rows:
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            out[_norm_lookup_key(name)] = int(row["id"])
        return out
    except Exception as exc:
        logging.warning("Nie udalo sie zaladowac body_types jako zabudowa: %s", exc)
        return {}


def _resolve_zabudowa_type_id_from_name(zabudowa_name: str) -> int | None:
    if not zabudowa_name:
        return None

    mapping = _load_zabudowa_types_map()
    if not mapping:
        return None

    normalized = _norm_lookup_key(zabudowa_name)
    if not normalized:
        return None

    if normalized in mapping:
        return mapping[normalized]

    for map_name, map_id in mapping.items():
        if map_name in normalized or normalized in map_name:
            return map_id

    detected_key: str | None = None
    for canonical_key, keywords in _ZABUDOWA_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            detected_key = canonical_key
            break

    if detected_key:
        for map_name, map_id in mapping.items():
            if detected_key in map_name:
                return map_id

    return None


def _extract_service_option_names(sd: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    cs = sd.get("card_summary") or {}

    paid_options = cs.get("paid_options") or []
    if isinstance(paid_options, list):
        for row in paid_options:
            if not isinstance(row, dict):
                continue
            category = str(row.get("category") or "").lower()
            if "fabryczna" in category:
                continue
            name = str(row.get("name") or "").strip()
            if name:
                names.append(name)

    service_options = sd.get("service_options") or []
    if isinstance(service_options, list):
        for row in service_options:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if name:
                names.append(name)
            components = row.get("description_or_components") or []
            if isinstance(components, list):
                for comp in components:
                    comp_name = str(comp or "").strip()
                    if comp_name:
                        names.append(comp_name)

    service_equipment = cs.get("service_equipment") or {}
    if isinstance(service_equipment, dict):
        main_name = str(service_equipment.get("name") or "").strip()
        if main_name:
            names.append(main_name)
        components = service_equipment.get("components") or []
        if isinstance(components, list):
            for comp in components:
                if not isinstance(comp, dict):
                    continue
                comp_name = str(comp.get("name") or "").strip()
                if comp_name:
                    names.append(comp_name)

    return names


def _infer_zabudowa_type_id(sd: Dict[str, Any], body_type_name: str = "") -> int | None:
    candidates: List[str] = []
    if body_type_name:
        candidates.append(body_type_name)

    cs = sd.get("card_summary") or {}
    mai = sd.get("mapped_ai_data") or {}

    for source in (
        sd.get("zabudowa_type_name"),
        cs.get("zabudowa_type_name"),
        mai.get("zabudowa_type_name"),
        cs.get("body_style"),
        mai.get("body_type"),
    ):
        text = str(source or "").strip()
        if text:
            candidates.append(text)

    candidates.extend(_extract_service_option_names(sd))

    for candidate in candidates:
        resolved = _resolve_zabudowa_type_id_from_name(candidate)
        if resolved:
            return resolved
    return None


def _build_report_html(cell: Dict[str, Any]) -> str:
    def _fmt(val: Any) -> str:
        if isinstance(val, (int, float)):
            return f"{val:,.2f}".replace(",", " ").replace(".", ",")
        return str(val or "-")

    rows = [
        ("Okres (mc)", _fmt(cell.get("Okres"))),
        ("Przebieg (km/rok)", _fmt(cell.get("Przebieg"))),
        ("Stawka laczna", _fmt(cell.get("LacznaStawka"))),
        ("Czynsz finansowy", _fmt(cell.get("CzynszFinansowy"))),
        ("Czynsz techniczny", _fmt(cell.get("CzynszTechniczny"))),
        ("WR", _fmt(cell.get("WR"))),
        ("Utrata wartosci", _fmt(cell.get("UtrataWartosci"))),
        ("Cena zakupu", _fmt(cell.get("CenaZakupu"))),
        ("Koszty dodatkowe", _fmt(cell.get("KosztyDodatkowe"))),
        ("Ubezpieczenie", _fmt(cell.get("LacznieUbezpieczenie"))),
        ("Serwis", _fmt(cell.get("KosztySerwisowe"))),
        ("Opony", _fmt(cell.get("LacznyKosztOpon"))),
        ("Samochod zastepczy", _fmt(cell.get("LacznieSamochodZastepczy"))),
        ("Marza miesiac", _fmt(cell.get("MarzaMiesiac"))),
        ("Marza na kontrakcie", _fmt(cell.get("MarzaNaKontrakcie"))),
        ("Koszt dzienny", _fmt(cell.get("KosztDzienny"))),
    ]

    row_html = "".join(
        f"<tr><td>{escape(label)}</td><td class='val'>{escape(value)}</td></tr>"
        for label, value in rows
    )

    return (
        "<!doctype html><html><head><meta charset='utf-8'/>"
        "<style>"
        "body{font-family:Segoe UI,Arial,sans-serif;background:#fff;color:#0f172a;margin:16px;}"
        "h3{margin:0 0 10px 0;font-size:16px;}"
        "table{border-collapse:collapse;width:100%;font-size:12px;}"
        "td{border:1px solid #cbd5e1;padding:6px 8px;vertical-align:top;}"
        "td.val{text-align:right;font-weight:600;white-space:nowrap;}"
        "</style></head><body>"
        f"<h3>Karta kalkulacji (V3)</h3><table>{row_html}</table>"
        "</body></html>"
    )


@lru_cache(maxsize=256)
def _resolve_paint_type_id_from_name(paint_type_name: str) -> int | None:
    if not paint_type_name:
        return None
    try:
        from core.database import supabase

        norm = paint_type_name.strip().upper()
        res = supabase.table("paint_types").select("id, name").execute()
        for row in res.data or []:
            row_name = str(row.get("name", "")).strip().upper()
            if row_name == norm:
                return int(row["id"])
        for row in res.data or []:
            row_name = str(row.get("name", "")).strip().upper()
            if row_name and (row_name in norm or norm in row_name):
                return int(row["id"])
    except Exception:
        return None
    return None


@lru_cache(maxsize=128)
def get_vehicle_from_db(vid: str) -> Dict[str, Any]:
    """Pobiera dane pojazdu z vehicle_synthesis i mapuje na format wejĹ›ciowy kalkulatora."""
    if not vid:
        return {}
    try:
        from core.database import supabase

        res = (
            supabase.table("vehicle_synthesis")
            .select("id, brand, model, synthesis_data, zabudowa_apr_wr")
            .eq("id", vid)
            .execute()
        )
        if not res.data or not isinstance(res.data, list) or len(res.data) == 0:
            return cast(Dict[str, Any], {})

        row = res.data[0]
        sd = row.get("synthesis_data") or {}
        cs = sd.get("card_summary") or {}
        mai = sd.get("mapped_ai_data") or {}

        samar_category = str(
            cs.get("samar_category") or mai.get("samar_category") or ""
        )
        samar_class_id = _resolve_samar_class_id_from_name(samar_category)

        engine_category = str(
            cs.get("engine_category", "") or mai.get("fuel", "") or ""
        )
        engine_type_id = _resolve_engine_type_id(engine_category)

        body_type_name = str(mai.get("body_type") or cs.get("body_style") or "")
        body_type_id = cs.get("body_type_id") or _resolve_body_type_id_from_name(
            body_type_name
        )
        zabudowa_type_id = (
            sd.get("zabudowa_type_id")
            or cs.get("zabudowa_type_id")
            or mai.get("zabudowa_type_id")
        )
        if zabudowa_type_id in (None, ""):
            zabudowa_type_id = _infer_zabudowa_type_id(sd, body_type_name)
        if zabudowa_type_id not in (None, ""):
            try:
                zabudowa_type_id = int(zabudowa_type_id)
            except Exception:
                zabudowa_type_id = None

        power_kw_raw = cs.get("power_kw") or 0
        if not power_kw_raw:
            powertrain = cs.get("powertrain", "") or ""
            import re

            kw_match = re.search(r"(\d+)\s*kW", powertrain, re.IGNORECASE)
            if kw_match:
                power_kw_raw = int(kw_match.group(1))
            else:
                km_match = re.search(r"(\d+)\s*KM", powertrain, re.IGNORECASE)
                if km_match:
                    power_km = int(km_match.group(1))
                    power_kw_raw = round(power_km / 1.36)

        if not power_kw_raw or float(power_kw_raw) <= 0:
            raise ValueError(
                f"Nie udaĹ‚o siÄ™ ustaliÄ‡ mocy pojazdu (brak kW i KM) dla ID: {vid}. "
                "UzupeĹ‚nij dane w panelu."
            )

        vehicle_dict: Dict[str, Any] = {
            "id": vid,
            "brand": row.get("brand", ""),
            "model": row.get("model", ""),
            "Segment": samar_category,
            "samar_class_id": int(samar_class_id),
            "engine_type_id": engine_type_id,
            "power_kw": float(power_kw_raw),
            "paint_type_id": cs.get("paint_type_id"),
            "body_type_id": body_type_id,
            "body_type_name": body_type_name,
            "drive_type": mai.get("drive_type") or cs.get("drive_type") or "",
            "zabudowa_apr_wr": bool(
                row.get("zabudowa_apr_wr", False) or zabudowa_type_id
            ),
            "zabudowa_type_id": zabudowa_type_id,
            "is_metalic": cs.get("is_metalic_paint", True),
            "rocznik": cs.get("rocznik", "current"),
        }
        return vehicle_dict

    except Exception as exc:
        logging.warning("get_vehicle_from_db error for %s: %s", vid, exc)
    return cast(Dict[str, Any], {})


@lru_cache(maxsize=128)
def get_samar_klasa_from_db(klasa_id: str) -> Dict[str, Any]:
    """Pobiera parametry serwisowe (i nie tylko) przypisane do klasy pojazdu"""
    if not klasa_id:
        return {}
    try:
        from core.database import supabase

        res = supabase.table("samar_klasa_wr").select("*").eq("id", klasa_id).execute()
        if res.data and len(res.data) > 0:
            return cast(Dict[str, Any], res.data[0])
    except Exception:
        pass
    return {}


@lru_cache(maxsize=128)
def get_insurance_rates_from_db(samar_class_id: str) -> List[Dict[str, Any]]:
    """Pobiera tabelÄ™ ubezpieczeĹ„ dla danej klasy SAMAR (28 klas, 7 lat)."""
    try:
        from core.database import supabase

        if samar_class_id:
            res = (
                supabase.table("ltr_admin_ubezpieczenia")
                .select("*")
                .eq("samar_class_id", samar_class_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(List[Dict[str, Any]], res.data)

    except Exception as e:
        logging.warning("Error fetching insurance rates: %s", e)
    return []


@lru_cache(maxsize=128)
def get_replacement_car_rate_from_db(samar_class_id: str) -> Dict[str, Any]:
    """Pobiera parametry auta zastÄ™pczego z tabeli replacement_car_rates.

    samar_class_id to PK z samar_classes.
    """
    try:
        from core.database import supabase

        if samar_class_id:
            res = (
                supabase.table("replacement_car_rates")
                .select("*")
                .eq("samar_class_id", samar_class_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])

        # Fallback: brak danych dla tej klasy â€” zwrĂłÄ‡ pusty dict (koszt = 0)
    except Exception as e:
        logging.warning("Error fetching replacement car rate: %s", e)
    return {}


@lru_cache(maxsize=128)
def get_damage_coefficients_from_db(samar_class_id: str) -> Dict[str, Any]:
    """Pobiera wspĂłĹ‚czynniki szkodowe dla klasy pojazdu (bez fallbacku na null)"""
    try:
        from core.database import supabase

        if samar_class_id:
            res = (
                supabase.table("ltr_admin_wspolczynniki_szkodowe")
                .select("*")
                .eq("samar_class_id", samar_class_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                return cast(Dict[str, Any], res.data[0])

    except Exception as e:
        logging.warning("Error fetching damage coefficients: %s", e)
    return {}


class LTRKalkulator:
    """RdzeĹ„ budujÄ…cy Matrix dla zadanego CalculatorInput"""

    def __init__(self, input_data: Any, settings: Any):
        self.input_data = input_data
        self.settings = settings

        # Inicjalizacja subkalkulatorĂłw
        self.tires_calc = LTRSubCalculatorOpony(
            z_oponami=getattr(self.input_data, "z_oponami", True),
            klasa_opony_string=getattr(self.input_data, "klasa_opony_string", ""),
            srednica_felgi=getattr(self.input_data, "srednica_felgi", 0) or 0,
            korekta_kosztu=getattr(self.input_data, "korekta_kosztu_opon", False),
            koszt_opon_korekta=getattr(self.input_data, "koszt_opon_korekta", 0.0),
            sets_needed_override=getattr(
                self.input_data, "liczba_kompletow_opon", None
            ),
            odkup_opon_enabled=getattr(self.input_data, "odkup_opon_enabled", False),
        )

        # Load vehicle if needed
        vid = getattr(self.input_data, "vehicle_id", "")
        if isinstance(self.input_data, dict):
            vid = self.input_data.get("vehicle_id", "")
        self.vehicle = get_vehicle_from_db(vid) if vid else {}

        self.samar_id = self.vehicle.get("samar_class_id", 0)
        self.vehicle["samar_class_id"] = self.samar_id

        samar_id_str = str(self.samar_id)
        self.samar_klasa = (
            get_samar_klasa_from_db(samar_id_str)
            if samar_id_str and samar_id_str != "0"
            else {}
        )

        # Override synthesized vehicle data with explicit dropdown input values.
        self._apply_explicit_input_overrides()

        # Service calculator (ASO/nonASO)
        self.include_servicing = bool(
            getattr(self.input_data, "include_servicing", True)
        )
        self.service_cost_type = str(
            getattr(self.input_data, "service_cost_type", "ASO") or "ASO"
        ).strip()
        normalized_service_type = (
            self.service_cost_type.upper().replace("-", "").replace("_", "")
        )
        if normalized_service_type in {"NONASO", "NIEASO"}:
            self._opcja_serwisowa = "NON-ASO"
        elif normalized_service_type == "ASO":
            self._opcja_serwisowa = "ASO"
        else:
            raise ValueError(
                f"Nieobslugiwany service_cost_type: '{self.service_cost_type}'. "
                "Dozwolone: ASO / NON-ASO."
            )

    def _apply_explicit_input_overrides(self) -> None:
        if not self.vehicle:
            self.vehicle = {}

        input_samar = str(getattr(self.input_data, "samar_category", "") or "").strip()
        if input_samar:
            resolved_samar_id = _resolve_samar_class_id_from_name(input_samar)
            if resolved_samar_id <= 0:
                raise ValueError(
                    f"Nie rozpoznano klasy SAMAR z dropdownu: '{input_samar}'."
                )
            self.vehicle["Segment"] = input_samar
            self.vehicle["samar_class_id"] = int(resolved_samar_id)
            self.samar_id = int(resolved_samar_id)

        # Nadpisanie mocy z UI payload
        if getattr(self.input_data, "power_kw", None):
            self.vehicle["power_kw"] = float(self.input_data.power_kw)
        elif getattr(self.input_data, "power_hp", None):
            self.vehicle["power_kw"] = float(round(self.input_data.power_hp / 1.36))
            self.samar_klasa = get_samar_klasa_from_db(str(self.samar_id))

        input_engine = str(getattr(self.input_data, "engine_name", "") or "").strip()
        if input_engine:
            resolved_engine_id = _resolve_engine_type_id(input_engine)
            self.vehicle["engine_type_id"] = int(resolved_engine_id)

        input_body = str(getattr(self.input_data, "body_type_name", "") or "").strip()
        if input_body:
            resolved_body_id = _resolve_body_type_id_from_name(input_body)
            if resolved_body_id:
                self.vehicle["body_type_id"] = int(resolved_body_id)
            else:
                logging.warning(
                    "Nie rozpoznano typu nadwozia z dropdownu: '%s'; zapis manualny bez body_type_id.",
                    input_body,
                )
            self.vehicle["body_type_name"] = input_body
            if not self.vehicle.get("zabudowa_type_id"):
                inferred_zabudowa = _resolve_zabudowa_type_id_from_name(input_body)
                if inferred_zabudowa:
                    self.vehicle["zabudowa_type_id"] = int(inferred_zabudowa)

        input_paint = str(getattr(self.input_data, "paint_type_name", "") or "").strip()
        if input_paint:
            resolved_paint_id = _resolve_paint_type_id_from_name(input_paint)
            if not resolved_paint_id:
                raise ValueError(
                    f"Nie rozpoznano typu lakieru z dropdownu: '{input_paint}'."
                )
            self.vehicle["paint_type_id"] = int(resolved_paint_id)

        input_drive = str(getattr(self.input_data, "drive_type", "") or "").strip()
        if input_drive:
            self.vehicle["drive_type"] = input_drive

        input_zab_type = getattr(self.input_data, "zabudowa_type_id", None)
        if input_zab_type not in (None, ""):
            self.vehicle["zabudowa_type_id"] = int(input_zab_type)
        elif not self.vehicle.get("zabudowa_type_id"):
            for opt in getattr(self.input_data, "service_options", []) or []:
                opt_name = str(getattr(opt, "name", "") or "")
                inferred_zabudowa = _resolve_zabudowa_type_id_from_name(opt_name)
                if inferred_zabudowa:
                    self.vehicle["zabudowa_type_id"] = int(inferred_zabudowa)
                    break

        self.vehicle["zabudowa_apr_wr"] = bool(
            self.vehicle.get("zabudowa_apr_wr", False)
            or self.vehicle.get("zabudowa_type_id")
        )

        if hasattr(self.input_data, "vehicle_vintage"):
            self.vehicle["rocznik"] = getattr(self.input_data, "vehicle_vintage")
        if hasattr(self.input_data, "is_metalic"):
            self.vehicle["is_metalic"] = bool(getattr(self.input_data, "is_metalic"))

    def _calculate_capex(self) -> Tuple[float, float, Any]:
        """Kalkuluje wejĹ›ciowÄ… sumÄ™ finansowanÄ… (CAPEX) autorskim kalkulatorem (V3)"""
        base_net = self.input_data.base_price_net

        options = []
        for opt in self.input_data.factory_options:
            options.append(
                PurchasePriceOption(
                    price_net=opt.price_net,
                    name=opt.name,
                    is_service=False,
                    is_discountable=not opt.no_discount,
                )
            )

        for opt in self.input_data.service_options:
            options.append(
                PurchasePriceOption(
                    price_net=opt.price_net,
                    name=opt.name,
                    is_service=True,
                    is_discountable=not opt.no_discount,
                )
            )

        # Zmiana względem pierwotnego V1: użytkownik chce by wartość CAPEX wprost
        # odpowiadała wybranej klasie opon (np. Premium), eliminując niespójność "Ceny zakupu".
        tires_capex = (
            self.tires_calc.tire_set_price if self.tires_calc.z_oponami else 0.0
        )
        brand = self.vehicle.get("brand", "").strip()
        transport_fee_net = float(getattr(self.input_data, "transport_fee_net", 0.0))
        if brand and transport_fee_net == 0.0:
            try:
                res = (
                    supabase.table("transport_fees")
                    .select("fee_net")
                    .eq("brand", brand)
                    .limit(1)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    transport_fee_net = float(res.data[0].get("fee_net", 0.0))
            except Exception as e:
                logging.getLogger(__name__).error(
                    f"Error fetching transport fee for {brand}: {e}"
                )

        pp_input = PurchasePriceInput(
            base_price_net=base_net,
            options=options,
            discount_pct=self.input_data.discount_pct,
            tires_capex_net=tires_capex,
            add_gsm_to_capex=True,  # Changed to True based on user feedback (V1 Parity)
            gsm_device_cost_net=float(getattr(self.settings, "cost_gsm_device", 469.0)),
            gsm_installation_cost_net=float(
                getattr(self.settings, "cost_gsm_installation", 150.0)
            ),
            pakiet_serwisowy_net=float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            ),
            transport_fee_net=transport_fee_net,
        )

        calc = PurchasePriceCalculator(pp_input)
        res = calc.calculate()

        # total_options_capex is undiscounted sum â€” we need the discounted value.
        # total_capex includes: discounted_base + disc_opts*factor + non_disc
        #   + svc_opts + pakiet + transport + tires + gsm
        # We want only: disc_opts*factor + non_disc + svc_opts + pakiet
        discounted_options_capex = (
            res.total_capex
            - res.discounted_base
            - res.tires_capex_net
            - res.gsm_capex_net
            - res.transport_fee_net
        )
        return res.discounted_base, discounted_options_capex, res

    def build_matrix(self, only_exact: bool = False) -> List[Dict[str, Any]]:
        """Przelicza wszystkie warianty i zwraca siatkÄ™ (List of Cells)"""
        # V3 Matrix Generation: Linear 1D Grid (6 - 84 months) based on reference usage (Card Summary)
        cells = []

        vehicle_capex, options_capex, capex_res = self._calculate_capex()
        capex = vehicle_capex + options_capex
        # V1 parity: WR curve uses full catalogue prices (no discount)
        base_price_net_full = float(getattr(self.input_data, "base_price_net", 0))

        # Instantiate RV calculator once (shared across all months)
        from core.LTRSubCalculatorUtrataWartosciNew import (
            LTRSubCalculatorUtrataWartosciNew,
        )

        rv_calc = LTRSubCalculatorUtrataWartosciNew(self.vehicle, self.input_data)

        # Opcje pod WartoĹ›Ä‡ RezydualnÄ… (Zawsze Fabryczne + Serwisowe z include_in_wr)
        base_wr_options = sum(opt.price_net for opt in self.input_data.factory_options)
        base_wr_options += sum(
            opt.price_net
            for opt in self.input_data.service_options
            if getattr(opt, "include_in_wr", False)
        )

        # Raw margin percentage (e.g. 2.0%)
        margin_pct = self.input_data.pricing_margin_pct / 100.0
        if margin_pct >= 1.0:
            margin_pct = 0.9999  # Prevention of division by zero

        matrix_km_mode = str(
            getattr(self.input_data, "matrix_km_mode", "annual") or "annual"
        ).lower()
        if matrix_km_mode not in {"annual", "contract"}:
            matrix_km_mode = "annual"

        # Requested base variant (used to derive default contract-km axis).
        req_months = int(getattr(self.input_data, "okres_bazowy", 48) or 48)
        req_total_km = int(
            getattr(self.input_data, "przebieg_bazowy", 140000) or 140000
        )
        if req_months <= 0:
            req_months = 48

        contract_km_step = int(
            getattr(self.input_data, "matrix_contract_km_step", 10000) or 10000
        )
        if contract_km_step <= 0:
            contract_km_step = 10000

        grid_params: List[tuple[int, int]] = []
        seen_pairs = set()
        contract_km_by_pair: Dict[tuple[int, int], int] = {}

        def add_grid_pair(
            months_val: int,
            km_per_year_val: int,
            contract_km_val: int | None = None,
        ) -> None:
            pair = (int(months_val), int(km_per_year_val))
            if pair in seen_pairs:
                return
            seen_pairs.add(pair)
            grid_params.append(pair)
            if contract_km_val is not None:
                contract_km_by_pair[pair] = int(contract_km_val)

        if only_exact:
            pass  # Skip building the full grid if we only want the exact requested tile
        elif matrix_km_mode == "contract":
            contract_km_min = 10000
            contract_km_max = 300000
            contract_km_step = 5000

            for m in (24, 36, 48, 60):
                for total_km_contract in range(
                    contract_km_min,
                    contract_km_max + 1,
                    contract_km_step,
                ):
                    km_py = int(round((total_km_contract / m) * 12))
                    add_grid_pair(m, km_py, total_km_contract)
        else:
            for m in (24, 36, 48, 60):
                for km_py in range(10000, 80001, 2500):
                    add_grid_pair(m, km_py)

        # Inject requested base period/mileage into the grid.
        if req_months > 0:
            req_km_per_year = int(round((req_total_km / req_months) * 12))
            add_grid_pair(req_months, req_km_per_year, req_total_km)

        for months, km_per_year in grid_params:
            total_km = contract_km_by_pair.get(
                (months, km_per_year), int((km_per_year / 12) * months)
            )

            # 1. Koszty Opon
            tires_res = self.tires_calc.calculate_cost(months=months, total_km=total_km)
            capex_for_financing = (
                capex + tires_res["capex_initial_set"]
            )  # WartoĹ›Ä‡ opony do rat

            # 2. Koszty Techniczne/Operacyjne â€” legacy ops_calc usuniÄ™ty (Fix 2)

            # W V1 Utrata Wartości i WR liczone są na Cenie pojazdu (po rabacie) + opcje fabryczne
            # Należy użyć opcji fabrycznych po rabacie (które w V3 to factory options discounted)
            discount_pct = getattr(self.input_data, "discount_pct", 0) / 100.0
            discounted_factory_options = base_wr_options * (1 - discount_pct)
            wp_amortyzacja = vehicle_capex + discounted_factory_options

            # VAT Rate to apply gross math
            vat_rate = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate > 10.0:
                vat_rate = 1.0 + (vat_rate / 100.0)

            # V1 parity: WR curve uses full catalogue brutto (no discount)
            # Uzywamy tylko opcji wp_amortyzacja do WR
            rv_res = rv_calc.calculate_values(
                months=months,
                total_km=total_km,
                base_vehicle_capex_gross=base_price_net_full * vat_rate,
                options_capex_gross=base_wr_options * vat_rate,
            )

            vr_samar = rv_res["WR"]

            # Obliczenie PMT (V1 parity â€” dwa warianty z/bez czynszu)
            vat_rate_fin = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate_fin > 10.0:
                vat_rate_fin = 1.0 + (vat_rate_fin / 100.0)
            finance_input = FinanseInput(
                WartoscPoczatkowaNetto=capex_for_financing,
                WrPrzewidywanaCenaSprzedazy=vr_samar,
                CzynszInicjalny=float(
                    getattr(self.input_data, "CzynszKwota", 0.0) or 0.0
                ),
                CzynszProcent=float(
                    getattr(self.input_data, "CzynszProcent", 0.0) or 0.0
                ),
                RodzajCzynszu=str(getattr(self.input_data, "RodzajCzynszu", "Kwotowo")),
                StawkaVAT=vat_rate_fin,
                Okres=months,
                WIBORProcent=float(getattr(self.input_data, "wibor_pct", 0.0) or 0.0),
                MarzaFinansowaProcent=float(
                    getattr(self.input_data, "margin_pct", 0.0) or 0.0
                ),
            )
            finance_calc = FinanseCalculator(finance_input)
            finance_res = finance_calc.calculate()

            # Wynik Opon z dict
            tires_base = float(
                tires_res["monthly_hardware"]
                + tires_res["monthly_storage"]
                + tires_res["monthly_swaps"]
            )
            # Wynik Serwisu ? nowy ServiceCalculator (ASO/nonASO z DB + floor normatywnego przebiegu)
            normatywny_przebieg = int(
                getattr(self.settings, "normatywny_przebieg_mc", 0) or 0
            )
            if normatywny_przebieg <= 0:
                raise ValueError(
                    "Brak poprawnej wartosci `normatywny_przebieg_mc` w Control Center."
                )

            if not self.samar_id:
                raise ValueError(
                    "Brak `samar_class_id` dla pojazdu. Uzupelnij klase SAMAR w danych wejsciowych."
                )

            engine_type_id = int(self.vehicle.get("engine_type_id", 0) or 0)
            if engine_type_id <= 0:
                engine_name_input = getattr(self.input_data, "engine_name", None)
                if engine_name_input:
                    try:
                        engine_type_id = _resolve_engine_type_id(engine_name_input)
                    except Exception:
                        pass

            if engine_type_id <= 0:
                raise ValueError(
                    "Brak `engine_type_id` dla pojazdu. Uzupelnij typ silnika w danych wejsciowych."
                )

            power_kw_input = getattr(self.input_data, "power_kw", None)
            if power_kw_input and float(power_kw_input) > 0:
                power_kw = float(power_kw_input)
            else:
                power_kw = float(self.vehicle.get("power_kw", 0.0) or 0.0)

            if power_kw <= 0.0:
                raise ValueError(
                    f"Brak poprawnej mocy `power_kw` pojazdu. power_kw_input={power_kw_input}, self.vehicle_power_kw={self.vehicle.get('power_kw')}"
                )

            pakiet_serwisowy_val = float(
                getattr(self.input_data, "pakiet_serwisowy", 0.0)
            )
            inne_koszty_val = float(
                getattr(
                    self.input_data,
                    "inne_koszty_serwisowania_netto",
                    0.0,
                )
            )
            service_input = ServiceCalculatorInput(
                z_serwisem=self.include_servicing,
                opcja_serwisowa=self._opcja_serwisowa,
                normatywny_przebieg_mc=normatywny_przebieg,
                samar_class_id=int(self.samar_id),
                engine_type_id=engine_type_id,
                power_kw=power_kw,
                przebieg=total_km,
                okres=months,
                pakiet_serwisowy=pakiet_serwisowy_val,
                inne_koszty_serwisowania_netto=inne_koszty_val,
            )
            service_calc = ServiceCalculator(service_input)
            service_from_new_dict = service_calc.calculate()
            service_from_new = float(service_from_new_dict["monthly_service"])
            # Use new ServiceCalculator result; fail-fast for missing table parameters.
            service_base = service_from_new
            service_fallback_used = False
            if self.include_servicing and service_from_new <= 0:
                service_fallback_used = True
                raise ValueError(
                    f"Brak stawek serwisowych (ServiceCalculator zwrocil 0) dla "
                    f"okres={months}, klasa={self.vehicle.get('samar_class_id', '?')}, "
                    f"silnik={self.vehicle.get('engine_type_id', '?')}. "
                    f"Uzupelnij brakujace dane w tabeli `samar_service_costs`."
                )

            # --- SUB-KALKULATOR: AMORTYZACJA (V1 port) ---
            if getattr(self.input_data, "depreciation_pct", None) is not None:
                procent_amortyzacji_miesiecznie = float(
                    self.input_data.depreciation_pct
                )
            else:
                amort_input = AmortyzacjaInput(
                    wp_finansowanie=capex_for_financing,
                    wp_amortyzacja=wp_amortyzacja,
                    wr=vr_samar,
                    okres=months,
                )
                amort_result = AmortyzacjaCalculator(amort_input).calculate()
                procent_amortyzacji_miesiecznie = amort_result.amortyzacja_procent

            # --- SUB-KALKULATOR: UBEZPIECZENIE ---
            s_class_id = str(self.samar_id)
            insurance_rates = get_insurance_rates_from_db(s_class_id)
            damage_coeffs = get_damage_coefficients_from_db(s_class_id)
            ins_calc = InsuranceCalculator(
                insurance_rates=insurance_rates,  # type: ignore
                damage_coefficients=damage_coeffs,  # type: ignore
                settings=self.settings,  # type: ignore
                amortization_pct=procent_amortyzacji_miesiecznie,  # type: ignore
                total_km=total_km,  # type: ignore
            )

            insurance_res = ins_calc.calculate_cost(months, capex_for_financing)  # type: ignore
            insurance_base = float(insurance_res["monthly_insurance"])
            insurance_total = float(
                insurance_res.get("total_insurance", insurance_base * months)
            )

            # --- SUB-KALKULATOR: SAMOCHOD ZASTEPCZY ---
            rc_rate = get_replacement_car_rate_from_db(s_class_id)
            rc_calc = ReplacementCarCalculator(rc_rate)  # type: ignore
            rc_res = rc_calc.calculate_cost(
                months=months, enabled=self.input_data.replacement_car_enabled
            )
            rc_base = float(rc_res["monthly_replacement_car"])
            rc_total = float(rc_res.get("total_replacement_car", rc_base * months))

            # --- SUB-KALKULATOR: KOSZTY DODATKOWE ---
            add_calc = AdditionalCostsCalculator(self.settings, self.input_data, months)
            add_calc_res = add_calc.calculate_cost()
            additional_costs_base = float(add_calc_res["monthly_additional_costs"])
            additional_costs_total = additional_costs_base * months

            # Totale do sub-kalkulatorĂłw V1
            tires_total = tires_base * months
            service_total = service_base * months
            utrata_z_czynszem = float(
                rv_res.get(
                    "UtrataWartosciZCzynszemInicjalnym", capex_for_financing - vr_samar
                )
            )
            utrata_bez_czynszu = float(rv_res["UtrataWartosciBEZczynszu"])

            # --- SUB-KALKULATOR: KOSZT DZIENNY (V1 port) ---
            kd_input = KosztDziennyInput(
                utrata_wartosci_z_czynszem=utrata_z_czynszem,
                utrata_wartosci_bez_czynszu=utrata_bez_czynszu,
                koszt_finansowy=finance_res.SumaOdsetekZczynszem,
                samochod_zastepczy_netto=rc_total,
                koszty_dodatkowe_netto=additional_costs_total,
                ubezpieczenie_netto=insurance_total,
                opony_netto=tires_total,
                serwis_netto=service_total,
                suma_odsetek_bez_czynszu=finance_res.SumaOdsetekBEZczynszu,
                okres=months,
            )
            kd_result = KosztDziennyCalculator(kd_input).calculate()

            # --- SUB-KALKULATOR: STAWKA (V1 port â€“ peĹ‚ny rozkĹ‚ad marĹĽy) ---
            stawka_input = StawkaInput(
                koszt_mc=kd_result.koszt_mc,
                koszt_mc_bez_czynszu=kd_result.koszt_mc_bez_czynszu,
                utrata_wartosci_netto=utrata_z_czynszem,
                koszty_finansowe_netto=finance_res.SumaOdsetekZczynszem,
                ubezpieczenie_netto=insurance_total,
                samochod_zastepczy_netto=rc_total,
                koszty_dodatkowe_netto=additional_costs_total,
                opony_netto=tires_total,
                serwis_netto=service_total,
                okres=months,
                marza=margin_pct,
                czynsz_inicjalny=float(finance_res.CzynszInicjalnyNetto),
            )
            stawka_result = StawkaCalculator(stawka_input).calculate()

            # --- SUB-KALKULATOR: BUDĹ»ET MARKETINGOWY (V1 port) ---
            vat_rate_mult = getattr(self.settings, "vat_rate", 1.23)
            if vat_rate_mult > 10.0:
                vat_rate_mult = 1.0 + (vat_rate_mult / 100.0)
            budzet_mktg_ltr = getattr(self.settings, "budzet_marketingowy_ltr", 0.0)
            bm_input = BudzetMarketingowyInput(
                wr_przewidywana_cena_sprzedazy=vr_samar,
                stawka_vat=vat_rate_mult,
                budzet_marketingowy_ltr=budzet_mktg_ltr,
            )
            bm_result = BudzetMarketingowyCalculator(bm_input).calculate()

            # Wyniki z nowego StawkaCalculator (uĹĽyte bezpoĹ›rednio niĹĽej)

            # --- WYNIK OSTATECZNY (FLAT V1 FORMAT) ---
            def to_koszt_dict(k_item):
                return {
                    "RozkladMarzy": k_item.rozklad_marzy,
                    "RozkladMarzyKorekta": k_item.rozklad_marzy_korekta,
                    "KwotaMarzy": round(k_item.kwota_marzy, 0),
                    "KwotaMarzyKorekta": round(k_item.kwota_marzy_korekta, 0),
                    "KosztPlusMarza": round(k_item.koszt_plus_marza, 0),
                    "KosztPlusMarzaKorekta": round(k_item.koszt_plus_marza_korekta, 0),
                }

            report_html = ""

            cells.append(
                {
                    "Okres": months,
                    "Przebieg": km_per_year,
                    "PrzebiegKontrakt": total_km,
                    # 1. Stawka (Math.Round(0))
                    "LacznaStawka": round(stawka_result.oferowana_stawka, 0),
                    "CzynszFinansowy": round(stawka_result.czynsz_finansowy, 0),
                    "CzynszTechniczny": round(stawka_result.czynsz_techniczny, 0),
                    "Ubezpieczenie": round(
                        stawka_result.koszt_ubezpieczenie.koszt_plus_marza_korekta, 0
                    ),
                    "Serwis": round(
                        stawka_result.koszt_serwis.koszt_plus_marza_korekta, 0
                    ),
                    "Admin": round(
                        stawka_result.koszt_admin.koszt_plus_marza_korekta, 0
                    ),
                    "Opony": round(
                        stawka_result.koszt_opony.koszt_plus_marza_korekta, 0
                    ),
                    "SamochodZastepczy": round(
                        stawka_result.koszt_samochod_zastepczy.koszt_plus_marza_korekta,
                        0,
                    ),
                    "Przychod": round(stawka_result.przychod, 0),
                    "PodstawaMarzy": stawka_result.podstawa_marzy,
                    "MarzaMiesiac": round(stawka_result.marza_mc, 0),
                    "MarzaNaKontrakcie": round(stawka_result.marza_na_kontrakcie, 0),
                    "MarzaNaKontrakcieProcent": stawka_result.marza_na_kontrakcie_procent,
                    "KosztyLaczneMC": stawka_result.koszty_laczne_mc,
                    "KosztFinansowyLacznie": round(
                        stawka_result.koszt_finansowy_lacznie, 0
                    ),
                    "KosztFinansowyMiesiecznie": round(
                        stawka_result.koszt_finansowy_miesiecznie, 0
                    ),
                    "Koszt": [
                        to_koszt_dict(stawka_result.koszt_finansowy),
                        to_koszt_dict(stawka_result.koszt_ubezpieczenie),
                        to_koszt_dict(stawka_result.koszt_samochod_zastepczy),
                        to_koszt_dict(stawka_result.koszt_serwis),
                        to_koszt_dict(stawka_result.koszt_opony),
                        to_koszt_dict(stawka_result.koszt_admin),
                    ],
                    # 2. Zakup (decimal - bez zaokrÄ…gleĹ„)
                    "CenaZakupu": capex_res.CenaZakupu,
                    "CenaZakupuBezOpon": capex_res.CenaZakupuBezOpon,
                    "CenaZakupuBezOponIOpcjiSerwisowych": capex_res.CenaZakupuBezOponIOpcjiSerwisowych,
                    "CenaZakupuBezOponIOpcjiSerwisowychIPakietu": capex_res.CenaZakupuBezOponIOpcjiSerwisowychIPakietu,
                    "CenaKatalogowaNetto": capex_res.CenaKatalogowaNetto,
                    "RabatKwotowo": capex_res.RabatKwotowo,
                    "GsmCapexNetto": capex_res.gsm_capex_net,
                    "OpcjeSerwisoweSumaNetto": capex_res.total_service_options,
                    # 3. Utrata WartoĹ›ci
                    "WR": vr_samar,
                    "WRdlaLO": round(rv_res.get("WRdlaLO", vr_samar), 0),
                    "UtrataWartosci": round(utrata_z_czynszem, 0),
                    "KorektaZaPrzebiegKwotowo": round(
                        rv_res.get("KorektaZaPrzebiegKwotowo", 0.0), 0
                    ),
                    "KorektaAdministracyjnaKwotowo": 0.0,
                    # 4. Finanse
                    "CzynszInicjalnyProcent": finance_res.CzynszInicjalnyProcent,
                    "CzynszInicjalnyNetto": round(finance_res.CzynszInicjalnyNetto, 0),
                    "LacznyKosztCzesciOdsetkowejRaty": round(
                        finance_res.SumaOdsetekZczynszem, 0
                    ),
                    "SumaOdsetekBezCzynszuInicjalnego": round(
                        finance_res.SumaOdsetekBEZczynszu, 0
                    ),
                    # 5. Opony
                    "LacznyKosztOpon": round(tires_total, 0),
                    "IloscOpon": round(tires_res["IloscOpon"], 0),
                    "Cena1KompletOpon": round(
                        tires_res.get("Cena1KompletOpon", 0.0), 0
                    ),
                    "Koszt1KplOpon": round(tires_res.get("Koszt1KplOpon", 0.0), 0),
                    # 6. Serwis
                    "LacznieKosztySerwisowe": round(service_total, 0),
                    "KosztySerwisowe": round(service_total, 0),
                    # 7. PozostaĹ‚e
                    "LacznieUbezpieczenie": round(insurance_total, 0),
                    "KosztyDodatkowe": round(additional_costs_total, 0),
                    "LacznieSamochodZastepczy": round(rc_total, 0),
                    "KosztyOgolem": round(kd_result.koszty_ogolem, 0),
                    "KosztDzienny": round(kd_result.koszt_dzienny, 2),
                    "AmortyzacjaProcent": procent_amortyzacji_miesiecznie,
                    "KorektaWRMaks": round(bm_result.korekta_wr_maks, 2),
                    # 8. Diagnostyka
                    "ReportHtml": report_html,
                    # 9. Ĺšlad rewizyjny (Calculation Trace)
                    "calculation_trace": (
                        capex_res.trace
                        + rv_res.get("trace", [])
                        + (amort_result.trace if "amort_result" in locals() else [])
                        + tires_res.get("trace", [])
                        + service_from_new_dict.get("trace", [])
                        + insurance_res.get("trace", [])
                        + rc_res.get("trace", [])
                        + add_calc_res.get("trace", [])
                        + finance_res.trace
                        + kd_result.trace
                        + stawka_result.trace
                        + bm_result.trace
                    ),
                    # Extra technical output (status/warnings)
                    "status": "OK" if total_km <= 200000 else "WARNING_HIGH_KM",
                    "warnings": {
                        "service_fallback_used": service_fallback_used,
                        "replacement_car_missing": rc_base == 0.0
                        and self.input_data.replacement_car_enabled,
                    },
                }
            )
            cells[-1]["ReportHtml"] = _build_report_html(cells[-1])

        return cells
