"""Regression tests for Gemini response_schema rejection surfacing.

When Gemini rejects the response_schema with a 400 INVALID_ARGUMENT
("too many states for serving") error, both Pro and Flash use the SAME
schema, so model fallback and retries cannot recover. Without these
guards the pipeline silently returned `{}` and downstream deterministic
backfills produced a Frankenstein vehicle merging unrelated data.

These tests pin the contract: ClientError 400 INVALID_ARGUMENT MUST
propagate, while other 4xx (auth, quota) keep the existing fallback
behavior.
"""

from __future__ import annotations

import pytest
from google.genai import errors as genai_errors


def _make_invalid_argument_error() -> genai_errors.ClientError:
    return genai_errors.ClientError(
        400,
        {
            "error": {
                "code": 400,
                "status": "INVALID_ARGUMENT",
                "message": "The specified schema produces a constraint that has too many states for serving",
            }
        },
    )


def _make_other_client_error() -> genai_errors.ClientError:
    return genai_errors.ClientError(
        429,
        {
            "error": {
                "code": 429,
                "status": "RESOURCE_EXHAUSTED",
                "message": "Rate limit exceeded",
            }
        },
    )


# ═══════════════════════════════════════════════════════════════════
# pipeline_digital_twin — Pro and Flash callers
# ═══════════════════════════════════════════════════════════════════


def test_digital_twin_pro_reraises_invalid_argument(monkeypatch) -> None:
    from core import pipeline_digital_twin as pdt

    def _raise_invalid_arg(*a, **kw):
        raise _make_invalid_argument_error()

    monkeypatch.setattr(pdt, "generate_content_with_retry", _raise_invalid_arg)

    with pytest.raises(genai_errors.ClientError) as exc:
        pdt._call_gemini_pro(client=None, contents=[])
    assert exc.value.status == "INVALID_ARGUMENT"


def test_digital_twin_pro_swallows_other_client_errors(monkeypatch) -> None:
    """Non-INVALID_ARGUMENT 4xx (e.g. rate limit) must NOT propagate from
    `_call_gemini_pro` so the orchestrator can fall back to Flash."""
    from core import pipeline_digital_twin as pdt

    def _raise_rate_limit(*a, **kw):
        raise _make_other_client_error()

    monkeypatch.setattr(pdt, "generate_content_with_retry", _raise_rate_limit)

    result = pdt._call_gemini_pro(client=None, contents=[])
    assert result == {}


def test_digital_twin_flash_reraises_invalid_argument(monkeypatch) -> None:
    from core import pipeline_digital_twin as pdt

    def _raise_invalid_arg(*a, **kw):
        raise _make_invalid_argument_error()

    monkeypatch.setattr(pdt, "generate_content_with_retry", _raise_invalid_arg)

    with pytest.raises(genai_errors.ClientError) as exc:
        pdt._call_gemini_flash(client=None, contents=[])
    assert exc.value.status == "INVALID_ARGUMENT"


def test_digital_twin_flash_swallows_other_client_errors(monkeypatch) -> None:
    from core import pipeline_digital_twin as pdt

    def _raise_rate_limit(*a, **kw):
        raise _make_other_client_error()

    monkeypatch.setattr(pdt, "generate_content_with_retry", _raise_rate_limit)

    result = pdt._call_gemini_flash(client=None, contents=[])
    assert result == {}


# ═══════════════════════════════════════════════════════════════════
# pipeline_card_summary — outer try around CardSummary schema call
# ═══════════════════════════════════════════════════════════════════


def test_card_summary_reraises_invalid_argument(monkeypatch) -> None:
    from core import pipeline_card_summary as pcs

    # Skip the Gemini client construction
    monkeypatch.setattr(pcs, "get_gemini_client", lambda: object())
    # Skip the doc-type classifier — return the "Oferta na samochód" branch
    monkeypatch.setattr(
        pcs, "classify_document_type", lambda *a, **kw: "Oferta na samochód"
    )
    # The schema call itself raises INVALID_ARGUMENT
    monkeypatch.setattr(
        pcs,
        "_call_with_pro_flash_fallback",
        lambda **kw: (_ for _ in ()).throw(_make_invalid_argument_error()),
    )

    pro_data = {"brand": "Toyota", "model": "Hilux", "digital_twin": {}}
    with pytest.raises(genai_errors.ClientError) as exc:
        pcs.generate_card_summary_from_twin(pro_data)
    assert exc.value.status == "INVALID_ARGUMENT"


def test_card_summary_swallows_other_client_errors(monkeypatch) -> None:
    """Non-INVALID_ARGUMENT errors (e.g. rate limit) must keep the existing
    fallback so the pipeline still produces a record (empty card_summary)
    rather than aborting on transient issues."""
    from core import pipeline_card_summary as pcs

    monkeypatch.setattr(pcs, "get_gemini_client", lambda: object())
    monkeypatch.setattr(
        pcs, "classify_document_type", lambda *a, **kw: "Oferta na samochód"
    )
    monkeypatch.setattr(
        pcs,
        "_call_with_pro_flash_fallback",
        lambda **kw: (_ for _ in ()).throw(_make_other_client_error()),
    )

    pro_data = {"brand": "Toyota", "model": "Hilux", "digital_twin": {}}
    result = pcs.generate_card_summary_from_twin(pro_data)
    assert result.get("card_summary") == {}
