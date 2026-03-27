from typing import Optional
from pydantic import BaseModel, Field


class VehicleDataDTO(BaseModel):
    model_config = {
        "extra": "allow"
    }  # Temporarily allow extra fields for seamless migration
    id: str = Field(..., description="Unikalny identyfikator pojazdu")
    brand: str = Field(..., description="Marka pojazdu")
    model: str = Field(..., description="Model pojazdu")
    Segment: Optional[str] = Field(None, description="Segment SAMAR, np. Premium-Sport")
    engine_type_id: int = Field(..., description="Kategoria silnika (id)")
    samar_class_id: int = Field(..., description="Identyfikator klasy SAMAR")
    zabudowa_type_id: Optional[int] = Field(
        None, description="Identyfikator rodzaju zabudowy"
    )
    zabudowa_apr_wr: Optional[bool] = Field(
        None, description="Czy zabudowa ma znaczenie w procesie RV"
    )
    power_kw: Optional[float] = Field(None, description="Moc pojazdu w kilowatach")
    rocznik: Optional[int | str] = Field(None, description="Rocznik pojazdu")
    is_metalic: Optional[bool] = Field(None, description="Czy lakier jest metalizowany")
    paint_type_id: Optional[int] = Field(None, description="ID typu lakieru")
    body_type_id: Optional[int] = Field(None, description="ID typu nadwozia")
    body_type_name: Optional[str] = Field(
        None, description="Nazwa nadwozia bezpośrednio z wyciągu"
    )
    drive_type: Optional[str] = Field(None, description="Rodzaj napędu (np. AWD, RWD)")


class SamarClassDTO(BaseModel):
    model_config = {"extra": "allow"}
    id: int = Field(..., description="Identyfikator klasy")
    klasa_nazwa: str = Field(..., description="Nazwa klasy (np. C, Premium-Sport)")
    rv_base_period_months: int = Field(..., description="Bazowy okres referencyjny RV")
    rv_base_mileage_km: int = Field(..., description="Bazowy przebieg referencyjny RV")


class LTRPipelineInputDTO(BaseModel):
    """
    W pełni otypowany wsad danych dla obiektu LTRKalkulator.
    Musi zrzeszać dane pobrane z Supabase przed rozpoczęciem 12-etapowej kalkulacji,
    omijając generyczne słowniki 'dict'.
    """

    vehicle: VehicleDataDTO
    samar_class: SamarClassDTO
    # Przestrzeń do ekspansji o modele stawkowe (ubezpieczenie, opony) w kolejnych krokach
