from pydantic import BaseModel, Field
from typing import Optional, List


class MappedOption(BaseModel):
    name: str = Field(description="Nazwa opcji wyposażenia lub akcesorium")
    category: str = Field(
        "Fabryczna",
        description="Kategoria opcji (Fabryczna, Serwisowa itp.). Zazwyczaj Fabryczna.",
    )
    price_net: float = Field(
        description="Cena netto opcji w PLN. Jeśli to rabat na opcję, kwota ujemna."
    )


class MappedOffer(BaseModel):
    brand: str = Field(description="Marka pojazdu.")
    model: str = Field(description="Model pojazdu.")
    trim: Optional[str] = Field(
        None, description="Pełna linia wyposażenia lub typ nadwozia."
    )
    body_style: Optional[str] = Field(
        None, description="Wywnioskowany Typ Nadwozia (np. SUV, Hatchback, Kombi, VAN)."
    )
    segment: Optional[str] = Field(
        None,
        description="Wywnioskowany segment wielkościowy auta (np. A, B, C, D, E, F, M). Opcjonalny.",
    )
    samar_class_name: Optional[str] = Field(
        None,
        description="Zmapowana Nazwa Klasy SAMAR (Wypełniana automatycznie na backendzie, nie przez LLM).",
    )
    fuel_type: str = Field(
        description="Rodzaj paliwa wywnioskowany z opisu. Oczekiwane wartości ściśle z listy: "
        "'Benzyna (PB)', 'Diesel (ON)', 'Benzyna mHEV (PB-mHEV)', "
        "'Diesel mHEV (ON-mHEV)', 'Hybryda (HEV)', 'Hybryda Plug-in (PHEV)', "
        "'Elektryczny (BEV)', 'Wodór (FCEV)', 'Autogaz (LPG)'"
    )
    color: Optional[str] = Field(
        None, description="Surowa nazwa lakieru / koloru nadwozia wyciągnięta z oferty."
    )

    base_price_net: float = Field(
        description="Cena bazowa pojazdu netto według cennika."
    )
    factory_options: List[MappedOption] = Field(
        default_factory=list, description="Lista opcji fabrycznych."
    )
    dealer_options: List[MappedOption] = Field(
        default_factory=list, description="Lista opcji dealerskich/serwisowych."
    )

    discount_amount_net: Optional[float] = Field(
        0.0,
        description="Całkowita kwota udzielonego rabatu netto w PLN na samochód bazowy i opcje. 0.0, jeśli brak.",
    )
    discount_pct: Optional[float] = Field(
        0.0, description="Procent udzielonego rabatu na samochód. 0.0, jeśli brak."
    )

    tire_size: str = Field(
        description="Rozmiar kół wyciągnięty ze specyfikacji, np. 205/75 R16."
    )
    power_hp: Optional[int] = Field(
        None,
        description="Moc silnika w Koniach Mechanicznych (KM), o ile podana w ofercie.",
    )
    transmission: Optional[str] = Field(
        None, description="Rodzaj skrzyni biegów ('manualna' lub 'automatyczna')"
    )
    service_interval_km: Optional[int] = Field(
        None,
        description="Cykl przeglądowy, interwał serwisowy wyrażony w przebytych kilometrach (np. 30000). Ustala LLM na podstawie dokumentu lub wyszukiwania. None jeśli nieznany.",
    )
    service_interval_months: Optional[int] = Field(
        None,
        description="Cykl przeglądowy, interwał serwisowy wyrażony w miesiącach (np. 12 lub 24). Ustala LLM na podstawie dokumentu lub wyszukiwania. None jeśli nieznany.",
    )
