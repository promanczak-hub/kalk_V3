"""Pure helpers shared across the scoring_search router modules.

Extracted from `scoring_search_routes.py` (refactor 2026-05-19). These
functions don't decorate endpoints — they're plain utilities for parsing,
normalising, caching, and snapshotting that the endpoint modules import.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

from core.body_type_matcher import normalize_body_style_for_display
from core.database import get_admin_client, supabase
from core.models_scoring_search import (
    AvailableFiltersRequest,
    OptionLineItem,
    SimilarityReasons,
    SimilarVehicleMatch,
)
from core.redis_cache import _get_client

logger = logging.getLogger(__name__)

VAT_RATE = 1.23

# ── TTL constants (used by both helper consumers and endpoint modules) ────────
TTL_INITIAL_DATA = 3600  # 1 hour  — changes only when vehicles are added
TTL_FILTERS = 300        # 5 min   — depends on vehicle DB state
TTL_SEARCH = 120         # 2 min   — user results; short enough to stay fresh


# ── Normalisation helpers ─────────────────────────────────────────────────────


def normalize_transmission(raw: str | None) -> str | None:
    """Collapse marketing transmission names to one of two clean values:
    "Automatyczna" or "Manualna". Returns None for empty/unrecognised input.
    Used so the search filter chip shows just two options instead of dozens.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    # Order matters: "automat" before "manual" since some strings contain both
    if (
        "automat" in s or "s-tronic" in s or "dsg" in s
        or "tiptronic" in s or "cvt" in s
    ):
        return "Automatyczna"
    if "manual" in s:
        return "Manualna"
    return None


def normalize_drive_type(raw: str | None) -> str | None:
    """Collapse drive_type variants to the AI mapper's canonical enum:
    FWD / RWD / AWD. Returns None for ambiguous values like "2X4".
    """
    if not raw:
        return None
    s = str(raw).strip().upper()
    if not s:
        return None
    if (
        s in {"AWD", "4WD", "4X4", "4MATIC", "QUATTRO", "XDRIVE", "4MOTION", "ALL4"}
        or "AWD" in s or "4X4" in s or "4WD" in s
        or "WSZYSTKIE KOŁA" in s or "4MOTION" in s or "QUATTRO" in s
    ):
        return "AWD"
    if s == "FWD" or "FWD" in s or "PRZEDNI" in s or "FRONT" in s:
        return "FWD"
    if s == "RWD" or "RWD" in s or "TYLN" in s or "REAR" in s:
        return "RWD"
    return None


# ── Redis helpers (Redis-down tolerant) ───────────────────────────────────────


def redis_get(key: str) -> Any | None:
    """Safe Redis GET — returns None on any error."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.debug("Redis GET error [%s]: %s", key, exc)
        return None


def redis_set(key: str, value: Any, ttl: int) -> None:
    """Safe Redis SETEX — silently skips on any error."""
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("Redis SET error [%s]: %s", key, exc)


def params_hash(payload: str) -> str:
    return hashlib.md5(payload.encode(), usedforsecurity=False).hexdigest()


# ── Coercion helpers ─────────────────────────────────────────────────────────


def coerce_float(val: Any) -> float | None:
    """Best-effort parse of a stan_json scalar into float. Returns None for
    empty/None/non-numeric so missing toggle values don't get pinned to 0."""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def coerce_bool(val: Any) -> bool | None:
    """Parse a stan_json toggle value into bool. Returns None only when the
    field is missing or unparseable, so the UI can distinguish 'set to off'
    from 'unknown'."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    s = str(val).strip().lower()
    if s in {"true", "1", "yes", "tak", "t"}:
        return True
    if s in {"false", "0", "no", "nie", "f"}:
        return False
    return None


# ── Supabase retry (transient httpx error tolerance) ─────────────────────────


def supabase_execute_with_retry(query_obj: Any, max_retries: int = 3) -> Any:
    """Execute a Supabase query, retrying on known transient transport errors."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return query_obj.execute()
        except Exception as exc:
            last_exc = exc
            err_str = str(exc).lower()
            if (
                "server disconnected" in err_str
                or "unreachable" in err_str
                or "timeout" in err_str
                or "connection" in err_str
                or "ssl" in err_str
                or "eof" in err_str
                or "protocol" in err_str
            ):
                logger.warning(
                    "Supabase connection issue (attempt %d/%d): %s",
                    attempt + 1, max_retries, exc,
                )
                time.sleep(0.5 * (2**attempt))
                continue
            raise
    assert last_exc is not None
    raise last_exc


