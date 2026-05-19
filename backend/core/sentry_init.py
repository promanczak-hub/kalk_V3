"""Sentry initialisation for kalk_v3 backend.

Imported once from `main.py` BEFORE the FastAPI app is created. No-op when
`SENTRY_DSN` env var is missing, so dev runs unaffected.

Coverage: FastAPI requests, Celery tasks, unhandled exceptions, structured
log breadcrumbs (INFO+). Sensitive PII (request bodies, query params, headers)
is scrubbed by `send_default_pii=False` plus the explicit `before_send` hook.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """Initialise Sentry SDK. Returns True if active, False if skipped."""
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        logger.info("Sentry: SENTRY_DSN not set, skipping init")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError as exc:
        logger.warning("Sentry: sentry-sdk not installed (%s), skipping init", exc)
        return False

    environment = os.environ.get("SENTRY_ENVIRONMENT", "development")
    release = os.environ.get("SENTRY_RELEASE")  # set by CI from git SHA
    traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.05"))
    profiles_sample_rate = float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.0"))

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            CeleryIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        send_default_pii=False,  # never auto-attach IP / auth headers
        attach_stacktrace=True,
        before_send=_before_send,
        before_breadcrumb=_before_breadcrumb,
    )

    logger.info(
        "Sentry initialised — env=%s release=%s traces=%.2f profiles=%.2f",
        environment,
        release or "(unset)",
        traces_sample_rate,
        profiles_sample_rate,
    )
    return True


# Field-name fragments that, if present in a string, get scrubbed.
_SENSITIVE_KEYS = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "apikey",
    "service_role",
    "supabase_jwt",
    "cookie",
)


def _scrub(value: Any) -> Any:
    """Recursively redact sensitive keys/values in dict and list payloads."""
    if isinstance(value, dict):
        return {
            k: ("***REDACTED***" if _is_sensitive(k) else _scrub(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def _is_sensitive(key: str) -> bool:
    key_l = key.lower()
    return any(marker in key_l for marker in _SENSITIVE_KEYS)


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Strip secrets before the event leaves the process."""
    if "request" in event and isinstance(event["request"], dict):
        req = event["request"]
        # Always drop request body — calculation payloads can contain prices,
        # vehicle data, and other operational info we don't want in Sentry.
        if "data" in req:
            req["data"] = "***REDACTED:request-body***"
        if "headers" in req and isinstance(req["headers"], dict):
            req["headers"] = _scrub(req["headers"])
        if "query_string" in req and isinstance(req["query_string"], str):
            # Don't ship query params verbatim — they may include vehicle_id /
            # offer_number that aren't PII but are operationally sensitive.
            req["query_string"] = "***REDACTED:query***"
    if "extra" in event and isinstance(event["extra"], dict):
        event["extra"] = _scrub(event["extra"])
    if "contexts" in event and isinstance(event["contexts"], dict):
        event["contexts"] = _scrub(event["contexts"])
    return event


def _before_breadcrumb(
    breadcrumb: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any] | None:
    """Scrub log breadcrumbs so debug INFO entries don't leak data."""
    if "data" in breadcrumb and isinstance(breadcrumb["data"], dict):
        breadcrumb["data"] = _scrub(breadcrumb["data"])
    return breadcrumb
