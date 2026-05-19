import json
import logging
import os
from typing import Union, Callable, Optional

from core.pipeline_digital_twin import extract_digital_twin_from_pdf
from core.pipeline_card_summary import generate_card_summary_from_twin
from core.pipeline_deterministic_normalize import (
    normalize_card_summary_from_digital_twin,
)
from core.pipeline_discounts import match_fleet_discount
from core.pipeline_overrides import process_manual_override
from core.pipeline_price_validator import validate_and_flag_prices
from core.pipeline_v3_integration import (
    apply_v3_enrichment_or_shadow,
)

# Type alias for progress/cancel callbacks
ProgressCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]

logger = logging.getLogger(__name__)


def extract_vehicle_data_v2(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
    on_progress: Optional[ProgressCallback] = None,
    is_cancelled: Optional[CancelCheck] = None,
    text_data: Optional[str] = None,
) -> str:
    """
    Orchestrates the modular extraction pipeline:
    1. Extracts Digital Twin (Gemini 2.5 Pro)
    2. Generates Card Summary & Classifies Doc Type (Gemini 2.5 Flash)
    3. Matches Fleet Discounts from DB (Gemini 2.5 Flash)

    Supports optional progress reporting and cancellation between stages.
    """

    def _progress(status: str) -> None:
        if on_progress:
            on_progress(status)

    def _check_cancel() -> bool:
        return is_cancelled() if is_cancelled else False

    try:
        # 1. Digital Twin extraction (Gemini Pro — najdłuższy krok)
        _progress("extracting_twin")
        pro_data = extract_digital_twin_from_pdf(
            document_data, mime_type, text_data=text_data
        )
        if not pro_data:
            logger.error("Digital twin extraction returned empty result")
            raise ValueError(
                "Ekstrakcja cyfrowego bliźniaka nie zwróciła danych. "
                "Sprawdź format dokumentu i upewnij się, że Gemini API jest dostępne."
            )

        if _check_cancel():
            return "{}"

        # 2. Card Summary classification and mapping (Gemini Flash)
        _progress("generating_summary")
        pro_data = generate_card_summary_from_twin(pro_data)

        # 2.05 DETERMINISTIC NORMALIZE — Warstwa 3 (added 2026-05-19).
        # Flash reliably drops 80% of digital_twin.optional_equipment when
        # mapping to card_summary.paid_options / service_equipment. Real-world
        # cases: Renault Master izoterma (Pro=7 items → Flash=0), Toyota Hilux
        # (Pro=4 items → Flash=0). This deterministic post-processor fills the
        # gap by partitioning digital_twin.optional_equipment into paid_options
        # vs service_equipment.components using service-keyword regex (zabudowa/
        # izoterma/kontener/agregat/...). IDEMPOTENT — only fills missing
        # fields, never overwrites Flash output when present.
        card_summary = pro_data.get("card_summary")
        digital_twin = pro_data.get("digital_twin") or pro_data.get("digital_twin_data") or {}
        if isinstance(card_summary, dict) and isinstance(digital_twin, dict):
            pro_data["card_summary"] = normalize_card_summary_from_digital_twin(
                card_summary,
                digital_twin,
                # Real-world rows often have brand/model on top-level synthesis_data
                # while digital_twin.brand is null. Fall back so vehicle_class
                # classification still works.
                brand_fallback=pro_data.get("brand"),
                model_fallback=pro_data.get("model"),
            )

        # 2.1 V3 enrichment — three modes via EXTRACTION_PROMPTS_V3 env var:
        #   - "1" / "live"   → LIVE: run RAW + NORMALIZE, merge into pro_data
        #   - "shadow"       → SHADOW: run V3 in background, log diff (NO merge)
        #   - anything else  → SKIP (default): zero overhead per upload
        # SHADOW is OPT-IN because it ADDS a Gemini 2.5 Pro call (~10-30s) per
        # extraction. Use it during the migration window, then disable.
        v3_mode = (os.environ.get("EXTRACTION_PROMPTS_V3") or "").strip().lower()
        if v3_mode in ("1", "live", "shadow") and isinstance(document_data, (bytes, bytearray)):
            pro_data = apply_v3_enrichment_or_shadow(
                pro_data,
                pdf_bytes=bytes(document_data),
                live=v3_mode in ("1", "live"),
            )

        # 2.2 Deterministic Netto Override
        if text_data:
            text_lower = text_data.lower()
            if (
                "w cenach netto" in text_lower
                or "ceny netto" in text_lower
                or "kwoty podane są w netto" in text_lower
                or "bez vat" in text_lower
            ):
                logger.info(
                    "Deterministyczne wykrycie 'w cenach netto' w tekście. Nadpisywanie price_domain..."
                )
                if "card_summary" in pro_data:
                    pro_data["card_summary"]["price_domain"] = "netto"
            elif "w cenach brutto" in text_lower or "ceny brutto" in text_lower:
                if "card_summary" in pro_data:
                    pro_data["card_summary"]["price_domain"] = "brutto"

        # 2.5 Deterministic financial validation
        _progress("validating_prices")
        pro_data = validate_and_flag_prices(pro_data)

        if _check_cancel():
            return "{}"

        # 3. Apply Fleet Discount Matching (Gemini Flash)
        _progress("matching_discounts")
        pro_data = match_fleet_discount(pro_data)

        return json.dumps(pro_data, ensure_ascii=False)

    except ValueError:
        raise  # Let validation errors propagate to caller
    except Exception:
        logger.exception("Error in modular extractor pipeline")
        raise  # Let caller handle error status in DB


