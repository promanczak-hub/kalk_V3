"""Multi-hypothesis price reconciliation (generate-and-test price auditor).

Instead of a single LLM "deduction", compute the full net/gross breakdown under 4
deterministic hypotheses (components netto/brutto × final netto/brutto), score each
by how well it reproduces EVERY independent total the PDF prints (catalog + final
net/gross pair), and pick the best. The winning hypothesis reveals the true price
domain and a reconciled breakdown.

The arithmetic is 100% deterministic Python — the LLM never converts net↔gross here
(it proved unreliable at ÷1,23). An optional judge (`run_judge`, added in a later
phase) only confirms the deterministic winner against the PDF or flags HITL; it can
never inject numbers. See plans/multi-hypothesis-price-reconciliation.md.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_FLASH_MODEL = "gemini-2.5-flash"

# Reconciliation tolerances.
_TOL_PLN = 5.0       # absolute residual under which a path "reconciles"
_TOL_FRAC = 0.005    # …or 0.5% of the largest stated total, whichever is larger
_GAP_PLN = 50.0      # winner must beat the next DISTINCT source-domain by this much

_DOMAINS = ("netto", "brutto")

RULE_FAILED = "PRICE_RECONCILIATION_FAILED"
RULE_AMBIGUOUS = "PRICE_RECONCILIATION_AMBIGUOUS"


# ── Internal models ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Hypothesis:
    """One interpretation: how to read the component amounts, and how to read
    any UNLABELED final total."""

    source_domain: str  # "netto" | "brutto" — domain of base/options/discount as printed
    final_domain: str   # "netto" | "brutto" — assumed domain of unlabeled anchors


@dataclass
class StatedNumber:
    """An independent total printed in the document, used to score a path."""

    kind: str     # "catalog" | "total"
    amount: float
    domain: str   # "netto" | "brutto" | "unknown" (from the printed label)


@dataclass
class ExtractedRaw:
    """Computation inputs (bare printed amounts) + the anchors to score against.

    Component amounts are read WITHOUT trusting their printed net/brutto label —
    the label may be wrong (domain-flip). Only the independent anchor totals carry
    a trusted domain (the net/gross pair is internally consistent)."""

    base_amount: float
    options_amount: float
    discount_amount: float
    service_amount: float
    anchors: list[StatedNumber] = field(default_factory=list)
    vat_rate: float = 0.23


@dataclass
class PathResult:
    hypothesis: Hypothesis
    base_net: float
    base_gross: float
    options_net: float
    options_gross: float
    service_net: float
    service_gross: float
    rabat_net: float
    rabat_gross: float
    catalog_net: float
    catalog_gross: float
    total_net: float
    total_gross: float
    residual_pln: float
    penalties: float

    @property
    def score(self) -> float:
        return self.residual_pln + self.penalties

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_domain": self.hypothesis.source_domain,
            "final_domain": self.hypothesis.final_domain,
            "base_net": self.base_net,
            "base_gross": self.base_gross,
            "options_net": self.options_net,
            "options_gross": self.options_gross,
            "service_net": self.service_net,
            "service_gross": self.service_gross,
            "rabat_net": self.rabat_net,
            "rabat_gross": self.rabat_gross,
            "catalog_net": self.catalog_net,
            "catalog_gross": self.catalog_gross,
            "total_net": self.total_net,
            "total_gross": self.total_gross,
            "residual_pln": self.residual_pln,
            "penalties": self.penalties,
            "score": round(self.score, 2),
        }


@dataclass
class ReconResult:
    verdict: str  # "ok" | "ambiguous" | "unreconcilable"
    best: PathResult
    all_paths: list[PathResult]
    source_domain: str
    warning: dict[str, Any] | None = None
    judge: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "source_domain": self.source_domain,
            "best": self.best.to_dict(),
            "all_paths": [p.to_dict() for p in self.all_paths],
            "warning": self.warning,
            "judge": self.judge,
        }


# ── Helpers ──────────────────────────────────────────────────────────────


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(" ", "").replace("PLN", "").replace(",", ".").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_price_string(raw: Any) -> tuple[float | None, str]:
    """Parse a legacy price string like '312 000,00 PLN brutto' → (312000.0, 'brutto').

    Handles both Polish comma-decimal ('312 000,00') and dot-decimal ('167 218.50')
    formats. Domain comes from the netto/brutto suffix, else 'unknown'."""
    if not isinstance(raw, str) or not raw.strip():
        return None, "unknown"
    low = raw.lower()
    domain = "brutto" if "brutto" in low else "netto" if "netto" in low else "unknown"
    cleaned = re.sub(r"[^0-9.,]", "", raw)
    if not cleaned:
        return None, domain
    has_dot, has_comma = "." in cleaned, "," in cleaned
    if has_dot and has_comma:
        # rightmost separator is the decimal point; the other groups thousands
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif has_comma:
        head, _, tail = cleaned.rpartition(",")
        cleaned = f"{head}.{tail}" if len(tail) <= 2 else cleaned.replace(",", "")
    elif has_dot:
        head, _, tail = cleaned.rpartition(".")
        if len(tail) == 3:  # '312.000' → thousands separator, not decimal
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned), domain
    except ValueError:
        return None, domain


def _split(amount: float, domain: str, vat: float) -> tuple[float, float]:
    """(net, gross) for an amount printed in `domain`."""
    if domain == "brutto":
        return round(amount / (1 + vat), 2), round(amount, 2)
    return round(amount, 2), round(amount * (1 + vat), 2)


def _printed_amount(line: dict[str, Any]) -> tuple[float, str]:
    """The single printed number + its domain for a raw price line.

    Label wins: 'brutto' → gross side, 'netto' → net side. Falls back to whichever
    side is populated. Domain 'unknown' when the label gives no hint."""
    label = str(line.get("label") or "").lower()
    net = _coerce_float(line.get("net_amount"))
    gross = _coerce_float(line.get("gross_amount"))
    if "brutto" in label:
        return (gross if gross is not None else (net or 0.0)), "brutto"
    if "netto" in label:
        return (net if net is not None else (gross or 0.0)), "netto"
    val = net if net is not None else gross
    return (val or 0.0), "unknown"


def _extract_raw(card_summary: dict[str, Any], known: dict[str, Any] | None) -> ExtractedRaw:
    """Build computation inputs + anchors from the stashed PASS-A raw price lines,
    falling back to the aggregated card triples for legacy vehicles."""
    lines = card_summary.get("_raw_price_lines") or []
    base = options = discount = service = 0.0
    anchors: list[StatedNumber] = []
    vat = 0.23

    for ln in lines:
        if not isinstance(ln, dict):
            continue
        role = str(ln.get("role") or "")
        amount, domain = _printed_amount(ln)
        ln_vat = _coerce_float(ln.get("vat_rate"))
        if ln_vat and 0 < ln_vat < 1:
            vat = ln_vat
        if role == "base_price":
            base = amount
        elif role == "options_total":
            options = amount
        elif role == "discount":
            discount = abs(amount)
        elif role == "service_total":
            service = amount
        elif role == "total_price":
            anchors.append(StatedNumber("total", amount, domain))
        else:
            quoted = str(ln.get("quoted_text") or "").lower()
            if "katalog" in quoted:
                anchors.append(StatedNumber("catalog", amount, domain))

    if not lines:
        # Non-V3 card_summary: prices live as numeric *_net/*_gross fields, in the
        # validator's parsed_prices, or as legacy strings ('312 000,00 PLN brutto').
        val = card_summary.get("_validation")
        parsed = val.get("parsed_prices") if isinstance(val, dict) else None
        parsed = parsed if isinstance(parsed, dict) else {}

        def _amount(numeric_keys: tuple[str, ...], parsed_key: str, string_key: str) -> float:
            for k in numeric_keys:
                v = _coerce_float(card_summary.get(k))
                if v:
                    return v
            v = _coerce_float(parsed.get(parsed_key))
            if v:
                return v
            amt, _dom = _parse_price_string(card_summary.get(string_key))
            return amt or 0.0

        base = _amount(("base_price_net", "base_price_gross"), "base", "base_price")
        options = _amount(("options_price_net", "options_price_gross"), "options", "options_price")

        # Zabudowa / pakiet serwisowy lives in service_equipment, NOT options — it's
        # part of the total, so it must enter the catalog sum (else the total won't
        # close; e.g. Renault Master izoterma: 85 497,30 zabudowa missing → false fail).
        se = card_summary.get("service_equipment")
        if isinstance(se, dict):
            service = (
                _coerce_float(se.get("net_amount"))
                or _coerce_float(se.get("gross_amount"))
                or _parse_price_string(se.get("total_price_net"))[0]
                or _parse_price_string(se.get("total_price_gross"))[0]
                or 0.0
            )

        disc_obj = card_summary.get("discount")
        if isinstance(disc_obj, dict):
            discount = abs(_coerce_float(disc_obj.get("explicit_rabat_pln")) or 0.0)

        tot_net = _coerce_float(card_summary.get("total_price_net"))
        tot_gross = _coerce_float(card_summary.get("total_price_gross"))
        if tot_net:
            anchors.append(StatedNumber("total", tot_net, "netto"))
        if tot_gross:
            anchors.append(StatedNumber("total", tot_gross, "brutto"))
        if not anchors:
            # Single stated total — domain from its suffix, else card-level _price_domain.
            amt, dom = _parse_price_string(card_summary.get("total_price"))
            tot = amt if amt else _coerce_float(parsed.get("total"))
            if dom == "unknown":
                dom = str(card_summary.get("_price_domain") or "unknown")
            if tot:
                anchors.append(StatedNumber("total", tot, dom if dom in _DOMAINS else "unknown"))

    if known:
        kb = _coerce_float(known.get("base_net")) or _coerce_float(known.get("base_gross"))
        ko = _coerce_float(known.get("options_net")) or _coerce_float(known.get("options_gross"))
        ks = _coerce_float(known.get("service_net")) or _coerce_float(known.get("service_gross"))
        kr = _coerce_float(known.get("rabat_pln"))
        if kb is not None:
            base = kb
        if ko is not None:
            options = ko
        if ks is not None:
            service = ks
        if kr is not None:
            discount = abs(kr)
        ktn = _coerce_float(known.get("total_net"))
        ktg = _coerce_float(known.get("total_gross"))
        if ktn is not None:
            anchors.append(StatedNumber("total", ktn, "netto"))
        if ktg is not None:
            anchors.append(StatedNumber("total", ktg, "brutto"))

    return ExtractedRaw(base, options, discount, service, anchors, vat)


def _compute_path(raw: ExtractedRaw, h: Hypothesis) -> PathResult:
    vat = raw.vat_rate if 0 < raw.vat_rate < 1 else 0.23
    bn, bg = _split(raw.base_amount, h.source_domain, vat)
    on, og = _split(raw.options_amount, h.source_domain, vat)
    sn, sg = _split(raw.service_amount, h.source_domain, vat)
    rn, rg = _split(raw.discount_amount, h.source_domain, vat)
    cat_n, cat_g = round(bn + on + sn, 2), round(bg + og + sg, 2)
    tot_n, tot_g = round(cat_n - rn, 2), round(cat_g - rg, 2)
    computed = {"catalog": (cat_n, cat_g), "total": (tot_n, tot_g)}

    residual = 0.0
    for a in raw.anchors:
        comp = computed.get(a.kind)
        if comp is None:
            continue
        dom = a.domain if a.domain in _DOMAINS else h.final_domain
        predicted = comp[1] if dom == "brutto" else comp[0]
        residual += abs(a.amount - predicted)

    penalties = 0.0
    if tot_n < 0:
        penalties += abs(tot_n)
    if rn > cat_n:
        penalties += rn - cat_n

    return PathResult(
        hypothesis=h,
        base_net=bn, base_gross=bg,
        options_net=on, options_gross=og,
        service_net=sn, service_gross=sg,
        rabat_net=rn, rabat_gross=rg,
        catalog_net=cat_n, catalog_gross=cat_g,
        total_net=tot_n, total_gross=tot_g,
        residual_pln=round(residual, 2),
        penalties=round(penalties, 2),
    )


def _decide(paths: list[PathResult], max_anchor: float) -> tuple[str, PathResult]:
    """Group by source domain (the meaningful axis), compare the best of each.

    A tie between DIFFERENT source domains is genuine ambiguity — the engine must
    not guess. Only a clear, isolated winner reconciles."""
    by_src: dict[str, list[PathResult]] = {}
    for p in paths:
        by_src.setdefault(p.hypothesis.source_domain, []).append(p)
    ranked = sorted((min(ps, key=lambda p: p.score) for ps in by_src.values()), key=lambda p: p.score)
    best = ranked[0]

    tol = max(_TOL_PLN, max_anchor * _TOL_FRAC)
    if best.score > tol:
        return "unreconcilable", best
    if len(ranked) > 1 and (ranked[1].score - best.score) < _GAP_PLN:
        return "ambiguous", best
    return "ok", best


def _build_warning(verdict: str, best: PathResult) -> dict[str, Any] | None:
    if verdict == "ok":
        return None
    if verdict == "unreconcilable":
        return {
            "rule": RULE_FAILED,
            "severity": "ERROR",
            "field_path": "total_price",
            "message": (
                f"Żadna z 4 ścieżek net/brutto nie domyka ceny (najlepsze residuum "
                f"{best.residual_pln:.2f} PLN). Wymaga ręcznej weryfikacji."
            ),
        }
    return {
        "rule": RULE_AMBIGUOUS,
        "severity": "WARNING",
        "field_path": "total_price",
        "message": (
            "Co najmniej dwie ścieżki net/brutto domykają cenę równie dobrze — "
            "domena nierozstrzygnięta arytmetycznie. Wymaga potwierdzenia."
        ),
    }


# ── LLM judge (bounded: confirm winner / flag HITL — NEVER alters numbers) ──


class _JudgeSchema(BaseModel):
    agrees_with_winner: bool
    chosen_source_domain: str  # plain str (no enum — avoids Gemini "too many states")
    reasoning: str
    confidence: float


_JUDGE_PROMPT = (
    "Jesteś ekspertem-krytykiem ds. cenników motoryzacyjnych. System wyliczył już "
    "DETERMINISTYCZNIE 4 hipotezy ceny (składniki netto/brutto × cena końcowa "
    "netto/brutto) i wybrał zwycięską (`winner_source_domain`) po najmniejszym "
    "residuum względem kwot wydrukowanych w PDF.\n\n"
    "Twoje zadanie: zweryfikuj ten wybór wobec dokumentu metodą 'Drzewa Myśli' (Tree "
    "of Thoughts). KRYTYCZNE: NIE PRZELICZAJ kwot i NIE PODAWAJ nowych liczb — liczby "
    "są już policzone deterministycznie. Oceniasz WYŁĄCZNIE, czy DOMENA zwycięskiej "
    "ścieżki zgadza się z dokumentem. Zapisz rozumowanie krok po kroku w `reasoning`.\n\n"
    "KROK 1 — ETYKIETY: znajdź w PDF jawne oznaczenia przy cenie końcowej i "
    "katalogowej ('netto', 'brutto', 'z VAT', 'bez VAT', wiersz netto/VAT/brutto, "
    "'VAT-marża' / 'opodatkowanie marży').\n"
    "KROK 2 — CROSS-CHECK VAT: sprawdź, czy podana w PDF para netto/brutto trzyma się "
    "stawki widocznej w dokumencie (zwykle 23%, ale bywa 8%/0%; przy VAT-marży NIE ma "
    "rozbicia). Czy `winner_total_net` i `winner_total_gross` odpowiadają tej parze "
    "z dokumentu?\n"
    "KROK 3 — KONFRONTACJA ŚCIEŻEK: spójrz na residua wszystkich ścieżek. Czy "
    "zwycięzca jest spójny z tym, co fizycznie pisze dokument? Czy któraś inna ścieżka "
    "pasuje do etykiet wyraźnie lepiej?\n"
    "KROK 4 — WERDYKT: jeśli etykiety i cross-check potwierdzają domenę zwycięzcy → "
    "agrees_with_winner=true. Jeśli dokument wyraźnie wskazuje INNĄ domenę, albo nic "
    "nie jest jednoznaczne (brak etykiet, VAT-marża, sprzeczne sygnały) → "
    "agrees_with_winner=false (system skieruje ofertę do weryfikacji ręcznej — to "
    "BEZPIECZNE, lepsze niż zgadywanie).\n\n"
    "Zwróć JSON: {agrees_with_winner (bool), chosen_source_domain ('netto'|'brutto'), "
    "reasoning (krótko, po polsku — wymień, który KROK zadecydował), confidence (0..1)}."
)


def _judge(
    best: PathResult,
    paths: list[PathResult],
    pdf_bytes: bytes,
    pdf_mime: str = "application/pdf",
) -> dict[str, Any] | None:
    """Ask Gemini Flash to confirm the deterministic winner against the PDF.

    Returns the judge dict, or ``None`` on any failure (judge is advisory — its
    absence never blocks the deterministic verdict). It can only DOWNGRADE an
    ``ok`` verdict to ``ambiguous``; it can never change the computed numbers."""
    try:
        from google.genai import types

        from core.gemini_client import SAFETY_SETTINGS_PERMISSIVE, get_gemini_client
    except Exception:
        logger.warning("[RECONCILE] judge deps unavailable", exc_info=True)
        return None

    try:
        client = get_gemini_client()
        config = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1024,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            response_mime_type="application/json",
            response_schema=_JudgeSchema,
            system_instruction=_JUDGE_PROMPT,
            safety_settings=SAFETY_SETTINGS_PERMISSIVE,
        )
        summary = {
            "winner_source_domain": best.hypothesis.source_domain,
            "winner_total_net": best.total_net,
            "winner_total_gross": best.total_gross,
            "paths": [
                {
                    "source_domain": p.hypothesis.source_domain,
                    "final_domain": p.hypothesis.final_domain,
                    "total_net": p.total_net,
                    "total_gross": p.total_gross,
                    "residual_pln": p.residual_pln,
                }
                for p in paths
            ],
        }
        contents: list[Any] = [types.Part.from_text(text=json.dumps(summary, ensure_ascii=False))]
        contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type=pdf_mime))
        response = client.models.generate_content(
            model=_FLASH_MODEL, contents=contents, config=config
        )
        data = json.loads(getattr(response, "text", "{}") or "{}")
        return data if isinstance(data, dict) else None
    except Exception:
        logger.warning("[RECONCILE] judge call failed — verdict stands", exc_info=True)
        return None


# ── Public entry ─────────────────────────────────────────────────────────


def reconcile_prices(
    card_summary: dict[str, Any],
    *,
    known: dict[str, Any] | None = None,
    pdf_bytes: bytes | None = None,
    pdf_mime: str = "application/pdf",
    run_judge: bool = True,
) -> ReconResult:
    """Reconcile a vehicle's price across 4 net/brutto hypotheses.

    Parameters
    ----------
    card_summary:
        Vehicle card. Reads `_raw_price_lines` (stashed PASS-A corpus) when present,
        else falls back to the aggregated `*_price_{net,gross}` triples.
    known:
        Optional user-supplied partial price anchors (panel manual form).
    pdf_bytes:
        Source PDF for the LLM judge (used only when `run_judge`).
    run_judge:
        When True, the LLM judge confirms the deterministic winner against the PDF
        (added in a later phase; no-op until then). It can never alter the numbers.
    """
    raw = _extract_raw(card_summary, known)
    paths = [
        _compute_path(raw, Hypothesis(source_domain=s, final_domain=f))
        for s in _DOMAINS
        for f in _DOMAINS
    ]
    max_anchor = max((a.amount for a in raw.anchors), default=0.0)
    verdict, best = _decide(paths, max_anchor)
    warning = _build_warning(verdict, best)

    result = ReconResult(
        verdict=verdict,
        best=best,
        all_paths=paths,
        source_domain=best.hypothesis.source_domain,
        warning=warning,
    )

    if run_judge and pdf_bytes:
        judge = _judge(best, paths, pdf_bytes, pdf_mime)
        if judge is not None:
            result.judge = judge
            # Judge may only DOWNGRADE confidence → HITL, never alter the numbers.
            if result.verdict == "ok" and judge.get("agrees_with_winner") is False:
                result.verdict = "ambiguous"
                result.warning = _build_warning("ambiguous", best)

    return result


def reconcile_and_flag(
    card_summary: dict[str, Any] | None,
    *,
    known: dict[str, Any] | None = None,
    pdf_bytes: bytes | None = None,
    pdf_mime: str = "application/pdf",
    run_judge: bool = True,
) -> ReconResult | None:
    """Run reconciliation and write its verdict onto `card_summary` in place
    (mirrors `validate_and_flag_prices`).

    Writes `_reconciliation` (full breakdown + all paths), sets the authoritative
    `_price_domain` only on a confident `ok`, and appends any HITL warning into
    `_validation.warnings` so the existing `_needs_hitl_review` machinery routes
    the vehicle. Never raises — an audit failure must not break extraction."""
    if not isinstance(card_summary, dict):
        return None
    try:
        result = reconcile_prices(
            card_summary,
            known=known,
            pdf_bytes=pdf_bytes,
            pdf_mime=pdf_mime,
            run_judge=run_judge,
        )
    except Exception:
        logger.warning("[RECONCILE] reconcile_and_flag failed — skipped", exc_info=True)
        return None

    card_summary["_reconciliation"] = result.to_dict()
    if result.verdict == "ok":
        card_summary["_price_domain"] = result.source_domain
    if result.warning is not None:
        validation = card_summary.setdefault("_validation", {})
        if isinstance(validation, dict):
            warnings = validation.setdefault("warnings", [])
            if isinstance(warnings, list):
                warnings.append(result.warning)
    return result
