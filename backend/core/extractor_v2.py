import json
import logging
from typing import Union, Callable, Optional

from core.pipeline_digital_twin import extract_digital_twin_from_pdf
from core.pipeline_card_summary import generate_card_summary_from_twin
from core.pipeline_discounts import match_fleet_discount
from core.pipeline_overrides import process_manual_override
from core.pipeline_price_validator import validate_and_flag_prices

# Type alias for progress/cancel callbacks
ProgressCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]

logger = logging.getLogger(__name__)


def extract_vehicle_data_v2(
    document_data: Union[str, bytes],
    mime_type: str = "application/pdf",
    on_progress: Optional[ProgressCallback] = None,
    is_cancelled: Optional[CancelCheck] = None,
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
        pro_data = extract_digital_twin_from_pdf(document_data, mime_type)
        if not pro_data:
            return "{}"

        if _check_cancel():
            return "{}"

        # 2. Card Summary classification and mapping (Gemini Flash)
        _progress("generating_summary")
        pro_data = generate_card_summary_from_twin(pro_data)

        # 2.5 Deterministic financial validation
        _progress("validating_prices")
        pro_data = validate_and_flag_prices(pro_data)

        if _check_cancel():
            return "{}"

        # 3. Apply Fleet Discount Matching (Gemini Flash)
        _progress("matching_discounts")
        pro_data = match_fleet_discount(pro_data)

        return json.dumps(pro_data, ensure_ascii=False)

    except Exception:
        logger.exception("Error in modular extractor pipeline")
        return "{}"


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

        # 2.5 Deterministic financial validation
        _progress("validating_prices")
        pro_data = validate_and_flag_prices(pro_data)

        if _check_cancel():
            return "{}"

        _progress("matching_discounts")
        pro_data = match_fleet_discount(pro_data)

        return json.dumps(pro_data, ensure_ascii=False)

    except Exception:
        logger.exception("Error in single-twin pipeline")
        return "{}"


def process_manual_override_v2(original_json: dict, user_prompt: str) -> str:
    """
    Delegates user override patching to the pipeline_overrides module.
    """
    try:
        return process_manual_override(original_json, user_prompt)
    except Exception:
        logger.exception("Error in manual override pipeline")
        return json.dumps(original_json, ensure_ascii=False)