# ── Snapshot / kalkulacja toggle params ──────────────────────────────────────


def fetch_kalkulacja_snapshot_params(
    kalk_ids: list[Any],
) -> dict[str, dict[str, Any]]:
    """Batch-fetch the pricing-toggle + financing-knob snapshot for a list of
    kalkulacja_ids. Reads `ltr_kalkulacje.stan_json` and projects the subset
    the UI needs to render next to a price (rabat, marża bankowa, WIBOR,
    opony / ubezpieczenie / auto zastępcze / serwis flags).
    Falls back to ControlCenterSettings defaults for missing WIBOR / margin.
    Silent-fails to an empty dict on RPC error.
    """
    out: dict[str, dict[str, Any]] = {}
    ids = sorted({str(x) for x in kalk_ids if x})
    if not ids:
        return out

    fb_wibor: float | None = None
    fb_margin: float | None = None
    try:
        from core.control_center import fetch_control_center_row

        cc_row = fetch_control_center_row(
            client=get_admin_client(),
            keys=["default_wibor", "bank_spread"],
        )
        fb_wibor = coerce_float(cc_row.get("default_wibor"))
        fb_margin = coerce_float(cc_row.get("bank_spread"))
    except Exception:
        logger.exception("control_center fallback fetch failed (non-fatal)")

    try:
        resp = (
            supabase.table("ltr_kalkulacje")
            .select("id, stan_json")
            .in_("id", ids)
            .execute()
        )
    except Exception:
        logger.exception("ltr_kalkulacje snapshot fetch failed for ids=%s", ids[:5])
        return out

    for row in resp.data or []:
        kid = str(row.get("id") or "")
        stan = row.get("stan_json") or {}
        if not isinstance(stan, dict):
            continue
        bank_margin = coerce_float(stan.get("margin_pct"))
        wibor = coerce_float(stan.get("wibor_pct"))
        out[kid] = {
            "discount_pct": coerce_float(stan.get("discount_pct")),
            "bank_margin_pct": bank_margin if bank_margin is not None else fb_margin,
            "wibor_pct": wibor if wibor is not None else fb_wibor,
            "tires_included": coerce_bool(stan.get("z_oponami")),
            "tire_buyback": coerce_bool(stan.get("odkup_opon_enabled")),
            "insurance_included": coerce_bool(stan.get("express_pays_insurance")),
            "replacement_car": coerce_bool(stan.get("replacement_car_enabled")),
            "service_included": coerce_bool(stan.get("include_servicing")),
        }
    return out


def attach_kalkulacja_snapshot_to_matches(matches: list[SimilarVehicleMatch]) -> None:
    """Mutate-in-place: enrich SimilarVehicleMatch list with snapshot fields.
    No-op for matches without a kalkulacja_id; preserves explicitly-populated
    snapshot fields (only fills None values).
    """
    if not matches:
        return
    snapshot_by_kid = fetch_kalkulacja_snapshot_params(
        [m.kalkulacja_id for m in matches if m.kalkulacja_id]
    )
    if not snapshot_by_kid:
        return
    for m in matches:
        if not m.kalkulacja_id:
            continue
        snap = snapshot_by_kid.get(str(m.kalkulacja_id))
        if not snap:
            continue
        for k, v in snap.items():
            if getattr(m, k, None) is None:
                setattr(m, k, v)


# ── Price parsing ────────────────────────────────────────────────────────────


def resolve_price_domain(price_str: str, domain_hint: str | None) -> str | None:
    """Inline `netto`/`brutto` suffix in the price string beats the domain hint."""
    s = price_str.lower()
    if "netto" in s:
        return "netto"
    if "brutto" in s:
        return "brutto"
    return domain_hint


