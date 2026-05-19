"""V3 pipeline integration glue.

Bridges `extractor_v2` ↔ `pipeline_raw_extraction` + `pipeline_normalization`,
with a feature-flag-gated LIVE mode and a SHADOW mode that logs diffs to JSON
files without touching the actual card_summary.

Feature flag: `EXTRACTION_PROMPTS_V3`
  - "1" → LIVE: run V3 pipeline, merge result into pro_data.
  - anything else (default) → SHADOW: run V3 pipeline in try/except, log
    diff to `backend/eval/shadow_run/<YYYY-MM-DD>/<hash>.json`. Do NOT
    modify pro_data.

Shadow output schema:
  {
    "timestamp": ISO-8601,
    "v3_enabled": false,
    "legacy_keys": ["base_price", "base_price_net", ...],
    "v3_keys": [...],
    "field_diff": {field: {"legacy": ..., "v3": ...}, ...},
    "v3_errors": [...],
  }
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_SHADOW_DIR = (
    Path(__file__).resolve().parent.parent / "eval" / "shadow_run"
)


# Fields we focus on for shadow-vs-legacy diffs. Numeric V3 fields and dedup.
_V3_FIELDS_TO_DIFF = (
    "base_price_net",
    "base_price_gross",
    "base_price_vat",
    "options_price_net",
    "options_price_gross",
    "options_price_vat",
    "total_price_net",
    "total_price_gross",
    "total_price_vat",
    "_duplicate_flags",
    "source_offsets_by_field",
)


def apply_v3_enrichment_or_shadow(
    pro_data: dict[str, Any],
    *,
    pdf_bytes: bytes,
    live: bool,
) -> dict[str, Any]:
    """Run V3 enrichment in LIVE or SHADOW mode.

    LIVE mode:
        - Run PASS A (raw_extraction) + PASS B (normalization) on pdf_bytes
        - MERGE V3 numeric/dedup fields into pro_data["card_summary"]
        - Return mutated pro_data

    SHADOW mode:
        - Run V3 pipeline in try/except
        - Log diff to JSON file
        - Return pro_data UNCHANGED

    Either mode is non-fatal — exceptions are caught and logged.
    """
    card_summary = pro_data.get("card_summary")
    if not isinstance(card_summary, dict):
        return pro_data

    v3_card: dict[str, Any] | None = None
    errors: list[str] = []
    started = time.time()

    try:
        from core.pipeline_normalization import normalize_raw_to_card_summary
        from core.pipeline_raw_extraction import extract_raw_from_pdf

        raw = extract_raw_from_pdf(pdf_bytes)
        v3_card = normalize_raw_to_card_summary(
            raw, legacy_card_seed=copy.deepcopy(card_summary)
        )
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
        logger.warning("V3 enrichment failed (%s mode): %s", "LIVE" if live else "SHADOW", e)

    elapsed = time.time() - started

    if live:
        if v3_card is not None:
            # MERGE: prefer V3-derived numeric/dedup fields, keep legacy
            # body_style/powertrain/etc.
            for key, val in v3_card.items():
                if key in card_summary and val in (None, [], {}):
                    continue  # don't clobber legacy with empty V3
                card_summary[key] = val
        # Even if errors — leave pro_data intact, downstream handles missing data
        return pro_data

    # SHADOW mode — log diff only
    _log_shadow_diff(card_summary, v3_card, errors, elapsed_s=elapsed)
    return pro_data


def _log_shadow_diff(
    legacy: dict[str, Any],
    v3: dict[str, Any] | None,
    errors: list[str],
    *,
    elapsed_s: float,
) -> None:
    """Write a shadow-run diff JSON file. Best-effort; never raises."""
    try:
        today = date.today().isoformat()
        day_dir = _SHADOW_DIR / today
        day_dir.mkdir(parents=True, exist_ok=True)

        # Hash on first 1KB of legacy json — stable per-vehicle identifier
        legacy_blob = json.dumps(legacy, ensure_ascii=False, sort_keys=True)[:1024]
        sha = hashlib.sha1(legacy_blob.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]

        field_diff: dict[str, dict[str, Any]] = {}
        if v3 is not None:
            for key in _V3_FIELDS_TO_DIFF:
                legacy_val = legacy.get(key)
                v3_val = v3.get(key)
                if legacy_val != v3_val:
                    field_diff[key] = {"legacy": legacy_val, "v3": v3_val}

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "v3_enabled": False,
            "elapsed_s": round(elapsed_s, 3),
            "errors": errors,
            "field_diff": field_diff,
            "legacy_keys_present": sorted(legacy.keys()),
            "v3_keys_present": sorted(v3.keys()) if v3 is not None else [],
        }
        out_path = day_dir / f"{sha}.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("V3 shadow diff written: %s (%d diffs)", out_path, len(field_diff))
    except Exception as e:  # pragma: no cover — defensive
        logger.warning("Shadow run logging failed: %s", e)
