"""
LLM price-deduction (Gemini Flash).

On-demand reconstruction of a vehicle's full price breakdown from PARTIAL
extracted data — used when the deterministic validator
(`pipeline_price_validator.py`) can't close the sum (mixed netto/brutto domains,
missing components, brand-specific non-discountable factory options).

Read-only: this module never writes to the DB. The route `/extract/price-deduce`
returns the suggestion; persistence happens only via `/extract/price-confirm`.

Mirrors `pipeline_price_summary.py` (same client, config, fallback shape).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google.genai import types
from pydantic import BaseModel

from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

logger = logging.getLogger(__name__)

_FLASH_MODEL = "gemini-2.5-flash"


# ── Structured-output schema ──
# Controlled generation guarantees valid JSON (Gemini otherwise emits
# thousands-separated numbers like "167 218.50" → JSONDecodeError). Flat fields
# + one list of flat objects; `bucket` is a plain str (NOT enum) to avoid the
# "too many states" 400 documented in memory `gemini_too_many_states`.
#
# DESIGN: the LLM only READS the source-domain amounts + classifies each line
# (it's reliable at that and at detecting netto/brutto from the document). It
# does NOT compute net/gross/totals — Python does that deterministically in
# `_compute_breakdown`, because the LLM proved inconsistent at applying ÷1.23
# uniformly across every component.
class _DeducedItemSchema(BaseModel):
    field_id: str
    name: str
    amount: float  # as printed in the document, in `source_domain`
    bucket: str
    discountable: bool


class _PriceDeductionSchema(BaseModel):
    source_domain: str  # "netto" | "brutto" — domain of ALL amounts below
    vat_rate: float
    base_amount: float  # catalog base price as printed (source domain)
    rabat_amount: float  # discount as printed (source domain)
    items: list[_DeducedItemSchema]  # factory + service lines (NOT the base)
    reasoning: str
    confidence: float
    source_domain: str

_SYSTEM_PROMPT = (
    "Jesteś audytorem cenowym cenników flotowych. Twoim zadaniem jest ODCZYTAĆ z "
    "dokumentu kwoty cząstkowe i je SKLASYFIKOWAĆ. NIE przeliczaj netto↔brutto — "
    "to zrobi system. Podajesz kwoty DOKŁADNIE tak, jak są wydrukowane.\n\n"
    "KROK 1 — DOMENA (`source_domain`, najczęstsze źródło błędów):\n"
    "Pole `price_domain` i etykiety w `card_summary` BYWAJĄ BŁĘDNE (kwota brutto bywa "
    "opisana jako 'netto'). NIE ufaj im — ustal domenę ARYTMETYCZNIE:\n"
    "  1. Z dokumentu odczytaj cenę KOŃCOWĄ podaną jednocześnie jako 'Kwota netto', "
    "'Kwota VAT' i 'Kwota brutto' (wiersz 'PROPONOWANA CENA KOŃCOWA').\n"
    "  2. Zsumuj pozycje cząstkowe (katalogowa + opcje fabryczne + zabudowa/serwis) i "
    "ODEJMIJ rabat.\n"
    "  3. Jeśli ta suma ≈ BRUTTO ceny końcowej → `source_domain`='brutto'. Jeśli ≈ "
    "NETTO → 'netto'. Etykieta wprost przy cenie katalogowej jest rozstrzygająca.\n"
    "PRZYKŁAD: 167218,50 + 2029,50 + 85497,30 − 49928,16 = 204817,14; dokument ma "
    "'Kwota brutto 204817,14' → `source_domain`='brutto'.\n\n"
    "KROK 2 — KWOTY (wszystkie w domenie `source_domain`, jak wydrukowane):\n"
    "- `base_amount` = cena katalogowa wersji pojazdu (bez opcji).\n"
    "- `rabat_amount` = kwota rabatu jako liczba DODATNIA.\n"
    "- `vat_rate` = stawka VAT jako ułamek (0.23 / 0.08 / 0.0), z relacji "
    "netto/VAT/brutto ceny końcowej.\n\n"
    "KROK 3 — POZYCJE (`items`, BEZ ceny bazowej):\n"
    "Wymień KAŻDĄ płatną pozycję oddzielnie. KAŻDY składnik zabudowy/serwisu OSOBNO "
    "(np. Agregat ORAZ Kontener jako dwie pozycje). Dla każdej: `field_id` (zachowaj z "
    "wejścia, inaczej ''), `name`, `amount` (jak wydrukowana, w source_domain), "
    "`bucket` ('fabryczna' | 'serwisowa'), `discountable` (bool):\n"
    "- serwisowe / zabudowa / załącznik → ZAWSZE discountable=false,\n"
    "- fabryczne → zwykle discountable=true, ALE w niektórych markach część opcji "
    "fabrycznych jest NIERABATOWANA — jeśli kontekst na to wskazuje, ustaw false i "
    "wyjaśnij w `reasoning`.\n"
    "Klasyfikuj pozycje obecne w dokumencie / `paid_options` / `service_equipment`; "
    "nie wymyślaj nowych.\n\n"
    "Zwróć WYŁĄCZNIE JSON: {source_domain, vat_rate, base_amount, rabat_amount, "
    "items:[{field_id,name,amount,bucket,discountable}], reasoning, confidence}. "
    "Kwoty to liczby PLN bez walut/tekstu; brak danej → 0."
)

# Required top-level keys for a well-formed (raw LLM) deduction result.
_REQUIRED_KEYS = (
    "source_domain",
    "base_amount",
    "reasoning",
    "confidence",
)


def deduce_prices(
    card_summary: dict[str, Any],
    known: dict[str, Any] | None = None,
    pdf_bytes: bytes | None = None,
    pdf_mime: str = "application/pdf",
) -> dict[str, Any] | None:
    """Reconstruct the full price breakdown via Gemini Flash.

    Parameters
    ----------
    card_summary:
        The vehicle's ``card_summary`` (current prices, paid_options,
        service_equipment, discount, price_domain).
    known:
        Optional user-supplied partial price anchors (e.g. ``options_net``,
        ``total_gross``) that override / supplement what's in card_summary.
    pdf_bytes:
        Optional raw source PDF. When provided, Gemini reads the document's
        netto/VAT/brutto summary to determine the TRUE domain — the only
        reliable signal, since extraction frequently mislabels it and the
        digital twin keeps only suffix-less numbers. ``None`` → text-only
        deduction (legacy behavior, domain trusted from card_summary).

    Returns
    -------
    dict with the deduction breakdown, or ``None`` when the LLM call fails or
    returns an unusable structure (caller surfaces an error — no silent garbage).
    """
    context = _build_context(card_summary, known or {})

    try:
        return _call_flash(context, pdf_bytes, pdf_mime)
    except Exception:
        logger.warning(
            "[PRICE DEDUCE] Gemini Flash failed — no deduction produced",
            exc_info=True,
        )
        return None


def _build_context(
    card_summary: dict[str, Any],
    known: dict[str, Any],
) -> str:
    """Build a compact JSON context string for Flash."""

    def _opt_view(opt: dict[str, Any]) -> dict[str, Any]:
        return {
            "field_id": opt.get("field_id", ""),
            "name": opt.get("name", ""),
            "price": opt.get("price", ""),
            "net_amount": opt.get("net_amount"),
            "gross_amount": opt.get("gross_amount"),
            "category": opt.get("category", ""),
            "price_type": opt.get("price_type", "unknown"),
        }

    paid_options = [
        _opt_view(o)
        for o in (card_summary.get("paid_options") or [])
        if isinstance(o, dict)
    ]

    service_eq = card_summary.get("service_equipment")
    service_view = None
    if isinstance(service_eq, dict):
        service_view = {
            "field_id": service_eq.get("field_id", ""),
            "name": service_eq.get("name", ""),
            "total_price_net": service_eq.get("total_price_net"),
            "total_price_gross": service_eq.get("total_price_gross"),
            "components": [
                {
                    "name": c.get("name", ""),
                    "price_net": c.get("price_net"),
                    "price_gross": c.get("price_gross"),
                }
                for c in (service_eq.get("components") or [])
                if isinstance(c, dict)
            ],
        }

    context = {
        "brand": card_summary.get("brand", ""),
        "model": card_summary.get("model", ""),
        "price_domain": card_summary.get("_price_domain")
        or card_summary.get("price_domain", "unknown"),
        "current_prices": {
            "base_price": card_summary.get("base_price"),
            "options_price": card_summary.get("options_price"),
            "total_price": card_summary.get("total_price"),
            "base_price_net": card_summary.get("base_price_net"),
            "base_price_gross": card_summary.get("base_price_gross"),
            "options_price_net": card_summary.get("options_price_net"),
            "options_price_gross": card_summary.get("options_price_gross"),
            "total_price_net": card_summary.get("total_price_net"),
            "total_price_gross": card_summary.get("total_price_gross"),
        },
        "discount": card_summary.get("discount"),
        "paid_options": paid_options,
        "service_equipment": service_view,
        # User-supplied partial anchors take priority over extracted values.
        "known_partial_prices": {k: v for k, v in known.items() if v is not None},
    }
    return json.dumps(context, ensure_ascii=False)


def _call_flash(
    context_json: str,
    pdf_bytes: bytes | None = None,
    pdf_mime: str = "application/pdf",
) -> dict[str, Any]:
    """Call Gemini Flash and parse + normalize the JSON response."""
    client = get_gemini_client()

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=4096,
        # Gemini 2.5 Flash enables "thinking" by default, which consumes the
        # output-token budget before the JSON finishes → truncated response →
        # JSONDecodeError. Deterministic structured deduction needs no thinking.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        response_mime_type="application/json",
        response_schema=_PriceDeductionSchema,
        system_instruction=_SYSTEM_PROMPT,
        safety_settings=SAFETY_SETTINGS_PERMISSIVE,
    )

    contents: list[Any] = [types.Part.from_text(text=context_json)]
    if pdf_bytes:
        # Source document → ground-truth domain (netto/VAT/brutto labels).
        contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type=pdf_mime))

    response = client.models.generate_content(
        model=_FLASH_MODEL,
        contents=contents,
        config=config,
    )

    raw_text = getattr(response, "text", "{}") or "{}"
    result = json.loads(raw_text)

    if not isinstance(result, dict) or any(k not in result for k in _REQUIRED_KEYS):
        raise ValueError(f"Unexpected Flash deduction structure: {result}")

    return _compute_breakdown(result)


def _coerce_float(value: Any) -> float:
    """Coerce LLM-returned scalar to float; non-numeric → 0.0."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(" ", "").replace("PLN", "").replace(",", ".").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _compute_breakdown(raw: dict[str, Any]) -> dict[str, Any]:
    """Turn the LLM's source-domain amounts + classification into the full net/gross
    breakdown DETERMINISTICALLY.

    The LLM only reads `source_domain`, `vat_rate`, `base_amount`, `rabat_amount`
    and the classified `items` (amounts as printed). Python applies the VAT
    conversion uniformly — the LLM proved unreliable at doing this consistently
    across every line. Output keys match the legacy contract the panel/confirm
    already consume (base_net, …, options[{net,gross,bucket,discountable}]).
    """
    vat = _coerce_float(raw.get("vat_rate"))
    if vat <= 0 or vat >= 1:
        vat = 0.23

    domain = str(raw.get("source_domain", "")).lower()
    if domain not in ("netto", "brutto"):
        domain = "netto"

    def split(amount: float) -> tuple[float, float]:
        """(net, gross) for an amount printed in `domain`."""
        if domain == "brutto":
            return round(amount / (1 + vat), 2), round(amount, 2)
        return round(amount, 2), round(amount * (1 + vat), 2)

    base_net, base_gross = split(_coerce_float(raw.get("base_amount")))
    rabat_net, _rabat_gross = split(_coerce_float(raw.get("rabat_amount")))

    disc_net = disc_gross = nondisc_net = nondisc_gross = svc_net = svc_gross = 0.0
    options: list[dict[str, Any]] = []
    for item in raw.get("items") or []:
        if not isinstance(item, dict):
            continue
        bucket = str(item.get("bucket", "fabryczna")).lower()
        if bucket not in ("fabryczna", "serwisowa", "katalogowa"):
            bucket = "fabryczna"
        if bucket == "katalogowa":
            continue  # base is authoritative via base_amount — never double-count
        net, gross = split(_coerce_float(item.get("amount")))
        discountable = bool(item.get("discountable", bucket != "serwisowa"))
        if bucket == "serwisowa":
            discountable = False
            svc_net += net
            svc_gross += gross
        elif discountable:
            disc_net += net
            disc_gross += gross
        else:
            nondisc_net += net
            nondisc_gross += gross
        options.append(
            {
                "field_id": str(item.get("field_id", "")),
                "name": str(item.get("name", "")),
                "net": net,
                "gross": gross,
                "bucket": bucket,
                "discountable": discountable,
            }
        )

    total_net = round(base_net + disc_net + nondisc_net + svc_net - rabat_net, 2)
    total_gross = round(total_net * (1 + vat), 2)

    confidence = min(1.0, max(0.0, _coerce_float(raw.get("confidence"))))
    reasoning = raw.get("reasoning") if isinstance(raw.get("reasoning"), str) else ""

    return {
        "source_domain": domain,
        "vat_rate": vat,
        "base_net": base_net,
        "base_gross": base_gross,
        "discountable_options_net": round(disc_net, 2),
        "discountable_options_gross": round(disc_gross, 2),
        "non_discountable_options_net": round(nondisc_net, 2),
        "non_discountable_options_gross": round(nondisc_gross, 2),
        "service_net": round(svc_net, 2),
        "service_gross": round(svc_gross, 2),
        "total_net": total_net,
        "total_gross": total_gross,
        "rabat_pln": rabat_net,
        "options": options,
        "deduced_fields": [],
        "reasoning": reasoning,
        "confidence": confidence,
    }