def parse_price_numeric(price_str: str) -> float | None:
    """Strip suffix tokens + whitespace and parse the numeric portion."""
    cleaned = (
        price_str.lower()
        .replace("netto", "")
        .replace("brutto", "")
        .replace(" ", "")
        .replace("\xa0", "")
        .replace("pln", "")
        .replace("zł", "")
    )
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")

    cleaned = "".join(c for c in cleaned if c.isdigit() or c == ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_price_to_net(price_str: str | None, domain: str | None) -> float | None:
    """Convert raw price string to a netto float."""
    if not price_str:
        return None
    s = str(price_str)
    val = parse_price_numeric(s)
    if val is None:
        return None
    effective = resolve_price_domain(s, domain)
    if effective == "netto":
        return round(val, 2)
    return round(val / VAT_RATE, 2)


def parse_price_pair(
    price_str: str | None, domain: str | None
) -> tuple[float | None, float | None]:
    """Return (net, gross). Whichever side is original wins; the other is
    derived once via VAT_RATE — avoids lossy net→gross multiplication on FE.
    """
    if not price_str:
        return None, None
    s = str(price_str)
    val = parse_price_numeric(s)
    if val is None:
        return None, None
    effective = resolve_price_domain(s, domain)
    if effective == "netto":
        return round(val, 2), round(val * VAT_RATE, 2)
    return round(val / VAT_RATE, 2), round(val, 2)


# ── Option line item extraction ──────────────────────────────────────────────


def extract_option_line_items(
    card_summary: dict[str, Any] | None,
) -> tuple[list[OptionLineItem], list[OptionLineItem]]:
    """Split paid_options + service_equipment into factory/service line lists.

    Each item carries BOTH price_net and price_gross — derived once at parse
    time. To avoid double-counting the service-equipment aggregate (extractor
    ships it twice as a paid_option + structured block), we prefer the
    detailed `components[]` and drop the matching paid_options aggregate.
    """
    if not card_summary:
        return [], []
    domain = card_summary.get("price_domain")
    factory: list[OptionLineItem] = []
    service: list[OptionLineItem] = []
    for opt in card_summary.get("paid_options") or []:
        if not isinstance(opt, dict):
            continue
        name = (opt.get("name") or "").strip()
        if not name:
            continue
        cat = (opt.get("category") or "").lower()
        price_net, price_gross = parse_price_pair(
            opt.get("price"), opt.get("price_type") or domain
        )
        item = OptionLineItem(
            name=name, price_net=price_net,
            price_gross=price_gross, category=opt.get("category"),
        )
        if "fabryczn" in cat:
            factory.append(item)
        elif "serwis" in cat or "akcesori" in cat or "zabudowa" in cat:
            service.append(item)

    svc_eq = card_summary.get("service_equipment") or {}
    agg_name = (svc_eq.get("name") or "").strip().lower()
    components = svc_eq.get("components") or []

    if agg_name and components:
        service = [s for s in service if (s.name or "").strip().lower() != agg_name]
        for c in components:
            if not isinstance(c, dict):
                continue
            cname = (c.get("name") or "").strip()
            if not cname:
                continue
            net, gross = parse_price_pair(
                c.get("price_net") or c.get("price_gross") or c.get("price"),
                "netto" if c.get("price_net") else None,
            )
            if net is None and gross is None:
                continue
            service.append(OptionLineItem(
                name=cname, price_net=net, price_gross=gross,
                category=svc_eq.get("name") or "Pakiet serwisowy",
            ))
    elif svc_eq.get("total_price_net") and not any(
        (s.name or "").strip().lower() == agg_name for s in service if agg_name
    ):
        net, gross = parse_price_pair(svc_eq.get("total_price_net"), "netto")
        if net is not None or gross is not None:
            service.append(OptionLineItem(
                name=svc_eq.get("name") or "Pakiet serwisowy",
                price_net=net, price_gross=gross, category="Serwisowa",
            ))

    return factory, service


# ── Similar vehicle row builder ──────────────────────────────────────────────


def build_similar_vehicle_match(row: dict[str, Any]) -> SimilarVehicleMatch:  # noqa: PLR0915 — RPC row → model mapping; splitting obscures the projection
    """Build a SimilarVehicleMatch from a raw RPC row dict.

    Handles both single and batch RPC variants (some field names differ),
    and maps the similarity_reasons JSONB payload to the SimilarityReasons model.
    """
    raw_reasons = row.get("similarity_reasons")
    similarity_reasons: SimilarityReasons | None = None
    price_domain = row.get("price_domain", "brutto")

    base_price_val: Optional[float] = None
    base_price_gross_val: Optional[float] = None
    if isinstance(raw_reasons, dict):
        base_price_raw = raw_reasons.get("base_price")
        if base_price_raw is not None:
            base_price_val, base_price_gross_val = parse_price_pair(
                str(base_price_raw), price_domain
            )

        def _opt_float(key: str) -> Optional[float]:
            v = raw_reasons.get(key)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        def _opt_int(key: str) -> Optional[int]:
            v = raw_reasons.get(key)
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        similarity_reasons = SimilarityReasons(
            samar_match=bool(raw_reasons.get("samar_match", False)),
            body_match=bool(raw_reasons.get("body_match", False)),
            fuel_match=bool(raw_reasons.get("fuel_match", False)),
            drive_match=bool(raw_reasons.get("drive_match", False)),
            equipment_match=bool(raw_reasons.get("equipment_match", False)),
            is_same_brand=bool(raw_reasons.get("is_same_brand", False)),
            equipment_similarity_pct=_opt_float("equipment_similarity_pct"),
            price_pct_diff=_opt_float("price_pct_diff"),
            is_cheaper=raw_reasons.get("is_cheaper"),
            samar_category=raw_reasons.get("samar_category"),
            body_style=raw_reasons.get("body_style"),
            base_price=base_price_val,
            paid_options=raw_reasons.get("paid_options"),
            is_fallback_match=bool(raw_reasons.get("is_fallback_match", False)),
            discount_pct=_opt_float("discount_pct"),
            final_price_net=_opt_float("final_price_net"),
            final_price_pct_diff=_opt_float("final_price_pct_diff"),
            discount_pct_diff=_opt_float("discount_pct_diff"),
            payload_kg=_opt_int("payload_kg"),
            cargo_volume_m3=_opt_float("cargo_volume_m3"),
            body_type=raw_reasons.get("body_type"),
            setup_match=raw_reasons.get("setup_match"),
            source_tire_class=raw_reasons.get("source_tire_class"),
            source_service_type=raw_reasons.get("source_service_type"),
            matched_duration_months=_opt_int("matched_duration_months"),
            matched_annual_mileage=_opt_int("matched_annual_mileage"),
        )

    factory_options: list[OptionLineItem] = []
    service_options: list[OptionLineItem] = []
    factory_total_net: Optional[float] = None
    factory_total_gross: Optional[float] = None
    service_total_net: Optional[float] = None
    service_total_gross: Optional[float] = None
    total_price_net: Optional[float] = None
    total_price_gross: Optional[float] = None
    if isinstance(raw_reasons, dict) and (
        raw_reasons.get("paid_options") is not None
        or raw_reasons.get("service_equipment") is not None
    ):
        synthetic_summary = {
            "paid_options": raw_reasons.get("paid_options") or [],
            "service_equipment": raw_reasons.get("service_equipment"),
            "price_domain": raw_reasons.get("price_domain") or price_domain,
        }
        factory_options, service_options = extract_option_line_items(synthetic_summary)
        if factory_options:
            factory_total_net = round(
                sum(o.price_net for o in factory_options if o.price_net is not None), 2
            )
            factory_total_gross = round(
                sum(o.price_gross for o in factory_options if o.price_gross is not None), 2
            ) or None
        if service_options:
            service_total_net = round(
                sum(o.price_net for o in service_options if o.price_net is not None), 2
            )
            service_total_gross = round(
                sum(o.price_gross for o in service_options if o.price_gross is not None), 2
            ) or None
    if base_price_val is not None:
        total_price_net = round(
            base_price_val + (factory_total_net or 0) + (service_total_net or 0), 2
        )
    if base_price_gross_val is not None:
        total_price_gross = round(
            base_price_gross_val + (factory_total_gross or 0) + (service_total_gross or 0), 2
        )

    raw_price = row.get("best_monthly_price") or row.get("min_price")
    return SimilarVehicleMatch(
        vehicle_id=str(row.get("vehicle_id") or row.get("v_id", "")),
        brand=row.get("brand"),
        model=row.get("model"),
        version=row.get("version"),
        samar_category=str(row.get("samar_category") or row.get("v_samar") or "N/A"),
        fuel=str(row.get("fuel") or row.get("v_fuel") or "N/A"),
        transmission=str(row.get("transmission") or row.get("v_transmission") or "N/A"),
        best_monthly_price=float(raw_price) if raw_price is not None else None,
        image_url=str(row.get("image_url") or row.get("v_image") or ""),
        similarity_score_pct=float(row.get("similarity_score_pct") or 0),
        power_hp=int(row.get("power_hp") or 0) or None,
        engine_label=row.get("engine_label") or None,
        body_style=str(normalize_body_style_for_display(row.get("body_style")) or "N/A"),
        vehicle_class=str(row.get("vehicle_class") or "N/A"),
        drive_type=str(row.get("drive_type") or "N/A"),
        price_domain=price_domain,
        similarity_reasons=similarity_reasons,
        kalkulacja_id=row.get("kalkulacja_id"),
        base_price_net=base_price_val,
        base_price_gross=base_price_gross_val,
        factory_options_price_net=factory_total_net,
        factory_options_price_gross=factory_total_gross,
        service_options_price_net=service_total_net,
        service_options_price_gross=service_total_gross,
        factory_options=factory_options,
        service_options=service_options,
        total_price_net=total_price_net,
        total_price_gross=total_price_gross,
    )


# ── Body style + candidate ID resolution ─────────────────────────────────────


BODY_TYPE_FIELDS = (
    ("card_summary", "body_style"),
    ("mapped_ai_data", "body_style"),
    ("__root__", "nadwozie"),
    ("__root__", "samar_body_type"),
    ("__root__", "samar_body_style"),
    ("__root__", "rodzaj_zabudowy"),
)

PRESENT_STATUSES = (
    "present_confirmed_primary",
    "present_confirmed_secondary",
    "present_inferred",
)


def vehicle_body_styles(synthesis_data: dict[str, Any] | None) -> list[str]:
    """Pull every plausible body-style label out of a vehicle's synthesis_data."""
    if not isinstance(synthesis_data, dict):
        return []
    out: list[str] = []
    for parent_key, leaf in BODY_TYPE_FIELDS:
        parent = synthesis_data if parent_key == "__root__" else synthesis_data.get(parent_key)
        if not isinstance(parent, dict):
            continue
        v = parent.get(leaf)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    return out


def resolve_candidate_vehicle_ids(request: AvailableFiltersRequest) -> list[str]:
    """Find vehicle_synthesis IDs matching the brand/model/body_type filter."""
    sb = supabase
    q = (
        sb.table("vehicle_synthesis")
        .select("id, brand, model, synthesis_data")
        .eq("verification_status", "completed")
    )
    if request.brands:
        q = q.in_("brand", request.brands)
    if request.models:
        q = q.in_("model", request.models)
    resp = supabase_execute_with_retry(q)
    rows = resp.data or []

    if not request.body_types:
        return [str(r["id"]) for r in rows if r.get("id")]

    wanted = {bt.upper() for bt in request.body_types}
    out: list[str] = []
    for r in rows:
        styles = vehicle_body_styles(r.get("synthesis_data"))
        if any(any(w in s.upper() for s in styles) for w in wanted):
            out.append(str(r["id"]))
    return out


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile (no scipy dep). 0 ≤ pct ≤ 1."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def parse_numeric(val: Any) -> float | None:
    """Permissive parse for filter values that may arrive as float/int/str."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip())
    except (TypeError, ValueError):
        return None
