from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GridVariant(BaseModel):
    months: List[int] = Field(
        default=[24, 36, 48, 60], description="Lista miesięcy kontraktu"
    )
    km_per_year: List[int] = Field(
        default=[10000, 20000, 30000, 40000, 50000, 60000],
        description="Opcje przebiegów rocznych",
    )


class CalculationSettings(BaseModel):
    settings_version_id: Optional[str] = Field(
        None, description="Id aktywnej wersji ustawień w DB"
    )
    overrides: Optional[Dict[str, Any]] = Field(
        None, description="Słownik nadpisań Manager'a dla wyceny (Calculation Override)"
    )


class VehicleOptions(BaseModel):
    name: str
    price_net: float
    price_gross: float
    no_discount: bool = False
    include_in_wr: bool = False


class CalculatorInput(BaseModel):
    calculation_id: Optional[str] = None
    vehicle_id: str = Field(..., description="ID Auta ze słownika Supabase / SAMAR")
    base_price_net: float = Field(
        ..., description="Cena cennikowa netto wybranego pojazdu"
    )
    discount_pct: float = Field(default=0.0, description="Rabat jako procent")
    factory_options: List[VehicleOptions] = Field(default_factory=list)
    service_options: List[VehicleOptions] = Field(default_factory=list)
    # Parametry bazowe (Siatka Dynamiczna V3)
    okres_bazowy: int = Field(
        default=48, description="Domyślny/bazowy okres w miesiącach z Card Summary"
    )
    przebieg_bazowy: int = Field(
        default=140000, description="Domyślny/bazowy przebieg z Card Summary"
    )

    pricing_margin_pct: float = Field(
        default=15.0, description="Marża sprzedaży % z poziomu UI (preset/suwak)"
    )
    settings: CalculationSettings = Field(
        default_factory=lambda: CalculationSettings(
            settings_version_id=None, overrides=None
        )
    )
    # Flagi dla logiki opon:
    z_oponami: bool = Field(default=True, description="Czy z oponami")
    klasa_opony_string: str = Field(
        default="Medium", description="Klasa Opon np. 'WIELOSEZONOWE MEDIUM'"
    )
    odkup_opon_enabled: bool = Field(
        default=False,
        description="Włącz logikę obniżenia kosztów przez odkup opon (V1)",
    )
    korekta_kosztu_opon: bool = Field(
        default=False, description="Czy stosować ręczną korektę"
    )
    koszt_opon_korekta: float = Field(default=0.0, description="Kwota korekty brutto")
    liczba_kompletow_opon: Optional[float] = Field(
        default=None, description="Ręczna liczba kompletów (opcjonalna)"
    )
    srednica_felgi: Optional[int] = Field(
        default=None,
        description="Średnica felgi w calach (z plakietki pojazdu). Wymagana gdy z_oponami=True.",
    )

    # Podatki i Finanse (PMT)
    wibor_pct: float = Field(default=5.0, description="WIBOR %")
    margin_pct: float = Field(default=2.0, description="Marża Finansowa Leasingu %")
    depreciation_pct: Optional[float] = Field(
        default=None,
        description="Procent amortyzacji przekazany z UI (nadpisuje dynamikę SAMAR)",
    )
    manual_wr_correction: float = Field(
        default=0.0,
        description="Ręczna korekta kwotowa (netto) Wartości Rezydualnej przekazywana z UI",
    )
    initial_deposit_pct: float = Field(
        default=0.0, description="Oplata Wstępna (Czynsz Inicjalny) % z ceny auta"
    )

    # Samochód Zastępczy
    replacement_car_enabled: bool = Field(
        default=True, description="Czy wliczać koszty auta zastępczego"
    )

    # Koszty Dodatkowe
    add_gsm_subscription: bool = Field(default=True, description="Abonament GSM")
    add_hook_installation: bool = Field(default=False, description="Montaż Haka")
    add_grid_dismantling: bool = Field(default=False, description="Wymontowanie Kraty")
    add_registration: bool = Field(default=True, description="Rejestracja")
    add_sales_prep: bool = Field(default=True, description="Przygotowanie do sprzedaży")
    korekta_kosztu_przygotowania: float = Field(
        default=0.0,
        description="Ręczna korekta kosztu przygotowania do sprzedaży (netto)",
    )

    # Nowe pola V1→V3
    service_cost_type: str = Field(
        default="ASO",
        description="Rodzaj kosztow serwisowych: 'ASO' lub 'nonASO'",
    )
    include_servicing: bool = Field(
        default=True,
        description="Czy uwzgledniac serwisowanie (V1: CzyUwzgledniaSerwisowanie)",
    )
    samar_category: Optional[str] = Field(
        default=None, description="Nazwa klasy SAMAR z dropdownu/UI (opcjonalnie)"
    )
    engine_name: Optional[str] = Field(
        default=None, description="Nazwa silnika z dropdownu/UI (opcjonalnie)"
    )
    body_type_name: Optional[str] = Field(
        default=None, description="Nazwa nadwozia z dropdownu/UI (opcjonalnie)"
    )
    drive_type: Optional[str] = Field(
        default=None, description="Typ napedu z dropdownu/UI (opcjonalnie)"
    )
    paint_type_name: Optional[str] = Field(
        default=None, description="Nazwa typu lakieru z dropdownu/UI (opcjonalnie)"
    )
    zabudowa_type_id: Optional[int] = Field(
        default=None,
        description="ID typu zabudowy z Control Center (opcjonalnie - legacy, mapowane jako body_type_id)",
    )
    power_kw: Optional[float] = Field(
        default=None, description="Moc silnika (kW) przesyłana wprost z UI"
    )
    power_hp: Optional[float] = Field(
        default=None, description="Moc silnika (KM) przesyłana wprost z UI"
    )
    pakiet_serwisowy: float = Field(
        default=0.0,
        description=(
            "Dedykowany pakiet serwisowy netto na kontrakt. "
            "Jeśli > 0, zastępuje logikę km-ową."
        ),
    )
    inne_koszty_serwisowania_netto: float = Field(
        default=0.0,
        description="Dodatkowe koszty serwisowania netto MIESIĘCZNIE.",
    )
    vehicle_vintage: str = Field(
        default="current",
        description="Rocznik pojazdu: 'current' (bieżący) lub 'previous' (ubiegły)",
    )
    is_metalic: bool = Field(
        default=False,
        description="Czy lakier metalik/perlowy (wplywa na korekte WR)",
    )

    matrix_km_mode: str = Field(
        default="annual",
        description="Tryb osi przebiegu matrycy: annual albo contract",
    )
    matrix_contract_km_step: int = Field(
        default=10000,
        description="Krok siatki przebiegu dla trybu contract (km/kontrakt)",
    )
