"""Reverse Search LLM extraction — response schema.

The system prompt itself is now built dynamically from the live catalog
(see `core.reverse_search_prompt.build_reverse_search_prompt`). The static
202-feature list previously hard-coded here was stale and incomplete (DB has
330 features). Source of truth is `reverse_search.universal_features`,
synced from Google Sheet 'cechy' via `scripts/mdm_sync.py`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedFeature(BaseModel):
    """One feature requirement extracted from a customer query.

    The combination of `feature_type` (looked up in the catalog) and the
    populated value field determines how the requirement is filtered:

    - boolean → value_bool
    - numeric → value_num + op (gte/lte/eq)
    - text/enum → value_text
    """

    feature_key: str = Field(
        description=(
            "Klucz cechy z katalogu (musi pasować 1:1 do listy w prompcie). "
            "Klucze spoza katalogu zostaną odrzucone przez backend."
        ),
    )
    op: Literal["eq", "gte", "lte", "in"] = Field(
        default="eq",
        description=(
            "Operator porównania. Dla cech boolean zawsze 'eq'. "
            "Dla numeric: 'gte' dla 'minimum/od', 'lte' dla 'do/max', 'eq' dla dokładnej wartości."
        ),
    )
    value_bool: bool | None = Field(
        default=None,
        description=(
            "Tylko dla cech feature_type=boolean. Ustaw True gdy klient jawnie wymaga "
            "tej cechy. Nie używaj False — brak wymagania = pomiń całą cechę."
        ),
    )
    value_num: float | None = Field(
        default=None,
        description=(
            "Tylko dla cech feature_type=numeric. Wartość w canonical unit cechy "
            "(zob. [jednostka: ...] w katalogu). Konwertuj wejście klienta jeśli trzeba."
        ),
    )
    value_text: str | None = Field(
        default=None,
        description=(
            "Tylko dla cech feature_type=text|enum. Dla enum: użyj jednej z dozwolonych "
            "wartości jeśli katalog je podaje, inaczej zachowaj sformułowanie klienta."
        ),
    )


class ExtractedReverseSearchFeatures(BaseModel):
    features: list[ExtractedFeature] = Field(
        default_factory=list,
        description=(
            "Lista wymagań klienta zmapowanych na klucze z katalogu. Pusta lista jeśli "
            "nic konkretnego nie zostało wymagane."
        ),
    )
    price_max: int | None = Field(
        default=None,
        description="Maksymalna miesięczna rata netto w PLN (np. 'rata do 2500'). Brak → null.",
    )
    duration_months: int | None = Field(
        default=None,
        description="Czas trwania leasingu w miesiącach (np. '4 lata' → 48). Brak → null.",
    )
    annual_mileage: int | None = Field(
        default=None,
        description=(
            "Roczny limit kilometrów (np. '30 tys' → 30000). Jeśli klient poda limit na "
            "cały okres (np. '160 tys / 4 lata'), oblicz roczny (160000/4 = 40000). Brak → null."
        ),
    )
    transcript: str | None = Field(
        default=None,
        description=(
            "Dosłowna transkrypcja po polsku, jeśli wejściem jest audio. "
            "Dla wejścia tekstowego pozostaw null."
        ),
    )
