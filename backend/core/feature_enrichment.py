"""Feature enrichment pipeline.

Reads card_summary data (standard_equipment, paid_options, direct fields)
from vehicle_synthesis and creates vehicle_feature_evidence records.
Then calls the resolver to build vehicle_feature_state.

Matching strategy: LLM-based semantic matching (Gemini Flash, batch call)
replaces the former deterministic fuzzy substring matcher.  This avoids
false positives such as "Koło zapasowe z felgą aluminiową" being matched
to the feature "felga aluminiowa".
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from google.genai import types

from core.body_type_matcher import BODY_ALIAS_MAP as _BODY_ALIAS_MAP
from core.database import supabase as sb_client
from core.feature_resolver import resolve_vehicle_features
from core.gemini_client import SAFETY_SETTINGS_PERMISSIVE, get_gemini_client

logger = logging.getLogger(__name__)

# Minimum confidence required to accept an LLM match.
_CONFIDENCE_THRESHOLD = 0.70

# Lower threshold for package-decomposed features (LLM knowledge, not from doc).
_PACKAGE_CONFIDENCE_THRESHOLD = 0.75

# Heuristic keywords to detect package names in paid_options.
_PACKAGE_KEYWORDS: frozenset[str] = frozenset(
    {
        "pakiet",
        "pack",
        "package",
        "edition",
        "paket",
    }
)

# Direct card_summary field → feature_key mappings (text/bool).
_DIRECT_FIELD_MAP: dict[str, str] = {
    "fuel": "paliwo",
    "transmission": "skrzynia_biegow",
    "drive_type": "naped",
    "body_style": "body_style",
    "number_of_seats": "liczba_miejsc",
    "has_tow_hook": "hak_holowniczy",
    "is_metalic_paint": "lakier_metalik",
    "has_automatic_ac": "klimatyzacja_automatyczna",
}

# Direct numeric field → feature_key mappings.
# card_summary fields that contain numeric values → universal_features keys.
_NUMERIC_DIRECT_MAP: dict[str, tuple[str, str]] = {
    # card_summary_key: (feature_key, unit)
    "power_hp": ("moc_silnika_km", "KM"),
    "engine_capacity_cc": ("pojemnosc_silnika", "cm³"),
    "length_mm": ("długość_pojazdu_w_mm_bez_haka", "mm"),
    "width_mm": ("szerokość_pojazdu_rozłożone_lusterka_w_mm", "mm"),
    "height_mm": ("wysokość_pojazdu_w_mm", "mm"),
    "wheelbase_mm": ("wheelbase_mm", "mm"),
    "cargo_volume_l": ("kubatura_przestrzeni_ładunkowej_w_m3", "m³"),
    "cargo_volume_m3": ("kubatura_przestrzeni_ładunkowej_w_m3", "m³"),
    "cargo_length_mm": ("długość_przestrzeni_ładunkowej_w_mm", "mm"),
    "cargo_width_mm": ("szerokość_przestrzeni_ładunkowej_w_mm", "mm"),
    "cargo_height_mm": ("wysokość_przestrzeni_ładunkowej_w_mm", "mm"),
    "payload_kg": ("dopuszczalna_ładowność_w_kg", "kg"),
    "dmc_kg": ("dmc_kg", "kg"),
    "gross_vehicle_weight_kg": ("dmc_kg", "kg"),
    "curb_weight_kg": ("curb_weight_kg", "kg"),
    "euro_pallets": ("ilość_europalet", "szt"),
    "battery_capacity_kwh": (
        "pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh",
        "kWh",
    ),
    "ev_range_km": ("zasięg_wltp_dla_pojazdów_elektrycznych_w_km", "km"),
    # NOTE: "seats" is handled by _DIRECT_FIELD_MAP ("number_of_seats")
}

# Canonical drive type values — ALL raw LLM outputs are normalized to these.
_CANONICAL_DRIVE_FWD = "FWD"
_CANONICAL_DRIVE_RWD = "RWD"
_CANONICAL_DRIVE_AWD = "AWD"

# Exact-match map (case-insensitive via .strip().lower()).
_DRIVE_TYPE_EXACT: dict[str, str] = {
    "napęd fwd": _CANONICAL_DRIVE_FWD,
    "fwd": _CANONICAL_DRIVE_FWD,
    "4x2": _CANONICAL_DRIVE_FWD,
    "4x2 (fwd)": _CANONICAL_DRIVE_FWD,
    "napęd przedni": _CANONICAL_DRIVE_FWD,
    "napęd przedni (fwd)": _CANONICAL_DRIVE_FWD,
    "front-wheel drive": _CANONICAL_DRIVE_FWD,
    "na przednią oś": _CANONICAL_DRIVE_FWD,
    "przedni": _CANONICAL_DRIVE_FWD,
    "napęd rwd": _CANONICAL_DRIVE_RWD,
    "rwd": _CANONICAL_DRIVE_RWD,
    "4x2 (rwd)": _CANONICAL_DRIVE_RWD,
    "napęd tylny": _CANONICAL_DRIVE_RWD,
    "rear-wheel drive": _CANONICAL_DRIVE_RWD,
    "na tylną oś": _CANONICAL_DRIVE_RWD,
    "tylny": _CANONICAL_DRIVE_RWD,
    "hinterradantrieb": _CANONICAL_DRIVE_RWD,
    "napęd awd": _CANONICAL_DRIVE_AWD,
    "awd": _CANONICAL_DRIVE_AWD,
    "4x4": _CANONICAL_DRIVE_AWD,
    "4x4 (awd)": _CANONICAL_DRIVE_AWD,
    "all-wheel drive": _CANONICAL_DRIVE_AWD,
    "napęd na wszystkie koła": _CANONICAL_DRIVE_AWD,
    "napęd integralny": _CANONICAL_DRIVE_AWD,
}

# Substring keywords → canonical (checked via `in` on lowered text).
_DRIVE_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("4motion", _CANONICAL_DRIVE_AWD),
    ("quattro", _CANONICAL_DRIVE_AWD),
    ("xdrive", _CANONICAL_DRIVE_AWD),
    ("4matic", _CANONICAL_DRIVE_AWD),
    ("all4", _CANONICAL_DRIVE_AWD),
    ("e-4orce", _CANONICAL_DRIVE_AWD),
    ("4drive", _CANONICAL_DRIVE_AWD),
    ("allgrip", _CANONICAL_DRIVE_AWD),
    ("e-ts", _CANONICAL_DRIVE_AWD),
    ("4x4", _CANONICAL_DRIVE_AWD),
    ("all-wheel", _CANONICAL_DRIVE_AWD),
    ("wszystkie koła", _CANONICAL_DRIVE_AWD),
    ("integralny", _CANONICAL_DRIVE_AWD),
    ("rear-wheel", _CANONICAL_DRIVE_RWD),
    ("tylną oś", _CANONICAL_DRIVE_RWD),
    ("front-wheel", _CANONICAL_DRIVE_FWD),
    ("przednią oś", _CANONICAL_DRIVE_FWD),
]


class LLMMatchItem(BaseModel):
    item: str = Field(description="Original equipment item name (verbatim).")
    feature_key: str = Field(
        default="",
        description="Matched feature_key from the catalog, or empty string when no match.",
    )
    confidence: float = Field(description="Match certainty 0.0-1.0.")


class LLMMatchesSchema(BaseModel):
    matches: list[LLMMatchItem]


class UtilityMatchItem(BaseModel):
    item_name: str = Field(description="Original utility feature name.")
    feature_key: str = Field(
        default="",
        description="Matched feature_key from the catalog, or empty string when no match.",
    )
    value_num: float | None = Field(
        default=None, description="Wyciągnięta wartość liczbowa z cechy."
    )
    unit: str = Field(default="", description="Jednostka wyciągnięta z tekstu.")
    confidence: float = Field(description="Match certainty 0.0-1.0.")


class UtilityMatchesSchema(BaseModel):
    matches: list[UtilityMatchItem]


class PackageContentsSchema(BaseModel):
    package_name: str
    contents: list[str]


class PackagesSchema(BaseModel):
    packages: list[PackageContentsSchema]


def _normalize_drive_type(raw: str) -> str:
    """Normalize a raw drive_type string to one of 3 canonical values.

    Returns the original string unchanged only if no mapping is found
    (should not happen in practice — log a warning in calling code).
    """
    key = raw.strip().lower()
    if not key:
        return raw

    # 1. Exact match
    if key in _DRIVE_TYPE_EXACT:
        return _DRIVE_TYPE_EXACT[key]

    # 2. Substring / keyword match
    for keyword, canonical in _DRIVE_TYPE_KEYWORDS:
        if keyword in key:
            return canonical

    # 3. No match — return as-is (caller should log warning)
    return raw


# Known canonical body type names (used to suppress spurious warnings).
_CANONICAL_BODY_TYPE_NAMES: frozenset[str] = frozenset(
    {
        "Hatchback",
        "Sedan",
        "Kombi",
        "SUV",
        "Liftback",
        "Coupe",
        "Cabrio",
        "Minivan",
        "Wieloosobowy",
        "Pickup",
        "Furgon",
        "Podwozie",
        "Furgon Brygadowy",
        "Podwozie z kabiną",
        "Van",
    }
)


def _normalize_body_style(raw: str) -> str:
    """Normalize raw body_style string to a canonical body_types.name.

    Uses BODY_ALIAS_MAP from body_type_matcher (single source of truth).
    Falls back to title-cased input if no mapping is found.

    NOTE: Uses exact lookup only (no substring matching) to avoid false
    positives e.g. 'VAN' substring-matching 'PANEL VAN' alias.
    """
    stripped = raw.strip()
    if not stripped:
        return raw
    upper = stripped.upper()

    # 1. Direct alias lookup (exact match on uppercased input)
    canonical = _BODY_ALIAS_MAP.get(upper)
    if canonical:
        return canonical

    # 2. No mapping — normalize casing (SUV/Van stay as-is, rest → Title Case)
    if upper == "SUV":
        return "SUV"
    if upper == "VAN":
        return "Van"
    return stripped.title()


def _safe_parse_num(raw_value: Any) -> float | None:
    """Safely extract a numeric value from a string or number."""
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    if isinstance(raw_value, str):
        # Usuń spacje przed walidacją (często 1 200,50)
        cleaned = raw_value.strip().replace(" ", "")

        # Oczyszczenie z niedozwolonych znaków
        cleaned = re.sub(r"[^\d,\.\-]", "", cleaned)
        if not cleaned:
            return None

        # Obsługa wariantu z tysięcznym separatorem i miejscami po przecinku
        if "." in cleaned and "," in cleaned:
            last_dot = cleaned.rfind(".")
            last_comma = cleaned.rfind(",")
            if last_comma > last_dot:
                # "1.250,55"
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # "1,250.55"
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        match = re.match(r"^-?\d+\.?\d*", cleaned)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def _build_feature_catalog_text(features: list[dict[str, Any]]) -> str:
    """Build a compact text representation of the feature catalog."""
    lines = [
        f"- {f['feature_key']}: {f['display_name']}"
        for f in features
        if f.get("feature_key") and f.get("display_name")
    ]
    return "\n".join(lines)


async def _llm_match_equipment(
    equipment_items: list[str],
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Batch LLM call: equipment items → matched features.

    Sends all items in a single Gemini Flash call with temperature=0.0
    and structured JSON output.  Returns only matches whose confidence
    meets or exceeds ``_CONFIDENCE_THRESHOLD``.

    Fail-fast: Rzuca poważnym błędem (wyjątkiem) z logami,
    jesli wywołanie API do LLMa nie zadziała – aby nie kontynuować błędnego zapisu do bazy.

    Parameters
    ----------
    equipment_items:
        Raw names from standard_equipment or paid_options.
    features:
        Rows from ``universal_features`` (need ``feature_key`` + ``display_name``).

    Returns
    -------
    list[dict]
        ``[{"item": str, "feature_key": str, "confidence": float}]``
        — only high-confidence matches.
    """
    if not equipment_items or not features:
        return []

    catalog_text = _build_feature_catalog_text(features)
    items_text = "\n".join(f"- {item}" for item in equipment_items)

    prompt = f"""Jesteś ekspertem klasyfikacji wyposażenia pojazdów.

Poniżej znajduje się katalog cech (feature_key: opis):
{catalog_text}

Przyporządkuj każdą z poniższych pozycji wyposażenia do DOKŁADNIE JEDNEJ cechy z katalogu.
Jeśli pozycja nie pasuje do żadnej cechy z katalogu, zwróć pusty feature_key i confidence=0.0.

WAŻNE ZASADY:
1. Dopasowanie musi być semantycznie dokładne — nie wystarczy, że słowo z opisu cechy
   pojawia się w nazwie pozycji (np. "Koło zapasowe z felgą aluminiową" NIE pasuje do
   cechy "felga_aluminiowa" — to osobna kategoria akcesorium).
2. Każda pozycja oceniana jest NIEZALEŻNIE — nie grupuj ich.
3. Zwróć wynik dla KAŻDEJ pozycji z listy, w tej samej kolejności.

Pozycje wyposażenia do dopasowania:
{items_text}
"""

    try:
        client = get_gemini_client()
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=LLMMatchesSchema,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        if not response.parsed:
            return []

        matches = [m.model_dump() for m in response.parsed.matches]

        return [
            m
            for m in matches
            if m.get("feature_key") and m.get("confidence", 0) >= _CONFIDENCE_THRESHOLD
        ]

    except Exception as exc:
        logger.error(
            f"FATAL: LLM feature matching failed for batch of {len(equipment_items)} items: {exc}"
        )
        raise RuntimeError(
            "Zatrzymano proces enrichment - błąd komunikacji z LLM."
        ) from exc


