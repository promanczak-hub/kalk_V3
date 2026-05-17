import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import supabase
from core.offer_generator import ExcelOfferGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


class OfferItem(BaseModel):
    """Slim payload from frontend cart — backend enriches the rest from DB."""

    id: Optional[str] = None
    brand: str = ""
    model: str = ""
    powertrain: str = ""
    vin_or_config: str = ""
    term: int = 0
    mileage: int = 0
    net_installment: float = 0.0
    contribution: float = 0.0
    margin_pct: Optional[float] = None
    system_recommendation: str = ""
    calculation_data: Dict[str, Any] = {}
    standard_equipment: List[str] = []
    factory_options: List[Any] = []
    dealer_options: List[Any] = []
    matrix_data: Optional[List[Dict[str, Any]]] = None
    notes: str = ""
    overuse_fee: Optional[float] = None  # zł/km — user-picked from dropdown, fallback 0.50


class OfferGenerateRequest(BaseModel):
    client_name: str
    client_nip: str
    client_address: str = ""
    representative: str = ""
    items: List[OfferItem]


def _f(v: Any) -> Optional[float]:
    """Coerce to float — accept str like '12 500,50 zł' too."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(" ", "").replace(" ", "").replace("zł", "")
    s = s.replace(",", ".")
    s = "".join(c for c in s if c.isdigit() or c in ".-")
    try:
        return float(s) if s else None
    except ValueError:
        return None


VAT_RATE = 1.23


def _to_net(value: Optional[float], price_type: str) -> Optional[float]:
    """Convert to net if the source explicitly says brutto."""
    if value is None:
        return None
    if (price_type or "").strip().lower() in ("brutto", "gross"):
        return round(value / VAT_RATE, 2)
    return value


def _option_prices_net_gross(entry: Dict[str, Any]) -> tuple[float, float]:
    """Resolve (net, gross) per-option price. Falls back to VAT 23% conversion
    when only one side is provided, or parses the legacy `price` + `price_type`."""
    pn = _f(entry.get("price_net"))
    pg = _f(entry.get("price_gross"))
    if pn is not None and pg is not None:
        return pn, pg
    if pn is not None:
        return pn, round(pn * VAT_RATE, 2)
    if pg is not None:
        return round(pg / VAT_RATE, 2), pg
    raw = _f(entry.get("price"))
    if raw is None:
        return 0.0, 0.0
    pt = (entry.get("price_type") or "").strip().lower()
    if pt in ("brutto", "gross"):
        return round(raw / VAT_RATE, 2), raw
    # Default: treat raw as net (LTR convention), derive gross.
    return raw, round(raw * VAT_RATE, 2)


def _normalize_options(raw: Any) -> List[tuple[str, float, float]]:
    """Return [(name, price_net, price_gross), ...] from heterogeneous shapes
    (list of dicts/strings, or single service_equipment-shaped dict)."""
    out: List[tuple[str, float, float]] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                name = (entry.get("name") or entry.get("description") or "").strip()
                if name:
                    net, gross = _option_prices_net_gross(entry)
                    out.append((name, net, gross))
            elif isinstance(entry, str) and entry.strip():
                out.append((entry.strip(), 0.0, 0.0))
    elif isinstance(raw, dict):
        components = raw.get("components") or []
        if not components:
            name = (raw.get("name") or "").strip()
            if name:
                net, gross = _option_prices_net_gross(raw)
                out.append((name, net, gross))
        for comp in components:
            if isinstance(comp, dict):
                cname = (comp.get("name") or "").strip()
                if cname:
                    net, gross = _option_prices_net_gross(comp)
                    out.append((cname, net, gross))
    return out


def _split_paid_options(paid_options: Any) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split card_summary.paid_options into (factory, service) by `category` field.
    'Serwisowa/Akcesoria' (and similar) → service; everything else → factory."""
    factory: List[Dict[str, Any]] = []
    service: List[Dict[str, Any]] = []
    if not isinstance(paid_options, list):
        return factory, service
    for opt in paid_options:
        if not isinstance(opt, dict):
            continue
        cat = (opt.get("category") or "").lower()
        if "serwis" in cat or "akcesor" in cat or "dealer" in cat:
            service.append(opt)
        else:
            factory.append(opt)
    return factory, service


# Marketing names for transmissions — pick the specific brand/family fragment
# (DSG, S tronic, PDK …) when the raw text glues a generic word in front
# (e.g. "Automatyczna, DSG 7-stopniowa"). Pure "Manualna 6-biegowa" /
# "Automatyczna 8-stopniowa" stay intact because they're already specific.
_TRANSMISSION_BRAND_PATTERNS = (
    r"DSG\s*\d*[\w\-]*",
    r"S[\s-]?tronic[\w\s\-]*",
    r"Steptronic[\w\s\-]*",
    r"Tiptronic[\w\s\-]*",
    r"Multitronic[\w\s\-]*",
    r"Powershift[\w\s\-]*",
    r"PowerShift[\w\s\-]*",
    r"Speedshift[\w\s\-]*",
    r"AUTOTRONIC[\w\s\-]*",
    r"PDK[\w\s\-]*",
    r"EDC\s*\d*[\w\-]*",
    r"CVT[\w\s\-]*",
    r"e-?CVT[\w\s\-]*",
    r"\d{1,2}[\s-]?G[\s-]?TRONIC[\w\s\-]*",
    r"\d{1,2}[\s-]?(?:AT|MT|DCT|G-Tronic|G\s?Tronic)[\w\-]*",
)

