"""Canonical-ID computation + potential-duplicate flagging.

CRITICAL DESIGN RULE: this module DETECTS potential duplicates and adds
`canonical_id` + `duplicate_of` markers. It does NOT merge, drop or rename
items. The HITL UI gives the user 100% control over disambiguation
(see frontend/src/VertexExtractor/HITLBuckets.tsx and
backend/api/extract_hitl_routes.py::move_item).

Replaces the auto-drop logic previously living in
`scoring_search_helpers.extract_option_line_items` (lines 376-393).
"""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from typing import Any

# Vendor codes: 2-3 uppercase letters immediately followed by 2+ digits
# (e.g. "ZAB123", "PR456"). Conservative — won't strip "BMW Series 3".
_VENDOR_CODE_RE = re.compile(r"\b[A-Z]{2,3}\d{2,}\b")

# Currency / price-domain tokens to strip after lowercasing. Note: we strip
# only standalone tokens or those at word boundaries.
_CURRENCY_TOKENS = ("pln", "zł", "zl", "eur", "usd", "netto", "brutto")

# Bracket characters → treat as whitespace so contents don't fuse with name.
_BRACKETS_RE = re.compile(r"[\(\)\[\]\{\}]")

# Characters NFKD doesn't decompose — provide explicit fold table.
# Polish "Ł/ł" is an independent codepoint (U+0141 / U+0142), not L + combining
# mark; German "ß" likewise. Other Polish letters (ą, ę, ć, ń, ó, ś, ź, ż) DO
# decompose via NFKD, so they're handled by the unicodedata.combining filter.
_PRE_FOLD: dict[str, str] = {
    "Ł": "L", "ł": "l",
    "ß": "ss", "ẞ": "SS",
    "Ø": "O", "ø": "o",
    "Æ": "AE", "æ": "ae",
    "Œ": "OE", "œ": "oe",
    "Đ": "D", "đ": "d",
}


def normalize_name(raw: str) -> str:
    """Normalize an item name for canonical-id hashing.

    Pipeline:
    1. Strip vendor codes (pre-lowercase so the regex catches uppercase).
    2. Replace bracket chars with whitespace.
    3. Unicode-fold diacritics (NFKD + strip combining marks) + German
       umlauts (ß → ss) and ligatures.
    4. Lowercase.
    5. Strip currency/domain tokens (PLN, zł, netto, brutto, …).
    6. Strip numeric tokens that look like prices (>= 3 digits) — they live
       in `net_amount`, not the name. Short numbers (<= 2 digits, e.g. "Series 3")
       stay.
    7. Collapse whitespace.

    Returns empty string for empty/whitespace-only input.
    """
    if not raw:
        return ""

    text = raw

    # 1. Strip vendor codes BEFORE lowercase (regex uses [A-Z])
    text = _VENDOR_CODE_RE.sub(" ", text)

    # 2. Brackets → whitespace
    text = _BRACKETS_RE.sub(" ", text)

    # 3. Pre-fold characters that NFKD doesn't decompose (Polish Ł/ł, German ß, …)
    for src, dst in _PRE_FOLD.items():
        if src in text:
            text = text.replace(src, dst)

    # 4. Unicode normalize — separate base + combining marks, drop the marks
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # 5. Lowercase
    text = text.lower()

    # 6. Strip currency / domain tokens (word-bounded so we don't hit
    # "uplandnetto"-like accidents — there are none in practice but safe).
    # Numbers in the name are KEPT — they may be intrinsic (e.g. "Pakiet 3000 km",
    # "Series 5"). The price lives separately in `net_amount` and disambiguates
    # the hash.
    for token in _CURRENCY_TOKENS:
        text = re.sub(rf"\b{re.escape(token)}\b", " ", text)

    # 7. Collapse whitespace
    text = " ".join(text.split())

    return text


def compute_canonical_id(name: str, net_amount: float | None) -> str:
    """Stable 12-char hex hash of (normalized_name | rounded_net).

    Same inputs → same id, across languages and formatting variants.
    Different prices → different id (e.g. 47970 vs 50000 for the same name).
    `None` net is preserved distinctly from `0.0`.
    """
    normalized = normalize_name(name)
    if net_amount is None:
        price_key = "none"
    else:
        price_key = f"{round(float(net_amount), 2):.2f}"
    payload = f"{normalized}|{price_key}".encode("utf-8")
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()[:12]