async def _llm_match_utility_features(
    utility_items: list[dict[str, Any]],
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not utility_items or not features:
        return []

    catalog_text = _build_feature_catalog_text(features)
    items_text = "\n".join(
        f"- {item.get('name')}: {item.get('value')}" for item in utility_items
    )

    prompt = f"""Jesteś wnikliwym ekspertem klasyfikacji wymiarów i cech użytkowych.
Poniżej znajduje się katalog ustandaryzowanych cech z systemu bazodanowego (feature_key: opis):
{catalog_text}

Przyporządkuj każdą z poniższych cech wymiarowych do DOKŁADNIE JEDNEJ cechy z katalogu.
Jeśli pozycja nie pasuje (np. wyciągnięta cecha nie jest wymiarem, albo nie ma jej w katalogu), zwróć pusty feature_key i confidence=0.0.

WAŻNE ZASADY:
1. Zawsze wyciągaj "value_num" (liczbę) oraz "unit" (jednostkę) z tekstu wymiaru!
2. Odrzucasz opis słowny i zostawiasz tylko twarde wartości liczbowe dla "value_num". 
3. Dopasowujesz feature_key po przemyśleniu znaczenia wymiaru. Zwróć uwagę na długość przestrzeni bagażowej ("cargo_length"), objętość ("cargo_volume"), itp. 

Pozycje do dopasowania podane w formacie 'Nazwa Cechy: Wartość':
{items_text}
"""

    try:
        client = get_gemini_client()
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=UtilityMatchesSchema,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        if not response.parsed:
            return []

        matches = [m.model_dump() for m in response.parsed.matches]

        return [
            m
            for m in matches
            if m.get("feature_key") and m.get("confidence", 0) >= _CONFIDENCE_THRESHOLD
        ]

    except Exception as exc:
        logger.error(
            f"FATAL: LLM utility matching failed for {len(utility_items)} items: {exc}"
        )
        raise RuntimeError(
            "Zatrzymano proces enrichment - błąd komunikacji z LLM."
        ) from exc


def _is_package_name(name: str) -> bool:
    """Heuristic check: does this option name look like a package?"""
    lower = name.strip().lower()
    return any(kw in lower for kw in _PACKAGE_KEYWORDS)


async def _llm_decompose_packages(
    package_names: list[str],
    brand: str,
    model: str,
) -> dict[str, list[str]]:
    """Ask LLM to decompose manufacturer packages into sub-features.

    Returns a mapping: package_name -> [sub-feature, ...].
    If LLM doesn't know a package, it returns an empty list (safe fallback).
    """
    if not package_names:
        return {}

    items_text = "\n".join(f"- {name}" for name in package_names)

    prompt = f"""Jesteś ekspertem ds. wyposażenia pojazdów marki {brand}.

Dla modelu **{brand} {model}**, wypisz elementy składowe (zawartość) każdego
z poniższych pakietów wyposażeniowych producenta.

Pakiety do rozłożenia:
{items_text}

ZASADY:
1. Dla każdego pakietu wypisz konkretne elementy wyposażenia, które w nim
   są zawarte (np. "Kamera 360°", "Adaptacyjny tempomat ACC", "Asystent
   martwego pola").
2. Wypisuj TYLKO elementy, o których masz pewną wiedzę dla tego konkretnego
   modelu. NIE zgaduj — jeśli nie znasz składu pakietu, zwróć pustą listę.
3. Każdy element powinien być krótką, precyzyjną nazwą wyposażenia.
4. Nie powtarzaj nazwy pakietu jako elementu.
"""

    try:
        client = get_gemini_client()
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=PackagesSchema,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )
        if not response.parsed:
            return {}

        packages = [m.model_dump() for m in response.parsed.packages]

        decomposed: dict[str, list[str]] = {}
        for pkg in packages:
            name = pkg.get("package_name", "")
            contents = pkg.get("contents", [])
            if name and contents:
                decomposed[name] = [
                    c for c in contents if isinstance(c, str) and c.strip()
                ]
                logger.info(
                    "Package '%s' decomposed into %d sub-features",
                    name,
                    len(decomposed[name]),
                )
        return decomposed

    except Exception as exc:
        logger.error(
            f"FATAL: LLM package decomposition failed for {len(package_names)} packages: {exc}"
        )
        raise RuntimeError(
            "Zatrzymano proces enrichment - błąd komunikacji z LLM (pakiety)."
        ) from exc