# Generic words that on their own carry no marketing weight — we only drop
# them when a more specific fragment exists in the same string.
_GENERIC_TRANSMISSION_WORDS = ("automatyczna", "manualna", "ręczna", "reczna")


def _extract_transmission_brand(text: str) -> str:
    """Return the first branded gearbox fragment (DSG/S tronic/PDK/…) found in
    `text`, or ''. Doesn't match plain '6-biegowa'/'8-stopniowa' — those are
    handled by `_marketing_transmission` which keeps the surrounding context."""
    if not text:
        return ""
    import re
    for pat in _TRANSMISSION_BRAND_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip(" ,;.-")
    return ""


def _clean_transmission_text(text: str) -> str:
    """Strip leading 'Automatyczna,' or 'Manualna,' prefixes (used when the raw
    text combines generic + specific labels but has no branded keyword)."""
    if not text:
        return ""
    s = str(text).strip(" ,;.-")
    low = s.lower()
    for word in _GENERIC_TRANSMISSION_WORDS:
        # Drop 'Automatyczna,' / 'Automatyczna' when followed by another word.
        if low.startswith(word + ","):
            return s[len(word) + 1:].strip(" ,;.-")
        if low.startswith(word + " ") and len(s) > len(word) + 1:
            # Keep when it's followed by a dimensional descriptor like
            # '6-biegowa' or '8-stopniowa' — the combined form is informative.
            return s
    return s


def _marketing_transmission(
    stan: Dict[str, Any], cs: Dict[str, Any], mai: Dict[str, Any]
) -> str:
    """Pick the most marketing-friendly gearbox name for the offer XLS.

    Priority:
      1. Branded fragment found inside `card_summary.transmission` (e.g. "DSG 7-stopniowa"
         from "Automatyczna, DSG 7-stopniowa").
      2. Branded fragment from `mapped_ai_data.transmission`.
      3. Branded fragment from `stan.gearbox_name`.
      4. Fallback to whichever raw value isn't blank — `cs.transmission` →
         `mai.transmission` → `stan.gearbox_name` → `mai.transmission_type`.
    """
    sources = (
        cs.get("transmission"),
        mai.get("transmission"),
        stan.get("gearbox_name"),
        mai.get("gearbox"),
    )
    for src in sources:
        branded = _extract_transmission_brand(str(src or ""))
        if branded:
            return branded
    for src in sources:
        cleaned = _clean_transmission_text(str(src or ""))
        if cleaned and cleaned.lower() not in ("brak", "—", "none", "null"):
            return cleaned
    fallback = str(mai.get("transmission_type") or stan.get("transmission_type") or "").strip()
    return fallback


# Drive-train tokens we strip from the end of powertrain so they appear as
# their own segment in marketing_name (e.g. "2.0 TSI 310 KM AWD" → powertrain
# "2.0 TSI (310 KM)", drive "AWD"). Doesn't affect tokens that sit inside the
# string, only trailing ones.
_DRIVE_TRAIL_TOKENS = (
    "AWD", "FWD", "RWD", "4x4", "4WD", "quattro", "xDrive", "sDrive", "4Motion",
)


def _strip_trailing_drive_token(text: str) -> str:
    """Drop a trailing drive-train token from a powertrain string."""
    s = text.strip(" ,;.-")
    low = s.lower()
    for tok in _DRIVE_TRAIL_TOKENS:
        tlow = tok.lower()
        if low.endswith(" " + tlow) or low.endswith("," + tlow) or low.endswith("-" + tlow):
            return s[: -len(tok)].strip(" ,;.-")
    return s


def _marketing_powertrain(cs: Dict[str, Any], stan: Dict[str, Any]) -> str:
    """Return engine label as 'X.X TFSI (150 KM)' or 'engine_designation (power KM)'.

    Uses card_summary.powertrain when it already reads as a marketing string,
    otherwise composes from engine_designation + power_hp. Preserves trailing
    descriptors like 'EQ Boost', 'mHEV' that follow the KM token but strips
    drive-train tokens (AWD/FWD/quattro/...) so they show as a separate
    segment in the offer model name."""
    raw = (cs.get("powertrain") or stan.get("powertrain") or "").strip()
    raw = _strip_trailing_drive_token(raw)
    power_hp = _f(cs.get("power_hp")) or _f(stan.get("power_hp"))

    if raw:
        import re
        # Already contains "(NNN KM)" — return as-is, fully preserving suffixes.
        if re.search(r"\(\s*\d+\s*KM\s*\)", raw, flags=re.IGNORECASE):
            return raw
        # Has "NNN KM" — wrap that fragment in parens, keep prefix and suffix.
        m = re.search(r"(\d+)\s*KM", raw, flags=re.IGNORECASE)
        if m:
            wrapped = re.sub(
                r"(\d+)\s*KM",
                lambda mm: f"({mm.group(1)} KM)",
                raw,
                count=1,
                flags=re.IGNORECASE,
            )
            # Collapse double spaces left by replacement.
            return re.sub(r"\s+", " ", wrapped).strip()
        # No KM in string — append from power_hp if available.
        if power_hp:
            return f"{raw} ({int(power_hp)} KM)"
        return raw

    eng = (cs.get("engine_designation") or "").strip()
    if eng and power_hp:
        return f"{eng} ({int(power_hp)} KM)"
    if eng:
        return eng
    if power_hp:
        return f"{int(power_hp)} KM"
    return ""