def process_single_twin(
    pro_data: dict,
    on_progress: Optional[ProgressCallback] = None,
    is_cancelled: Optional[CancelCheck] = None,
) -> str:
    """
    Process an already-extracted digital twin through pipeline stages 2-3.

    Used by the multi-vehicle flow where Phase 0 already produced the twin.
    Runs: card_summary → fleet discount matching.
    """

    def _progress(status: str) -> None:
        if on_progress:
            on_progress(status)

    def _check_cancel() -> bool:
        return is_cancelled() if is_cancelled else False

    try:
        _progress("generating_summary")
        pro_data = generate_card_summary_from_twin(pro_data)

        # 2.05 DETERMINISTIC NORMALIZE (multi-vehicle path)
        # Same Flash-gap fix as in `extract_vehicle_data_v2` — each split twin
        # gets its paid_options / service_equipment / vehicle_class / body_style
        # populated from digital_twin where Flash dropped them.
        card_summary = pro_data.get("card_summary")
        digital_twin = pro_data.get("digital_twin") or pro_data.get("digital_twin_data") or {}
        if isinstance(card_summary, dict) and isinstance(digital_twin, dict):
            pro_data["card_summary"] = normalize_card_summary_from_digital_twin(
                card_summary,
                digital_twin,
                brand_fallback=pro_data.get("brand"),
                model_fallback=pro_data.get("model"),
            )

        # 2.5 Deterministic financial validation
        _progress("validating_prices")
        pro_data = validate_and_flag_prices(pro_data)

        if _check_cancel():
            return "{}"

        _progress("matching_discounts")
        pro_data = match_fleet_discount(pro_data)

        return json.dumps(pro_data, ensure_ascii=False)

    except ValueError:
        raise  # Let validation errors propagate to caller
    except Exception:
        logger.exception("Error in single-twin pipeline")
        raise  # Let caller handle error status in DB


def process_manual_override_v2(original_json: dict, user_prompt: str) -> str:
    """
    Delegates user override patching to the pipeline_overrides module.
    """
    try:
        return process_manual_override(original_json, user_prompt)
    except Exception:
        logger.exception("Error in manual override pipeline")
        return json.dumps(original_json, ensure_ascii=False)
