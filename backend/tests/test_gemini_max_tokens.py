"""Tests for the central max_output_tokens resolver (gemini_client).

Decision 2026-05-19: main Gemini extraction calls route their output-token
limit through resolve_max_output_tokens() so a single env var
(GEMINI_MAX_OUTPUT_TOKENS) tunes them all at once. Default = 65536 (Gemini 2.5
max). Deliberately-tiny calls keep their own hardcoded limits.
"""

from __future__ import annotations

import pytest

from core.gemini_client import (
    DEFAULT_GEMINI_MAX_OUTPUT_TOKENS,
    resolve_max_output_tokens,
)


class TestResolveMaxOutputTokens:
    def test_default_is_gemini_max(self) -> None:
        assert DEFAULT_GEMINI_MAX_OUTPUT_TOKENS == 65536

    def test_returns_default_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_MAX_OUTPUT_TOKENS", raising=False)
        assert resolve_max_output_tokens() == 65536

    def test_explicit_default_arg_honored_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GEMINI_MAX_OUTPUT_TOKENS", raising=False)
        assert resolve_max_output_tokens(8192) == 8192

    def test_env_override_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "32768")
        # Even a per-call default is overridden by the env knob.
        assert resolve_max_output_tokens() == 32768
        assert resolve_max_output_tokens(8192) == 32768

    def test_invalid_env_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "not-a-number")
        assert resolve_max_output_tokens() == 65536
        assert resolve_max_output_tokens(4096) == 4096

    def test_non_positive_env_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for bad in ("0", "-100"):
            monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", bad)
            assert resolve_max_output_tokens() == 65536

    def test_blank_env_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_MAX_OUTPUT_TOKENS", "   ")
        assert resolve_max_output_tokens() == 65536