def _build_marketing_name(
    stan: Dict[str, Any], cs: Dict[str, Any], mai: Dict[str, Any] | None = None
) -> str:
    """Compose 'MARKA MODEL Trim • Silnik (KM) • Skrzynia • Napęd • Nadwozie'
    using bullet separators. Drops empty/'brak'/'—' parts and de-duplicates
    fragments that already appear earlier in the chain (e.g. trim that
    already contains the engine label)."""
    mai = mai or {}
    brand = (stan.get("brand") or "").strip().upper()
    model = (stan.get("model") or "").strip().upper()
    trim = (cs.get("trim_level") or stan.get("trim_level") or "").strip()
    powertrain = _marketing_powertrain(cs, stan)
    transmission = _marketing_transmission(stan, cs, mai)
    drive = (
        cs.get("drive_type") or stan.get("drive_type") or mai.get("drive_type") or ""
    ).strip()
    body = (cs.get("body_style") or stan.get("body_type_name") or mai.get("body_type") or "").strip()

    head_parts: List[str] = []
    if brand:
        head_parts.append(brand)
    if model:
        head_parts.append(model)
    if trim and trim.lower() not in ("brak", "—", "none", "null"):
        head_parts.append(trim)
    head = " ".join(head_parts).strip()

    tail: List[str] = []
    for label in (powertrain, transmission, drive, body):
        if not label:
            continue
        s = label.strip()
        if not s or s.lower() in ("brak", "—", "none", "null"):
            continue
        if s.lower() in head.lower() or any(s.lower() in t.lower() for t in tail):
            continue
        tail.append(s)

    return " • ".join([head, *tail]) if tail else head


def _build_in_rate(stan: Dict[str, Any]) -> Dict[str, Any]:
    toggles = stan.get("toggles") or {}
    tire_params = stan.get("tire_params") or {}
    tire_count_mode = tire_params.get("tire_count_mode")
    z_oponami = stan.get("z_oponami")
    if z_oponami is None:
        z_oponami = tire_count_mode and tire_count_mode != "BRAK"

    cost_type = stan.get("service_cost_type") or "ASO"
    include_servicing = bool(toggles.get("include_servicing", stan.get("include_servicing", False)))

    return {
        "ubezp_oc_ac": bool(
            toggles.get("express_pays_insurance", stan.get("express_pays_insurance", False))
        ),
        "serwis": include_servicing,
        "serwis_typ": cost_type if include_servicing else None,
        "opony": bool(z_oponami),
        "opony_klasa": stan.get("klasa_opony_string") or "",
        "opony_rozmiar": tire_params.get("tire_size") or "",
        "opony_zestawy": stan.get("liczba_kompletow_opon") or tire_params.get("tire_set_count"),
        "auto_zastepcze": bool(
            toggles.get("replacement_car", stan.get("replacement_car_enabled", False))
        ),
        "gps": bool(stan.get("add_gsm_subscription", False)),
    }


