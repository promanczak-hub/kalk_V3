from pydantic import BaseModel, ConfigDict, Field


class Footnote(BaseModel):
    reference: str = Field(description="Oznaczenie przypisu, np. '*1', '(1)'")
    text: str = Field(description="Treść przypisu")


class TrimPricing(BaseModel):
    trim_name: str = Field(
        description="Nazwa wersji wyposażenia, np. Business, Elegance"
    )
    price_netto: float | None = Field(
        default=None, description="Cena netto auta w danej wersji wyposażenia"
    )
    price_brutto: float | None = Field(
        default=None, description="Cena brutto auta w danej wersji wyposażenia"
    )


class EngineVariant(BaseModel):
    engine_name: str = Field(description="Pełna nazwa silnika")
    transmission: str = Field(description="Skrzynia biegów")
    fuel_type: str = Field(description="Rodzaj paliwa")
    power_hp: int | None = Field(
        default=None, description="Moc w koniach mechanicznych (KM)"
    )
    prices_by_trim: list[TrimPricing] = Field(
        description="Ceny dla tego silnika z podziałem na wersje wyposażenia"
    )


class FeatureOption(BaseModel):
    code: str | None = Field(default=None, description="Kod opcji (jeśli istnieje)")
    name: str = Field(description="Nazwa opcji wyposażenia")
    price_netto: float | None = Field(default=None, description="Cena netto opcji")
    price_brutto: float | None = Field(default=None, description="Cena brutto opcji")
    availability_rules: str | None = Field(
        default=None,
        description="Zasady dostępności (np. wymaga, wyklucza, standard dla wersji X)",
    )
    applicable_trims: list[str] | None = Field(
        default=None,
        description="Wyposażenie dostępne w tych wersjach (- jeśli niedostępne)",
    )


class ParsedPriceList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    brand: str = Field(description="Marka pojazdu")
    model: str = Field(description="Model pojazdu")
    model_year: str | None = Field(
        default=None, description="Rok modelowy / produkcyjny"
    )
    valid_from: str | None = Field(default=None, description="Data ważności cennika")
    engines: list[EngineVariant] = Field(
        description="Lista wariantów silnikowych z cenami rożnych wersji"
    )
    features: list[FeatureOption] = Field(
        default_factory=list, description="Lista dostępnych opcji wyposażenia"
    )
    footnotes: list[Footnote] = Field(
        default_factory=list, description="Lista znalezionych przypisów w cenniku"
    )


class ExtractorPipelineResult(BaseModel):
    is_successful: bool
    error_message: str | None = Field(default=None)
    parsed_data: ParsedPriceList | None = Field(default=None)
    raw_markdown: str | None = Field(default=None)
