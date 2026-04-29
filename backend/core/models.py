from typing import Optional
from pydantic import BaseModel, Field


class ControlCenterSettings(BaseModel):
    default_wibor: float
    default_ltr_margin: float
    vat_rate: float
    bank_spread: float
    samar_segment_b_adjustment: int
    samar_segment_c_adjustment: int
    samar_segment_d_adjustment: int
    value_threshold_1: float
    value_threshold_2: float
    resale_time_days: int
    samar_rv_apply_color_correction: bool
    samar_rv_apply_body_correction: bool
    samar_rv_apply_options_depreciation: bool
    samar_rv_base_mileage: int
    samar_rv_mileage_unit_km: int

    # Parametry ubezpieczeń V1 (Szkoda)
    ins_avg_damage_value: float
    ins_avg_damage_mileage: int
    ins_nnw_annual_rate: float
    ins_ass_annual_rate: float
    ins_green_card_annual_rate: float

    # Koszty Dodatkowe
    cost_gsm_subscription_monthly: float
    cost_gsm_device: float
    cost_gsm_installation: float
    gsm_amortization_years: float = 4.0
    cost_hook_installation: float
    cost_grid_dismantling: float
    cost_registration: float
    cost_sales_prep: float
    cost_transport: float = 0.0

    # Normatywny przebieg floty (floor dla kosztu serwisu)
    normatywny_przebieg_mc: int = 1666  # km/mc (ok. 20 000 km/rok)

    # Współczynnik WR dla ceny sprzedaży LO: WRdlaLO = WR × (1 + lo_param)
    przewidywana_cena_sprzedazy_lo: float = 0.15
    budzet_marketingowy_ltr: float = 0.0
    last_settings_update: str = ""  # ISO datetime from DB


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
