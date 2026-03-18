from pydantic import BaseModel, Field


class PricingComponent(BaseModel):
    label: str = Field(..., description="Nazwa składowej, np. 'Cena katalogowa'")
    amount_net: float = Field(..., description="Kwota netto składowej")
    no_discount: bool = Field(
        default=False,
        description="Czy składowa jest wyłączona z rabatu (non-discountable)",
    )


class PricingPatch(BaseModel):
    components: list[PricingComponent] = Field(
        ..., description="Lista edytowalnych składowych cenowych"
    )
    discount_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Rabat procentowy (0–100)"
    )


class PricingResult(BaseModel):
    components: list[PricingComponent]
    discount_pct: float
    discountable_sum: float
    non_discountable_sum: float
    total_sum_net: float
    discount_amount: float
    purchase_price_net: float
    vat_amount: float
    purchase_price_gross: float