def _compute_matrix_breakdown(
    stan: Dict[str, Any],
    term: int,
    annual_mileage: int,
    applied_margin_pct: Optional[float],
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Re-run LTRKalkulator from stan_json and return
    (czynsz_finansowy, czynsz_techniczny, laczna_stawka, marginal_per_km, ilosc_opon)
    for the (term, annual_mileage) cell.

    marginal_per_km = (rate(next_higher_mileage) - rate(current)) * 12 / km_diff
    — the cost of one additional kilometer when stepping from the chosen mileage
    tier to the next higher one in the matrix. Used to suggest overuse fees.

    ilosc_opon is the calculator-derived tire-set count for this cell — used as
    fallback for the 'Ogumienie' column when stan_json doesn't carry an explicit
    liczba_kompletow_opon override.

    Returns Nones on any failure or when no higher tier is available."""
    if not stan or not term or not annual_mileage:
        return None, None, None, None, None
    try:
        from api.schemas.calculator import CalculatorInput
        from core.LTRKalkulator import LTRKalkulator
        from core.control_center import fetch_control_center_settings

        try:
            settings = fetch_control_center_settings()
        except Exception:
            return None, None, None, None, None

        # Older stan_json rows have None for fields that the schema now types as
        # required-with-default (e.g. inne_koszty_serwisowania_netto: float = 0.0).
        # Pydantic v2 rejects None for those even when a default exists; drop the
        # nulls so Pydantic falls back to the field default.
        stan_clean = {k: v for k, v in stan.items() if v is not None}
        try:
            calc_input = CalculatorInput(**stan_clean)
        except Exception as ve:
            # Promoted to warning + exc_info: when fin/tech split silently
            # disappears in the XLS we need to see *which* field failed, not
            # just notice that K/L/J turned red.
            logger.warning(
                "CalculatorInput validation failed (term=%s, mileage=%s): %s",
                term, annual_mileage, str(ve)[:500], exc_info=True,
            )
            return None, None, None, None, None
        if applied_margin_pct is not None:
            calc_input.pricing_margin_pct = float(applied_margin_pct)

        engine = LTRKalkulator(input_data=calc_input, settings=settings, trace_id="offer-gen")
        # build_matrix() returns full cells with CzynszFinansowy/Techniczny;
        # build_reverse_search_matrix() returns slim cells with only LacznaStawka.
        cells = engine.build_matrix()
        same_term = sorted(
            (c for c in cells if int(c.get("Okres", 0)) == int(term)),
            key=lambda c: int(c.get("Przebieg", 0)),
        )
        current = next(
            (c for c in same_term if int(c.get("Przebieg", 0)) == int(annual_mileage)),
            None,
        )
        if not current:
            return None, None, None, None, None

        fin_raw = current.get("CzynszFinansowy")
        tech_raw = current.get("CzynszTechniczny")
        stawka_raw = current.get("LacznaStawka")
        ilosc_opon_raw = current.get("IloscOpon")
        fin = float(fin_raw) if fin_raw is not None else None
        tech = float(tech_raw) if tech_raw is not None else None
        stawka = float(stawka_raw) if stawka_raw is not None else None
        ilosc_opon = float(ilosc_opon_raw) if ilosc_opon_raw is not None else None

        marginal: Optional[float] = None
        higher = [c for c in same_term if int(c.get("Przebieg", 0)) > int(annual_mileage)]
        if higher and stawka is not None:
            nxt = higher[0]
            rate_next_raw = nxt.get("LacznaStawka")
            if rate_next_raw is not None:
                rate_next = float(rate_next_raw)
                km_now = int(current.get("Przebieg", 0))
                km_next = int(nxt.get("Przebieg", 0))
                if km_next > km_now and rate_next > stawka:
                    marginal = (rate_next - stawka) * 12.0 / (km_next - km_now)

        return fin, tech, stawka, marginal, ilosc_opon
    except Exception as e:
        # Promoted to warning + exc_info: silent split-loss in the XLS comes
        # from this except, so we want the full traceback in the log.
        logger.warning(
            "matrix breakdown skipped (term=%s, mileage=%s): %s",
            term, annual_mileage, str(e)[:300], exc_info=True,
        )
    return None, None, None, None, None


def _suggest_overuse_fee(marginal_per_km: Optional[float]) -> float:
    """Suggest overuse fee = marginal per-km cost +65%, snapped to the
    OVERUSE_FEE_OPTIONS grid (0.10..0.80 step 0.01). Falls back to 0.50 zł/km
    when the marginal can't be derived (e.g. customer chose the highest mileage
    tier in the matrix)."""
    if marginal_per_km is None or marginal_per_km <= 0:
        return 0.50
    suggested = round(marginal_per_km * 1.65, 2)
    return max(0.10, min(0.80, suggested))


def _format_cost_breakdown(in_rate: Dict[str, Any]) -> str:
    """'Rodzaj kosztów' = service-table type only ('ASO' or 'nonASO')."""
    if not in_rate.get("serwis"):
        return "—"
    return in_rate.get("serwis_typ") or "—"


def _format_tire_display(in_rate: Dict[str, Any]) -> str:
    """Build 'Ogumienie' cell value: '<klasa> • <ilość> kpl' / 'Bez opon' / '—'."""
    if not in_rate.get("opony"):
        return "Bez opon"
    klasa = (in_rate.get("opony_klasa") or "").strip()
    ilosc = in_rate.get("opony_zestawy")
    ilosc_str = f"{float(ilosc):.2f}".replace(".", ",") if ilosc else None
    if klasa and ilosc_str:
        return f"{klasa} • {ilosc_str} kpl"
    if klasa:
        return klasa
    if ilosc_str:
        return f"{ilosc_str} kpl"
    return "—"


def _load_synthesis_fallback(vehicle_id: Optional[str]) -> Dict[str, Any]:
    """Fetch vehicle_synthesis row and shape it into a stan-like dict.

    Used when no kalkulacja exists for the cart item — gives the offer XLSX
    enough vehicle context (spec, options, standard equipment, SAMAR) without
    requiring the user to first run a full LTR calculation.
    Returns {} on miss or any error.
    """
    if not vehicle_id:
        return {}
    try:
        res = (
            supabase.table("vehicle_synthesis")
            .select("brand, model, offer_number, synthesis_data")
            .eq("id", vehicle_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return {}
        row = res.data[0]
        synth = row.get("synthesis_data") or {}
        cs = synth.get("card_summary") or {}
        mai = synth.get("mapped_ai_data") or {}
        return {
            "brand": row.get("brand") or synth.get("brand") or mai.get("brand"),
            "model": row.get("model") or synth.get("model") or mai.get("model"),
            "trim_level": synth.get("trim_level") or cs.get("trim_level") or mai.get("trim_level"),
            "offer_number": row.get("offer_number") or synth.get("offer_number"),
            "configuration_code": synth.get("configuration_code"),
            "card_summary": cs,
            "mapped_ai_data": mai,
            "_synthetic": True,  # tag — skip _compute_matrix_breakdown for non-CalculatorInput shapes
        }
    except Exception as e:
        logger.info("vehicle_synthesis fallback skipped: %s", str(e)[:200])
        return {}


def _resolve_vehicle_id_from_calc_data(calc_data: Dict[str, Any]) -> Optional[str]:
    """Cart items from search spread the car into calculation_data — vehicle_id
    can hide under different keys depending on the source (vehicle_id, id,
    car_id) or be derivable from configuration_code via vehicle_synthesis."""
    vid = calc_data.get("vehicle_id") or calc_data.get("car_id")
    if vid:
        return vid
    raw_id = calc_data.get("id")
    if raw_id and isinstance(raw_id, str) and len(raw_id) == 36 and raw_id.count("-") == 4:
        # Looks like a UUID — likely the vehicle_synthesis primary key.
        return raw_id
    cfg = calc_data.get("configuration_code")
    if cfg:
        try:
            res = (
                supabase.table("vehicle_synthesis")
                .select("id")
                .filter("synthesis_data->>configuration_code", "eq", cfg)
                .limit(1)
                .execute()
            )
            if res.data:
                return res.data[0].get("id")
        except Exception as e:
            logger.info("vehicle_synthesis lookup by config failed: %s", str(e)[:200])
    return None


def _resolve_kalk_id_via_matrix_cache(
    vehicle_id: Optional[str],
    term: Optional[int],
    annual_mileage: Optional[int],
) -> Optional[str]:
    """Recover the kalkulacja_id that produced a given (vehicle, term, mileage)
    matrix cell. Used when the cart item didn't include kalkulacja_id (e.g.
    legacy cart entries, or search responses where the field was null), but the
    matrix cache row clearly points at a real kalkulacja."""
    if not vehicle_id or not term or not annual_mileage:
        return None
    try:
        res = (
            supabase.table("vehicle_matrix_cache")
            .select("kalkulacja_id, calculated_at")
            .eq("vehicle_id", vehicle_id)
            .eq("duration_months", int(term))
            .eq("annual_mileage", int(annual_mileage))
            .not_.is_("kalkulacja_id", "null")
            .order("calculated_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0].get("kalkulacja_id")
    except Exception as e:
        logger.info("matrix cache lookup failed: %s", str(e)[:200])
    return None


def _load_package_contents_map(vehicle_id: Optional[str]) -> Dict[str, List[str]]:
    """Lower-cased {package_name: [sub_feature_name, ...]} for offer XLS.

    Wraps `feature_enrichment.fetch_package_contents()` (reads from
    `reverse_search.vehicle_feature_evidence` — note the **non-default
    schema**; queries via the default `public` schema will report the
    table as missing). Lower-cased key + sorted sub-features for stable,
    case-insensitive matching against option names in the offer.
    Returns {} on miss/error (XLS just won't render expandable rows).
    """
    if not vehicle_id:
        return {}
    try:
        from core.feature_enrichment import fetch_package_contents

        raw = fetch_package_contents(vehicle_id)
    except Exception as e:
        logger.info("package contents skipped [%s]: %s", vehicle_id, str(e)[:200])
        return {}
    return {
        pkg.strip().lower(): sorted({name for name, _conf in subs})
        for pkg, subs in raw.items()
        if subs
    }


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _kalk_id_from_item_id(item_id: Any) -> Optional[str]:
    """Cart items added from the VertexExtractor matrix encode the kalkulacja
    UUID as the prefix of `item.id` (format: `<kalk_uuid>_<term>_<contract_km>`)
    but historically didn't propagate it into calculation_data. Pull it back
    from the prefix so legacy cart entries still enrich properly."""
    if not item_id or not isinstance(item_id, str):
        return None
    m = _UUID_RE.match(item_id)
    return m.group(0) if m else None


def _preflight_cache_key(item: Dict[str, Any]) -> str:
    """Stable Redis key for an offer item's enriched form. Includes only fields
    that affect _enrich_item output: identity + matrix-cell coordinates +
    margin. Notes/overuse_fee are display-only and don't trigger re-enrich."""
    import hashlib
    parts = [
        str(item.get("id") or ""),
        str(item.get("kalkulacja_id") or ""),
        str(item.get("vehicle_id") or ""),
        str(int(item.get("term") or 0)),
        str(int(item.get("mileage") or 0)),
        f"{float(item.get('margin_pct') or 0):.4f}",
        str(item.get("vin_or_config") or ""),
    ]
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"kalk_v3:offer_enriched:{h}"


def _get_cached_enriched(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return cached _enrich_item result, or None on miss / Redis down."""
    try:
        from core.redis_cache import _get_client
        client = _get_client()
        if client is None:
            return None
        cached = client.get(_preflight_cache_key(item))
        if cached:
            import json as _json
            return _json.loads(cached)
    except Exception as e:
        logger.debug("offer enrich cache get failed: %s", str(e)[:200])
    return None


def _set_cached_enriched(item: Dict[str, Any], enriched: Dict[str, Any]) -> None:
    """Store enriched item in Redis (30min TTL). Silent on failure."""
    try:
        from core.redis_cache import _get_client
        client = _get_client()
        if client is None:
            return
        import json as _json
        client.setex(
            _preflight_cache_key(item),
            1800,  # 30 minutes — covers typical cart review window
            _json.dumps(enriched, default=str),
        )
    except Exception as e:
        logger.debug("offer enrich cache set failed: %s", str(e)[:200])


def _enrich_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Pull stan_json + numer_kalkulacji + matrix breakdown for a single offer item."""
    calc_data = item.get("calculation_data") or {}
    kalk_id = (
        calc_data.get("kalkulacja_id")
        or item.get("kalkulacja_id")
        or _kalk_id_from_item_id(item.get("id"))
    )
    vehicle_id = (
        item.get("vehicle_id")
        or calc_data.get("vehicle_id")
        or _resolve_vehicle_id_from_calc_data(calc_data)
    )

    stan: Dict[str, Any] = {}
    numer = None
    stan_loaded = False

    def _load_stan(kid: str) -> bool:
        nonlocal stan, numer, stan_loaded
        try:
            res = (
                supabase.table("ltr_kalkulacje")
                .select("numer_kalkulacji, stan_json")
                .eq("id", kid)
                .limit(1)
                .execute()
            )
            if res.data:
                row = res.data[0]
                numer = row.get("numer_kalkulacji")
                stan = row.get("stan_json") or {}
                stan_loaded = bool(stan)
                return stan_loaded
        except Exception:
            pass
        return False

    if kalk_id:
        _load_stan(kalk_id)

    # Recovery path: cart item came from search results but didn't carry a
    # kalkulacja_id (or the one it carried is stale). The matrix cache row for
    # this (vehicle, term, mileage) cell knows which kalkulacja produced it —
    # use that to load stan_json and enable fin/tech split + cost breakdown.
    if not stan_loaded:
        recovered = _resolve_kalk_id_via_matrix_cache(
            vehicle_id,
            int(item.get("term") or 0),
            int(item.get("mileage") or 0),
        )
        if recovered and recovered != kalk_id:
            logger.info(
                "Recovered kalk_id=%s via matrix cache (cart had %r, vehicle=%s, term=%s, mileage=%s)",
                recovered, kalk_id, vehicle_id, item.get("term"), item.get("mileage"),
            )
            kalk_id = recovered
            _load_stan(kalk_id)

    if not stan_loaded:
        stan = _load_synthesis_fallback(vehicle_id)

    cs: Dict[str, Any] = stan.get("card_summary") or {}
    mai: Dict[str, Any] = stan.get("mapped_ai_data") or {}

    # AUTO-generated kalkulacje save only flat top-level keys (no card_summary
    # or mapped_ai_data). Pull the rich PDF-extracted spec from
    # vehicle_synthesis so the marketing name still gets trim / powertrain /
    # transmission / body / drive — without this, those rows show only
    # "BRAND MODEL" in the offer XLS.
    if not cs:
        fallback_vid = stan.get("vehicle_id") or vehicle_id
        if fallback_vid:
            synth = _load_synthesis_fallback(fallback_vid)
            if synth:
                cs = synth.get("card_summary") or cs
                if not mai:
                    mai = synth.get("mapped_ai_data") or mai

    factory_raw, service_raw_from_paid = _split_paid_options(cs.get("paid_options"))

    factory = _normalize_options(stan.get("factory_options"))
    if not factory:
        factory = _normalize_options(factory_raw)
    service = _normalize_options(stan.get("service_options"))
    if not service:
        service = _normalize_options(service_raw_from_paid) + _normalize_options(cs.get("service_equipment"))

    standard = (
        stan.get("standard_equipment")
        or cs.get("standard_equipment")
        or item.get("standard_equipment")
        or []
    )
    if isinstance(standard, list):
        standard_strs = [str(s) for s in standard if s]
    else:
        standard_strs = []

    base_price_net = _f(stan.get("base_price_net")) or _f(calc_data.get("base_price_net")) or 0.0
    factory_total = sum(net for _, net, _ in factory)
    service_total = sum(net for _, net, _ in service)

    contribution_pln = _f(item.get("contribution"))
    if contribution_pln is None or contribution_pln == 0.0:
        contribution_pct = _f(stan.get("initial_deposit_pct")) or 0.0
        contribution_pln = round(base_price_net * contribution_pct / 100, 0) if contribution_pct else 0.0
    elif base_price_net:
        # If frontend sent contribution as raw PLN, derive pct for display
        contribution_pct = round(contribution_pln / base_price_net * 100, 1)
    else:
        contribution_pct = None

    in_rate = _build_in_rate(stan)

    marketing_name = _build_marketing_name(stan, cs, mai) or item.get("powertrain") or "—"

    config_code = (stan.get("configuration_code") or item.get("vin_or_config") or "").strip()
    brand_str = (stan.get("brand") or item.get("brand") or "").strip()
    model_str = (stan.get("model") or item.get("model") or "").strip()
    base_price_for_label = _f(stan.get("base_price_net")) or _f(calc_data.get("base_price_net"))
    if config_code and config_code.lower() not in ("brak", "—", "none"):
        sheet_label = config_code
    elif brand_str or model_str:
        price_token = (
            f" {int(round(base_price_for_label / 1000))}k"
            if base_price_for_label and base_price_for_label > 0
            else ""
        )
        sheet_label = f"{brand_str} {model_str}{price_token}".strip()
    else:
        sheet_label = numer or "Pojazd"

    if stan_loaded and not stan.get("_synthetic"):
        fin, tech, stawka_recalc, marginal_per_km, tires_count_recalc = _compute_matrix_breakdown(
            stan,
            term=int(item.get("term") or 0),
            annual_mileage=int(item.get("mileage") or 0),
            applied_margin_pct=item.get("margin_pct"),
        )
    else:
        fin, tech, stawka_recalc, marginal_per_km, tires_count_recalc = None, None, None, None, None

    # Anchor K+L to the rate the customer was actually quoted.
    # net_installment in the cart came from vehicle_matrix_cache and was shown
    # to the user — that's the contractual rate. The fin/tech split is derived
    # from a fresh build_matrix call which can diverge from cache (calc changes,
    # control_center tweaks, etc.); when it does, K+L would NOT equal J.
    # Solution: keep the fin/tech ratio from the recompute, but rescale so
    # the integer-rounded sum equals net_installment to the złoty.
    cart_rate = _f(item.get("net_installment"))
    if (
        fin is not None and tech is not None
        and cart_rate is not None and cart_rate > 0
    ):
        recalc_total = float(fin) + float(tech)
        if recalc_total > 0:
            # Use the ratio from the recompute, then round so K+L == J exactly.
            target = round(cart_rate)
            fin_ratio = float(fin) / recalc_total
            fin_rounded = round(target * fin_ratio)
            tech_rounded = target - fin_rounded
            if abs(recalc_total - cart_rate) / cart_rate > 0.01:
                logger.warning(
                    "Offer K+L rescaled: kalk=%s cart_rate=%.0f recalc_total=%.0f "
                    "fin %s->%s tech %s->%s (calc drift from cache)",
                    item.get("kalkulacja_id") or kalk_id or "?",
                    cart_rate, recalc_total,
                    fin, fin_rounded, tech, tech_rounded,
                )
            fin = float(fin_rounded)
            tech = float(tech_rounded)

    # User input (liczba_kompletow_opon / tire_set_count) is rare; most rows
    # rely on the calculator to compute IloscOpon from contract km + tire
    # thresholds. Backfill so the 'Ogumienie' column shows the same number
    # the user sees in the 'Podsumowanie V1' panel.
    if not in_rate.get("opony_zestawy") and tires_count_recalc:
        in_rate["opony_zestawy"] = tires_count_recalc

    # Treat 0.0 as "unset" — the dropdown grid starts at 0.10, so a 0 means the
    # user never picked anything and we should suggest based on marginal cost.
    user_overuse_fee = _f(item.get("overuse_fee")) or _f(calc_data.get("opłata_nadprzebieg"))
    overuse_fee = user_overuse_fee or _suggest_overuse_fee(marginal_per_km)

    def _pick(*vals: Any) -> str:
        for v in vals:
            if v is None:
                continue
            s = str(v).strip()
            if s and s.lower() not in ("brak", "—", "none", "null"):
                return s
        return ""

    enriched = {
        **item,
        "kalk_numer": numer,
        "sheet_label": sheet_label,
        "vin": _pick(stan.get("vin"), mai.get("vin"), cs.get("vin"), calc_data.get("vin")) or None,
        "config_code": _pick(
            stan.get("configuration_code"),
            calc_data.get("configuration_code"),
            item.get("vin_or_config"),
        ),
        "offer_number": stan.get("offer_number") or calc_data.get("offer_number"),
        "marketing_name": marketing_name,
        "trim": _pick(
            cs.get("trim_level"), stan.get("trim_level"),
            calc_data.get("trim_level"), calc_data.get("version"),
        ),
        "transmission": _pick(
            cs.get("transmission"), stan.get("gearbox_name"),
            mai.get("transmission"), mai.get("gearbox"),
            calc_data.get("transmission"),
        ),
        "drive": _pick(
            cs.get("drive_type"), stan.get("drive_type"),
            mai.get("drive_type"), calc_data.get("drive_type"),
        ),
        "fuel": _pick(
            cs.get("fuel"), stan.get("fuel"),
            mai.get("fuel"),
            calc_data.get("fuel_type"), calc_data.get("fuel"),
            item.get("powertrain"),
        ),
        "engine_power_hp": _f(cs.get("power_hp")) or _f(stan.get("power_hp")) or _f(calc_data.get("power_hp")),
        "body_style": _pick(
            cs.get("body_style"), stan.get("body_type_name"),
            mai.get("body_type"), calc_data.get("body_style"),
        ),
        "paint_metallic": bool(
            stan.get("is_metalic", cs.get("is_metalic_paint", calc_data.get("is_metalic_paint", False)))
        ),
        "samar_category": _pick(
            stan.get("samar_category"), mai.get("samar_category"),
            calc_data.get("vehicle_class"),
        ),
        "base_price_net": base_price_net,
        "factory_options_total": factory_total,
        "service_options_total": service_total,
        "factory_options_priced": factory,
        "dealer_options_priced": service,
        "standard": standard_strs,
        "contribution": contribution_pln,
        "contribution_pct": contribution_pct,
        "cost_type": stan.get("service_cost_type") or "ASO",
        "cost_breakdown": _format_cost_breakdown(in_rate),
        "tire_display": _format_tire_display(in_rate),
        "in_rate": in_rate,
        # Re-run calculator to get the fin/tech split — vehicle_matrix_cache
        # only stores LacznaStawka, so we recompute from stan_json with the
        # user's applied margin.
        "financial": fin,
        "technical": tech,
        "marginal_per_km": marginal_per_km,
        "overuse_fee": overuse_fee,
        "notes": (item.get("notes") or "").strip(),
        # {package_name_lower: [sub_feature_name, ...]} — used by offer XLS to
        # render expandable rows under each package option. Lower-cased key
        # so the generator can match against factory/dealer option names
        # regardless of original casing.
        "package_contents": _load_package_contents_map(vehicle_id),
    }
    return enriched


def _enrich_item_cached(item: Dict[str, Any]) -> Dict[str, Any]:
    """Cache-aware wrapper around _enrich_item — read-through Redis with
    30min TTL. The expensive part of _enrich_item is the build_matrix()
    recompute inside _compute_matrix_breakdown (~11s per item); caching
    eliminates that cost for items pre-warmed via /preflight while the
    user is still filling client data in the cart drawer."""
    cached = _get_cached_enriched(item)
    if cached is not None:
        return cached
    enriched = _enrich_item(item)
    _set_cached_enriched(item, enriched)
    return enriched


class OfferPreflightRequest(BaseModel):
    items: List[OfferItem]


@router.post("/preflight")
def preflight_offer(request: OfferPreflightRequest):
    """Pre-warm enrichment cache for offer items so generate_offer can skip
    the ~11s-per-item build_matrix recompute. Called by the frontend when:
      - an item is added to the offer cart (single-item warm-up)
      - the offer cart drawer is opened (warm-up all cart items)
    Returns counts only — actual enriched payload stays in Redis."""
    if not request.items:
        return {"warmed": 0, "cached": 0}

    items_dict = [item.model_dump() for item in request.items]
    warmed = 0
    cached_hits = 0
    for it in items_dict:
        if _get_cached_enriched(it) is not None:
            cached_hits += 1
            continue
        try:
            enriched = _enrich_item(it)
            _set_cached_enriched(it, enriched)
            warmed += 1
        except Exception as e:
            logger.warning(
                "preflight enrich failed for item %s: %s",
                it.get("id"), str(e)[:200],
            )
    return {"warmed": warmed, "cached": cached_hits, "total": len(items_dict)}


@router.post("/generate")
def generate_offer(request: OfferGenerateRequest):
    if not request.items:
        raise HTTPException(status_code=400, detail="Koszyk ofertowy jest pusty.")

    try:
        items_dict = [item.model_dump() for item in request.items]
        # Read-through cache — items pre-warmed via /preflight skip the
        # ~11s build_matrix recompute and resolve in <1ms.
        enriched = [_enrich_item_cached(it) for it in items_dict]

        generator = ExcelOfferGenerator()
        excel_bytes = generator.generate_offer(
            client_name=request.client_name,
            client_nip=request.client_nip,
            client_address=request.client_address,
            representative=request.representative,
            items=enriched,
        )

        client_clean = "".join(c if c.isalnum() else "_" for c in request.client_name)
        filename = (
            f"oferta_{int(time.time())}_{client_clean}_{str(uuid.uuid4())[:8]}.xlsx"
        )

        try:
            supabase.storage.from_("offers_excel").upload(
                path=filename,
                file=excel_bytes,
                file_options={
                    "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
            )
            file_url = supabase.storage.from_("offers_excel").get_public_url(filename)
        except Exception as storage_err:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Błąd zapisu w chmurze (bucket 'offers_excel'). "
                    f"Sprawdź czy bucket istnieje w Supabase. Błąd: {storage_err}"
                ),
            )

        supabase.table("ltr_offers").insert(
            [
                {
                    "client_name": request.client_name,
                    "client_nip": request.client_nip,
                    "total_calculations": len(items_dict),
                    "offer_snapshot": items_dict,
                    "excel_file_path": file_url,
                }
            ]
        ).execute()

        return {
            "success": True,
            "url": file_url,
            "message": "Oferta została poprawnie wygenerowana i zarchiwizowana.",
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