def _ensure_field_id(item: dict[str, Any], fallback_prefix: str, idx: int) -> str:
    fid = item.get("field_id")
    if fid:
        return str(fid)
    return f"{fallback_prefix}_{idx}"


def _extract_net(item: dict[str, Any]) -> float | None:
    """Try several keys (numeric `net_amount`, parsed `price_net`/`price`).

    Conservative: only returns explicit numeric values, no string parsing here.
    The pipeline_normalization pass populates `net_amount` upstream via
    price_inference.infer_price_pair.
    """
    val = item.get("net_amount")
    if isinstance(val, (int, float)):
        return float(val)
    return None


def flag_potential_duplicates(card_summary: dict[str, Any]) -> dict[str, Any]:
    """Mark items with the same canonical_id by cross-pointing `duplicate_of`.

    Operates over:
    - paid_options[]
    - service_equipment.components[]
    - service_equipment (top-level, treated as one item)

    Mutates a deep copy — caller's data is untouched.

    Appends `_duplicate_flags: list[{canonical_id, field_ids, names}]` to the
    returned card_summary as audit trail.
    """
    if not card_summary:
        return card_summary

    card = copy.deepcopy(card_summary)

    # ── Step 1: collect every item with computed canonical_id + field_id ──
    # Each entry: (canonical_id, field_id, item_ref, name)
    entries: list[tuple[str, str, dict[str, Any], str]] = []

    paid_options = card.get("paid_options") or []
    for idx, opt in enumerate(paid_options):
        if not isinstance(opt, dict):
            continue
        name = (opt.get("name") or "").strip()
        if not name:
            continue
        fid = _ensure_field_id(opt, "po", idx)
        opt["field_id"] = fid
        cid = compute_canonical_id(name, _extract_net(opt))
        opt["canonical_id"] = cid
        entries.append((cid, fid, opt, name))

    svc_eq = card.get("service_equipment")
    if isinstance(svc_eq, dict):
        # Components first
        components = svc_eq.get("components") or []
        for idx, comp in enumerate(components):
            if not isinstance(comp, dict):
                continue
            name = (comp.get("name") or "").strip()
            if not name:
                continue
            fid = _ensure_field_id(comp, "se_comp", idx)
            comp["field_id"] = fid
            cid = compute_canonical_id(name, _extract_net(comp))
            comp["canonical_id"] = cid
            entries.append((cid, fid, comp, name))

        # Top-level service_equipment as aggregate
        agg_name = (svc_eq.get("name") or "").strip()
        if agg_name:
            fid = _ensure_field_id(svc_eq, "se", 0)
            svc_eq["field_id"] = fid
            cid = compute_canonical_id(agg_name, _extract_net(svc_eq))
            svc_eq["canonical_id"] = cid
            entries.append((cid, fid, svc_eq, agg_name))

    # ── Step 2: group by canonical_id, cross-point duplicate_of ──
    by_canonical: dict[str, list[tuple[str, dict[str, Any], str]]] = {}
    for cid, fid, ref, name in entries:
        by_canonical.setdefault(cid, []).append((fid, ref, name))

    duplicate_flags: list[dict[str, Any]] = []
    for cid, members in by_canonical.items():
        if len(members) < 2:
            continue
        member_fids = [fid for fid, _, _ in members]
        for fid, ref, _ in members:
            # Point to the OTHER members (joined by comma if 3+; UI uses list)
            others = [f for f in member_fids if f != fid]
            # Single string ref for backward-compat with tests/UI; if 3+ items,
            # pick the first other — UI consumes `_duplicate_flags` for full set.
            ref["duplicate_of"] = others[0] if others else None
        duplicate_flags.append({
            "canonical_id": cid,
            "field_ids": member_fids,
            "names": [name for _, _, name in members],
        })

    if duplicate_flags:
        card["_duplicate_flags"] = duplicate_flags

    return card
