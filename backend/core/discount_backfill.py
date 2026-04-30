"""Deterministyczny backfill `card_summary.discount` dla istniejacych wpisow.

Dziala BEZ wywolan LLM - uzywa:
1. Regexow do znalezienia literalnej linii "RABAT N PLN" w `digital_twin` markdown.
2. Slownika `_DEALER_EXTRA_KEYWORDS` do wykrycia zabudow w `paid_options`.
3. Triangulacji `discountable + non_discountable - rabat ~ total` dla weryfikacji.

Zwraca obiekt `DiscountBreakdown` (lub None gdy nie da sie wnioskowac).
Confidence:
  - 0.95 - literalny RABAT znaleziony i triangulacja zgadza sie
  - 0.85 - literalny RABAT znaleziony, ale triangulacja bledna (LLM mogl pominac opcje)
  - 0.55 - wyliczone posrednio z roznicy total - (base + options)
  - 0.00 - nie ma rabatu ani sygnalu do wyliczenia
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from core.extractor_models import DiscountBreakdown, DiscountExtractionMethod
from core.pipeline_price_validator import _DEALER_EXTRA_KEYWORDS
from core.price_parser import parse_price_string

logger = logging.getLogger(__name__)

# Helper: zbuduj wzorzec dla slowa kluczowego pozwalajac na opcjonalne spacje
# miedzy literami (Ford PDFs maja "R A B A T" z osobnymi literami) ORAZ
# wymagajac WORD BOUNDARY na koncu, by wykluczyc formy odmienione typu RABATEM/RABATU
# (gdy w "Z RABATEM" liczba to cena, nie rabat).
def _spacy_keyword(word: str) -> str:
    """Build pattern: each char optionally followed by whitespace, end with \\b."""
    return r"\s*".join(re.escape(c) for c in word) + r"\b"


_RABAT_KEYWORDS = ["RABAT", "Discount", "Znizka", "Upust", "Bonus", "Korzysc"]
_RABAT_KEYWORD_PATTERN = "(?:" + "|".join(_spacy_keyword(w) for w in _RABAT_KEYWORDS) + ")"

# Numerek po kluczowym slowie - dopuszcza spacje miedzy cyframi (Ford "1 2 8  9 0 0")
# oraz konczy na ',-' / ', -' / 'PLN' / 'zl'.
_NUM_TAIL = (
    r"\s*[:\-]?\s*"
    r"([\d][\d\s\.]+?)"
    r"\s*(?:,\s*-|PLN|zl|zlotych|$|\n)"
)

_RABAT_REGEX = re.compile(
    _RABAT_KEYWORD_PATTERN
    + r"(?:\s+(?:klienta|dealerski|specjalny|bazowy|laczny|total|customer|special))?"
    + _NUM_TAIL,
    re.IGNORECASE,
)

# Procent: "Rabat 24%", "Upust 12,5%". Slowa kluczowe te same.
_RABAT_PCT_REGEX = re.compile(
    "(?:" + "|".join(_spacy_keyword(w) for w in ["RABAT", "Discount", "Upust"]) + ")"
    + r"\s*[:\-]?\s*(\d{1,2}(?:[,.]\d{1,2})?)\s*%",
    re.IGNORECASE,
)


def _parse_pl_number(s: str) -> Optional[float]:
    """Parsuj polski/europejski format liczby: '42 317,50' -> 42317.5"""
    cleaned = s.replace(" ", "").replace(" ", "").replace(".", "")
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _flatten_text(node: Any, parts: list[str]) -> None:
    """Rekurencyjnie wyciagnij stringi z dowolnej JSON-struktury."""
    if isinstance(node, str):
        parts.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            _flatten_text(v, parts)
    elif isinstance(node, list):
        for v in node:
            _flatten_text(v, parts)


def _extract_text_corpus(digital_twin: Any) -> str:
    """Splaszcz caly digital_twin do jednego stringa do regex-search."""
    parts: list[str] = []
    _flatten_text(digital_twin, parts)
    return "\n".join(parts)


def _normalize_for_regex(text: str) -> str:
    """Usun polskie znaki diakrytyczne aby regex bez IGNORECASE/UNICODE
    laczyl 'Znizka' i 'Zniżka', 'Korzysc' i 'Korzyść' itp.
    """
    table = str.maketrans(
        "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
        "acelnoszzACELNOSZZ",
    )
    return text.translate(table)


def _find_explicit_rabat_pln(corpus: str) -> Optional[float]:
    """Znajdz literalna kwote rabatu w korpusie. Zwraca najwieksza znaleziona
    (bo dokumenty potrafia wymieniac 'rabat klienta' i 'rabat dealera' osobno;
    chcemy laczny / najwyzszy)."""
    normalized = _normalize_for_regex(corpus)
    candidates: list[float] = []
    for match in _RABAT_REGEX.finditer(normalized):
        raw = match.group(1)
        val = _parse_pl_number(raw)
        # Filtr: rabat musi byc sensowny (>= 100 PLN, <= 1M PLN)
        if val is not None and 100 <= val <= 1_000_000:
            candidates.append(val)
    if not candidates:
        return None
    return max(candidates)


def _find_explicit_rabat_pct(corpus: str) -> Optional[float]:
    """Znajdz literalny procent rabatu."""
    normalized = _normalize_for_regex(corpus)
    for match in _RABAT_PCT_REGEX.finditer(normalized):
        raw = match.group(1)
        val = _parse_pl_number(raw)
        if val is not None and 0.5 <= val <= 60.0:
            return val
    return None


def _sum_dealer_extras(paid_options: list[Any]) -> tuple[float, list[str]]:
    """Zsumuj wartosci pozycji oznaczonych jako zabudowa/dealer extras."""
    if not paid_options:
        return 0.0, []
    total = 0.0
    names: list[str] = []
    for opt in paid_options:
        if not isinstance(opt, dict):
            continue
        haystack = f"{opt.get('name', '')} {opt.get('category', '')}".lower()
        if any(kw in haystack for kw in _DEALER_EXTRA_KEYWORDS):
            parsed = parse_price_string(opt.get("price", ""))
            if parsed:
                total += parsed.value
                names.append(opt.get("name", "?"))
    return total, names


def _sum_factory_options(paid_options: list[Any]) -> float:
    """Zsumuj fabryczne opcje (bez slow-kluczy zabudowy)."""
    if not paid_options:
        return 0.0
    total = 0.0
    for opt in paid_options:
        if not isinstance(opt, dict):
            continue
        haystack = f"{opt.get('name', '')} {opt.get('category', '')}".lower()
        if any(kw in haystack for kw in _DEALER_EXTRA_KEYWORDS):
            continue
        parsed = parse_price_string(opt.get("price", ""))
        if parsed:
            total += parsed.value
    return total


def derive_discount_breakdown(
    card_summary: dict[str, Any],
    digital_twin: Any = None,
) -> Optional[DiscountBreakdown]:
    """Zbuduj DiscountBreakdown deterministycznie z istniejacego card_summary.

    Strategia:
    1. Sprobuj znalezc literalny RABAT w digital_twin (regex).
    2. Wykryj zabudowy w paid_options.
    3. Zbuduj breakdown, triangulacja, confidence.

    UWAGA: Funkcja jest "pure" - zawsze probuje wyliczyc nowy breakdown niezaleznie
    czy `card_summary.discount` juz istnieje. Gating idempotencji robi
    `apply_backfill_to_card_summary` na podstawie flagi `overwrite_existing`.

    Zwraca None gdy nie da sie sensownie wnioskowac.
    """
    base = parse_price_string(card_summary.get("base_price"))
    options_summary = parse_price_string(card_summary.get("options_price"))
    total = parse_price_string(card_summary.get("total_price"))

    paid_options = card_summary.get("paid_options", []) or []

    dealer_extras_sum, dealer_names = _sum_dealer_extras(paid_options)
    factory_opts_sum = _sum_factory_options(paid_options)

    if base is None:
        return None

    if factory_opts_sum > 0:
        discountable_base = base.value + factory_opts_sum
    elif options_summary is not None:
        # options_summary moze zawierac zabudowy -> odejmij
        discountable_base = base.value + max(0.0, options_summary.value - dealer_extras_sum)
    else:
        discountable_base = base.value

    non_discountable = dealer_extras_sum

    corpus = _extract_text_corpus(digital_twin) if digital_twin else ""
    explicit_pln = _find_explicit_rabat_pln(corpus) if corpus else None
    explicit_pct = _find_explicit_rabat_pct(corpus) if corpus and not explicit_pln else None

    audit_notes: list[str] = []

    if explicit_pln:
        audit_notes.append(f"Backfill: znaleziono literalny RABAT {explicit_pln:.0f} PLN w dokumencie.")
    if dealer_extras_sum > 0:
        audit_notes.append(
            f"Backfill: wykryto dealer extras suma {dealer_extras_sum:.0f} PLN ({', '.join(dealer_names)})."
        )

    method = DiscountExtractionMethod.NONE
    confidence = 0.0
    final_pln: Optional[float] = explicit_pln
    final_pct: Optional[float] = explicit_pct

    if explicit_pln:
        method = DiscountExtractionMethod.EXPLICIT_AMOUNT
        if total is not None:
            expected_total = discountable_base - explicit_pln + non_discountable
            triang_diff = abs(expected_total - total.value)
            if triang_diff <= 1.0:
                confidence = 0.95
                audit_notes.append(
                    f"Triangulacja OK: {discountable_base:.0f} + {non_discountable:.0f} "
                    f"- {explicit_pln:.0f} = {expected_total:.0f} ~ total {total.value:.0f}."
                )
            else:
                confidence = 0.85
                audit_notes.append(
                    f"Triangulacja niezgodna (delta {triang_diff:.0f} PLN) - mozliwa pominieta opcja."
                )
        else:
            confidence = 0.7

    elif explicit_pct:
        method = DiscountExtractionMethod.EXPLICIT_PERCENTAGE
        confidence = 0.85
        if discountable_base > 0:
            final_pln = round(discountable_base * explicit_pct / 100.0, 2)
            audit_notes.append(
                f"Backfill: rabat {explicit_pct}% x {discountable_base:.0f} = {final_pln:.0f} PLN."
            )

    elif total is not None:
        implied = discountable_base - (total.value - non_discountable)
        if implied > 100:
            method = DiscountExtractionMethod.COMPUTED_FROM_TOTAL
            confidence = 0.55
            final_pln = round(implied, 2)
            audit_notes.append(
                f"Backfill: rabat wyliczony posrednio = {discountable_base:.0f} "
                f"- ({total.value:.0f} - {non_discountable:.0f}) = {implied:.0f} PLN."
            )
        else:
            return None
    else:
        return None

    computed_pct: Optional[float] = None
    if final_pln and discountable_base > 0:
        computed_pct = round((final_pln / discountable_base) * 100, 2)

    return DiscountBreakdown(
        explicit_rabat_pln=final_pln,
        explicit_rabat_pct=final_pct,
        discountable_base_net=round(discountable_base, 2),
        non_discountable_total_net=round(non_discountable, 2),
        computed_pct=computed_pct,
        extraction_method=method,
        confidence=confidence,
        audit_notes=audit_notes,
    )


def apply_backfill_to_card_summary(
    card_summary: dict[str, Any],
    digital_twin: Any = None,
    overwrite_existing: bool = False,
) -> bool:
    """Wstaw `discount` w `card_summary` jesli da sie wnioskowac.

    Zwraca True jesli cos zmieniono. Modyfikuje card_summary in-place.
    """
    if not overwrite_existing and isinstance(card_summary.get("discount"), dict):
        existing = card_summary["discount"]
        if existing.get("extraction_method") in ("explicit_amount", "explicit_percentage"):
            return False

    breakdown = derive_discount_breakdown(card_summary, digital_twin)
    if breakdown is None:
        return False

    card_summary["discount"] = json.loads(breakdown.model_dump_json())

    # Zsynchronizuj legacy pola dla wstecznej kompatybilnosci
    if breakdown.computed_pct is not None and not card_summary.get("offer_discount_pct"):
        card_summary["offer_discount_pct"] = str(breakdown.computed_pct)
    if breakdown.explicit_rabat_pln is not None and not card_summary.get("offer_discount_pln"):
        card_summary["offer_discount_pln"] = f"{int(breakdown.explicit_rabat_pln)} PLN"

    return True
