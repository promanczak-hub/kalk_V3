"""Pydantic schemas for cross-reference LLM responses.

Shared by cross_ref_llm and cross_ref_evidence modules.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MatchedFeature(BaseModel):
    """Single feature extracted from matched variant."""

    feature_key: str = Field(
        description="Klucz cechy z universal_features (np. 'liczba_miejsc', "
        "'długość_przestrzeni_ładunkowej_w_mm', 'ilość_europalet')"
    )
    mapping_confidence: float = Field(
        description="Ocena w skali 0.0 - 1.0 jak bardzo nazwa cechy "
        "producenta odpowiada semantycznie wybranemu kluczowi 'feature_key'."
    )
    value_text: str | None = Field(None, description="Wartość tekstowa cechy")
    value_num: float | None = Field(None, description="Wartość numeryczna cechy")
    value_bool: bool | None = Field(None, description="Wartość boolean cechy")
    unit: str | None = Field(None, description="Jednostka (mm, kg, szt, m², m³)")


class VariantMatchResult(BaseModel):
    """LLM output: matched variant + extracted features."""

    matched_variant_name: str = Field(
        description="Nazwa dopasowanego wariantu z katalogu "
        "(np. 'L3H3 FWD 177KM', 'Ducato 35 MH2 3.0')"
    )
    confidence: float = Field(description="Pewność dopasowania 0.0-1.0")
    reasoning: str = Field(
        description="Krótkie uzasadnienie dopasowania (1-2 zdania)"
    )
    features: list[MatchedFeature] = Field(
        default_factory=list,
        description="Lista cech wyekstrahowanych z dopasowanego wariantu",
    )


class CatalogRanking(BaseModel):
    """Single catalog ranking."""

    catalog_id: str = Field(description="ID dopasowanego katalogu")
    relevance_score: float = Field(description="Ocena dopasowania 0.0-1.0")
    reasoning: str = Field(
        description="Krótkie uzasadnienie, dlaczego ten dokument pasuje"
    )


class CatalogRankingResult(BaseModel):
    """List of ranked catalogs."""

    rankings: list[CatalogRanking] = Field(
        description="Lista katalogów posortowana od najbardziej "
        "do najmniej pasującego",
    )


class CrossRefLLMError(Exception):
    """Raised when LLM infrastructure fails (not a match result)."""
