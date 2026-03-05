"""
Centralized price string parser for Polish vehicle documents.

Handles formats like:
  "295 700 PLN brutto"
  "120.500,00 PLN netto"
  "5.476 PLN"
  "180000"
  "Brak"
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedPrice:
    """Immutable result of parsing a price string."""

    value: float
    currency: str
    tax_type: str  # "netto" | "brutto" | "unknown"

    @property
    def value_net(self) -> float:
        """Return net value (divide by 1.23 if brutto)."""
        if self.tax_type == "brutto":
            return round(self.value / 1.23, 2)
        return self.value

    @property
    def value_gross(self) -> float:
        """Return gross value (multiply by 1.23 if netto)."""
        if self.tax_type == "netto":
            return round(self.value * 1.23, 2)
        return self.value


# Regex: optional sign, digits with optional space/dot/comma separators
_PRICE_PATTERN = re.compile(r"(-?\s*[\d][\d\s.,]*\d|\d)", re.UNICODE)

_EMPTY_VALUES = frozenset(
    {
        "",
        "brak",
        "none",
        "null",
        "n/a",
        "-",
        "—",
        "0",
    }
)


def parse_price_string(raw: str | None) -> ParsedPrice | None:
    """
    Parse a Polish price string into a structured ParsedPrice.

    Handles thousands separators (dots and spaces),
    decimal commas, and tax type detection.

    Returns None if the string is empty or unparseable.
    """
    if raw is None:
        return None

    text = str(raw).strip()
    if text.lower() in _EMPTY_VALUES:
        return None

    # Detect tax type
    lower = text.lower()
    tax_type = _detect_tax_type(lower)

    # Detect currency
    currency = _detect_currency(text)

    # Extract numeric part
    numeric_value = _extract_numeric_value(text)
    if numeric_value is None or numeric_value <= 0:
        return None

    return ParsedPrice(
        value=numeric_value,
        currency=currency,
        tax_type=tax_type,
    )


def _detect_tax_type(lower_text: str) -> str:
    """Detect netto/brutto from text context."""
    if "netto" in lower_text:
        return "netto"
    if "brutto" in lower_text:
        return "brutto"
    return "unknown"


def _detect_currency(text: str) -> str:
    """Detect currency code from text."""
    upper = text.upper()
    if "EUR" in upper:
        return "EUR"
    if "USD" in upper:
        return "USD"
    return "PLN"


def _extract_numeric_value(text: str) -> float | None:
    """
    Extract a numeric value from a noisy price string.

    Strategy:
    1. Find all digit groups with separators
    2. Determine if dots/commas are thousands or decimal separators
    3. Parse to float

    Examples:
        "295 700"      → 295700.0
        "120.500,00"   → 120500.0
        "5.476"        → 5476.0  (dot as thousands sep in Polish)
        "1 234.56"     → 1234.56
        "180000"       → 180000.0
    """
    match = _PRICE_PATTERN.search(text)
    if not match:
        return None

    num_str = match.group(0).strip()
    # Remove spaces used as thousands separators
    num_str = num_str.replace(" ", "")

    return _parse_numeric_string(num_str)


def _parse_numeric_string(num_str: str) -> float | None:
    """
    Parse a numeric string handling Polish number formatting.

    Polish convention:
      - dot (.) = thousands separator
      - comma (,) = decimal separator
    International convention:
      - comma (,) = thousands separator
      - dot (.) = decimal separator

    Heuristic: if string has a dot followed by exactly 3 digits
    at the end (and no comma), treat dot as thousands separator.
    """
    has_dot = "." in num_str
    has_comma = "," in num_str

    if has_dot and has_comma:
        # Both present: determine which is decimal
        dot_pos = num_str.rfind(".")
        comma_pos = num_str.rfind(",")

        if comma_pos > dot_pos:
            # Polish: 120.500,00 → dots=thousands, comma=decimal
            num_str = num_str.replace(".", "").replace(",", ".")
        else:
            # International: 120,500.00 → commas=thousands, dot=decimal
            num_str = num_str.replace(",", "")

    elif has_comma and not has_dot:
        # Comma only: check if it's decimal or thousands
        parts = num_str.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Decimal: "1234,50" → 1234.50
            num_str = num_str.replace(",", ".")
        else:
            # Thousands: "1,234,567" → 1234567
            num_str = num_str.replace(",", "")

    elif has_dot and not has_comma:
        # Dot only: use Polish heuristic
        parts = num_str.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            # Polish thousands: "5.476" → 5476
            num_str = num_str.replace(".", "")
        elif len(parts) > 2:
            # Multiple dots = thousands: "1.234.567" → 1234567
            num_str = num_str.replace(".", "")
        # else: single dot with ≠3 decimals → treat as decimal point

    try:
        return float(num_str)
    except ValueError:
        return None
