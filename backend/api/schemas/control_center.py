from typing import Optional
from pydantic import BaseModel


class TyreCost(BaseModel):
    id: Optional[str] = None
    tyre_class: str
    diameter: int
    purchase_price: float
    buyback_price: float


class ServiceRate(BaseModel):
    id: Optional[int] = None
    klasa_id: int
    rodzaj_paliwa: str
    stawka_za_km: float


class ServiceBaseCost(BaseModel):
    id: Optional[int] = None
    klasa_id: int
    koszt_przegladu_podstawowego: float


class EngineType(BaseModel):
    id: Optional[int] = None
    name: str
    category: str
    description: Optional[str] = None


class SamarClass(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    mileage_cutoff_threshold: Optional[int] = None
    example_models: Optional[str] = None
    excel_code: Optional[str] = None
    category: Optional[str] = None
    size_class: Optional[str] = None


class SamarServiceCost(BaseModel):
    id: Optional[str] = None
    samar_class_id: int
    engine_type_id: int
    power_band: str
    cost_aso_per_km: float
    cost_non_aso_per_km: float


class ReplacementCarRate(BaseModel):
    id: Optional[str] = None
    samar_class_id: int
    samar_class_name: str = ""
    average_days_per_year: float = 6.5
    daily_rate_net: float


class BrandCorrection(BaseModel):
    id: Optional[int] = None
    samar_class_id: int
    rodzaj_paliwa: int
    brand_name: str
    model_name: Optional[str] = None
    korekta_procent: float = 0.0
    notes: Optional[str] = None


class DepreciationRate(BaseModel):
    id: Optional[int] = None
    samar_class_id: int
    fuel_type_id: int  # references engines.id (1:1)
    year: int
    base_depreciation_percent: float = 0.0
    options_depreciation_percent: float = 0.0


class MileageCorrection(BaseModel):
    id: Optional[int] = None
    samar_class_id: int
    fuel_type_id: int  # references engines.id (1:1)
    under_threshold_percent: float = 0.0
    over_threshold_percent: float = 0.0


class BodyType(BaseModel):
    id: Optional[int] = None
    name: str
    vehicle_class: str  # "Osobowy" / "Dostawczy"
    description: Optional[str] = None


class BodyCorrection(BaseModel):
    id: Optional[int] = None
    samar_class_id: int
    brand_name: Optional[str] = None
    body_type_id: Optional[int] = None
    engine_type_id: Optional[int] = None
    correction_percent: float = 0.0
    zabudowa_correction_percent: float = 0.0


class ZabudowaType(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    excel_code: Optional[str] = None


class ZabudowaCorrection(BaseModel):
    id: Optional[int] = None
    samar_class_id: Optional[int] = None
    zabudowa_type_id: Optional[int] = None
    correction_percent: float = 0.0


class PaintType(BaseModel):
    id: Optional[int] = None
    name: str = ""
    wr_correction: float = 0.0


class VintageCorrection(BaseModel):
    id: Optional[int] = None
    rocznik: str = ""
    korekta_procent: float = 0.0