async def _load_feature_catalog() -> list[dict[str, Any]]:
    """Load all active universal_features from DB asynchronously."""

    def _fetch():
        return (
            sb_client.schema("reverse_search")
            .table("universal_features")
            .select("id, feature_key, display_name, feature_type")
            .execute()
        )

    resp = await asyncio.to_thread(_fetch)
    return resp.data or []


async def enrich_vehicle_features(
    vehicle_id: str,
    synthesis_data: dict[str, Any],
) -> dict[str, Any]:
    """Extract features from card_summary and create evidence.

    Uses LLM-based semantic matching to map equipment names to universal
    features. Direct field mappings (fuel, transmission, …) are applied
    separately without LLM involvement.

    Parameters
    ----------
    vehicle_id:
        UUID of the vehicle in ``vehicle_synthesis``.
    synthesis_data:
        Full ``synthesis_data`` JSON from ``vehicle_synthesis``.

    Returns
    -------
    dict
        Summary dict with counts and any errors.
    """
    card_summary = synthesis_data.get("card_summary", {})
    if not card_summary or not isinstance(card_summary, dict):
        # Fallback to synthesis_data itself (for V1/Flat synthesis)
        card_summary = synthesis_data

    # Guard against completely empty data
    if not isinstance(card_summary, dict) or len(card_summary) < 2:
        return {"error": "No valid vehicle data found", "evidence_created": 0}

    features = await _load_feature_catalog()
    if not features:
        return {"error": "Feature catalog empty", "evidence_created": 0}

    feature_by_key: dict[str, str] = {f["feature_key"]: f["id"] for f in features}

    evidence_batch: list[dict[str, Any]] = []

    # ── 0. Flatten nested utility_features into card_summary for direct mapping ──
    utility_features_list: list[dict] = card_summary.get("utility_features", [])
    if isinstance(utility_features_list, list):
        # Map of partial name in utility_features -> card_summary key
        utility_to_cs_map = {
            "Długość": "length_mm",
            "Szerokość": "width_mm",
            "Wysokość": "height_mm",
            "Rozstaw osi": "wheelbase_mm",
            "Dopuszczalna masa całkowita": "dmc_kg",
            "Masa własna": "curb_weight_kg",
            "Ładowność": "payload_kg",
        }

        for item in utility_features_list:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            value = item.get("value", "")

            for key_match, cs_target in utility_to_cs_map.items():
                if key_match.lower() == name.strip().lower():
                    # Only populate if not already present in card_summary
                    if cs_target not in card_summary or card_summary[cs_target] is None:
                        parsed = _safe_parse_num(value)
                        if parsed is not None:
                            card_summary[cs_target] = parsed
                            logger.info(
                                "Flattened utility feature '%s' -> %s: %s",
                                name,
                                cs_target,
                                parsed,
                            )

    # ── 0b. Flatten 'dimensions' dict into card_summary for direct mapping ──
    dimensions_dict = card_summary.get("dimensions", {})
    if isinstance(dimensions_dict, dict):
        for k, v in dimensions_dict.items():
            if k not in card_summary or card_summary[k] is None:
                parsed = _safe_parse_num(v)
                if parsed is not None:
                    card_summary[k] = parsed

    # ── 1. Standard equipment → LLM match → boolean "present" evidence ──
    std_equipment: list[str] = card_summary.get("standard_equipment", [])
    std_items = [i for i in std_equipment if isinstance(i, str) and i.strip()]

    std_matches = await _llm_match_equipment(std_items, features)
    for match in std_matches:
        feat_id = feature_by_key.get(match["feature_key"])
        if not feat_id:
            continue
        evidence_batch.append(
            {
                "source_vehicle_id": vehicle_id,
                "feature_id": feat_id,
                "source_type": "spec",
                "evidence_status": "observed",
                "value_bool": True,
                "value_text": match["item"],
                "confidence": round(match["confidence"], 4),
            }
        )

    # ── 2. Paid options → LLM match → boolean "present" evidence ──
    paid_options: list[dict] = card_summary.get("paid_options", [])
    opt_names = [
        (opt.get("name") or "").strip()
        for opt in paid_options
        if isinstance(opt, dict) and (opt.get("name") or "").strip()
    ]

    opt_matches = await _llm_match_equipment(opt_names, features)
    for match in opt_matches:
        feat_id = feature_by_key.get(match["feature_key"])
        if not feat_id:
            continue
        evidence_batch.append(
            {
                "source_vehicle_id": vehicle_id,
                "feature_id": feat_id,
                "source_type": "spec",
                "evidence_status": "observed",
                "value_bool": True,
                "value_text": match["item"],
                "confidence": round(match["confidence"], 4),
            }
        )

    # ── 2a. Package Decomposition → LLM decompose → sub-feature matching ──
    brand = (
        card_summary.get("brand")
        or synthesis_data.get("brand")
        or synthesis_data.get("card_summary", {}).get("brand", "")
    ) or ""
    model_name = (
        card_summary.get("model")
        or synthesis_data.get("model")
        or synthesis_data.get("card_summary", {}).get("model", "")
    ) or ""

    # Collect package names from paid_options & standard equipment
    package_names: list[str] = [name for name in opt_names if _is_package_name(name)]
    # Also check standard equipment for package names
    package_names.extend(item for item in std_items if _is_package_name(item))

    pkg_evidence_count = 0
    if package_names and brand:
        decomposed = await _llm_decompose_packages(package_names, brand, model_name)
        all_sub_features: list[str] = []
        sub_feature_to_package: dict[str, str] = {}
        for pkg_name, contents in decomposed.items():
            for sub in contents:
                all_sub_features.append(sub)
                sub_feature_to_package[sub] = pkg_name

        if all_sub_features:
            sub_matches = await _llm_match_equipment(all_sub_features, features)
            for match in sub_matches:
                feat_id = feature_by_key.get(match["feature_key"])
                if not feat_id:
                    continue
                pkg_origin = sub_feature_to_package.get(
                    match["item"], "unknown_package"
                )
                evidence_batch.append(
                    {
                        "source_vehicle_id": vehicle_id,
                        "feature_id": feat_id,
                        "source_type": "package_decomposition",
                        "evidence_status": "inferred",
                        "value_bool": True,
                        "value_text": (f"{match['item']} (z: {pkg_origin})"),
                        "confidence": round(match["confidence"] * 0.9, 4),
                    }
                )
                pkg_evidence_count += 1

        logger.info(
            "Vehicle %s: decomposed %d packages → %d sub-features → "
            "%d evidence records",
            vehicle_id,
            len(package_names),
            len(all_sub_features),
            pkg_evidence_count,
        )

    # ── 2b. Utility Features → LLM match → numeric evidence ──
    utility_features: list[dict] = card_summary.get("utility_features", [])
    valid_utility = [
        opt
        for opt in utility_features
        if isinstance(opt, dict) and opt.get("name") and opt.get("value")
    ]

    utility_matches = await _llm_match_utility_features(valid_utility, features)
    for match in utility_matches:
        feat_id = feature_by_key.get(match["feature_key"])
        if not feat_id:
            continue

        evidence_batch.append(
            {
                "source_vehicle_id": vehicle_id,
                "feature_id": feat_id,
                "source_type": "spec",
                "evidence_status": "observed",
                "value_num": _safe_parse_num(match.get("value_num")),
                "unit": match.get("unit"),
                "value_text": f"{match.get('value_num', '')} {match.get('unit', '')}".strip()
                if match.get("value_num") is not None
                else "",
                "confidence": round(match.get("confidence", 0), 4),
            }
        )

    # ── 3. Direct field mappings (fuel, transmission, etc.) ──
    for cs_field, feat_key in _DIRECT_FIELD_MAP.items():
        value = card_summary.get(cs_field)
        if value is None:
            continue
        feat_id = feature_by_key.get(feat_key)
        if not feat_id:
            continue

        evidence: dict[str, Any] = {
            "source_vehicle_id": vehicle_id,
            "feature_id": feat_id,
            "source_type": "spec",
            "evidence_status": "observed",
            "confidence": 0.95,
        }

        if isinstance(value, bool):
            evidence["value_bool"] = value
        elif isinstance(value, (int, float)):
            evidence["value_num"] = float(value)
        else:
            str_val = str(value).strip()
            if str_val.lower() not in ("brak", "none", "null", ""):
                # Normalize drive_type to canonical values
                if cs_field == "drive_type":
                    normalized = _normalize_drive_type(str_val)
                    if normalized == str_val:
                        logger.warning(
                            "Unknown drive_type value '%s' — not normalized",
                            str_val,
                        )
                    str_val = normalized
                elif cs_field == "body_style":
                    normalized = _normalize_body_style(str_val)
                    if (
                        normalized == str_val
                        and str_val not in _CANONICAL_BODY_TYPE_NAMES
                    ):
                        logger.warning(
                            "Unknown body_style value '%s' — stored as-is",
                            str_val,
                        )
                    str_val = normalized
                evidence["value_text"] = str_val
            else:
                continue

        evidence_batch.append(evidence)

    # ── 3b. Direct numeric field mappings (power_hp, dimensions, etc.) ──
    numeric_count = 0
    for cs_field, (feat_key, unit) in _NUMERIC_DIRECT_MAP.items():
        raw_value = card_summary.get(cs_field)
        parsed = _safe_parse_num(raw_value)
        if parsed is None:
            continue
        feat_id = feature_by_key.get(feat_key)
        if not feat_id:
            logger.debug(
                "Numeric field %s → feature_key %s not found in catalog",
                cs_field,
                feat_key,
            )
            continue

        evidence_batch.append(
            {
                "source_vehicle_id": vehicle_id,
                "feature_id": feat_id,
                "source_type": "spec",
                "evidence_status": "observed",
                "value_num": parsed,
                "unit": unit,
                "value_text": f"{parsed} {unit}",
                "confidence": 0.95,
            }
        )
        numeric_count += 1

    logger.info(
        "Vehicle %s: extracted %d numeric fields from card_summary",
        vehicle_id,
        numeric_count,
    )

    # ── 4. Insert evidence (batch upsert) ──
    created_count = 0
    errors: list[str] = []

    if evidence_batch:
        # Deduplicate to prevent Supabase 'ON CONFLICT DO UPDATE command cannot affect row a second time'
        unique_evidence_map: dict[tuple[str, str, str], dict[str, Any]] = {}
        for ev in evidence_batch:
            key = (ev["source_vehicle_id"], ev["feature_id"], ev["source_type"])
            if key not in unique_evidence_map or ev.get(
                "confidence", 0
            ) > unique_evidence_map[key].get("confidence", 0):
                unique_evidence_map[key] = ev

        deduped_batch = list(unique_evidence_map.values())

        def _do_upsert():
            return (
                sb_client.schema("reverse_search")
                .table("vehicle_feature_evidence")
                .upsert(
                    deduped_batch,
                    on_conflict="source_vehicle_id,feature_id,source_type",
                )
                .execute()
            )

        try:
            await asyncio.to_thread(_do_upsert)
            created_count = len(deduped_batch)
        except Exception as exc:
            msg = f"Evidence batch upsert error: {exc}"
            errors.append(msg)
            logger.warning(msg)

    # ── 5. Resolve features ──
    resolve_result: dict[str, Any] = {}
    if created_count > 0:

        def _do_resolve():
            return resolve_vehicle_features(vehicle_id)

        resolve_result = await asyncio.to_thread(_do_resolve)

    logger.info(
        "Enriched vehicle %s: %d evidence records, %d errors",
        vehicle_id,
        created_count,
        len(errors),
    )

    return {
        "vehicle_id": vehicle_id,
        "evidence_created": created_count,
        "evidence_matched_from": {
            "standard_equipment": len(std_items),
            "paid_options": len(opt_names),
            "packages_decomposed": len(package_names),
            "package_sub_features": pkg_evidence_count,
            "direct_fields": len(_DIRECT_FIELD_MAP),
        },
        "resolve_result": resolve_result,
        "errors": errors,
    }


async def enrich_all_vehicles(
    limit: int = 100,
) -> dict[str, Any]:
    """Batch-enrich all vehicles that have card_summary data."""

    def _fetch_vehicles():
        return (
            sb_client.table("vehicle_synthesis")
            .select("id, synthesis_data")
            .not_.is_("synthesis_data", "null")
            .limit(limit)
            .execute()
        )

    resp = await asyncio.to_thread(_fetch_vehicles)
    vehicles = resp.data or []

    results: list[dict[str, Any]] = []
    total_evidence = 0
    total_errors = 0

    for v in vehicles:
        synthesis = v.get("synthesis_data")
        if not isinstance(synthesis, dict):
            continue
        if not isinstance(synthesis.get("card_summary"), dict):
            continue

        result = await enrich_vehicle_features(v["id"], synthesis)
        results.append(result)
        total_evidence += result.get("evidence_created", 0)
        total_errors += len(result.get("errors", []))

    return {
        "vehicles_processed": len(results),
        "total_evidence_created": total_evidence,
        "total_errors": total_errors,
        "per_vehicle": results,
    }
