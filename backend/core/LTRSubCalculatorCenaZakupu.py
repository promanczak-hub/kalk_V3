from dataclasses import dataclass
from typing import List


@dataclass
class PurchasePriceOption:
    price_net: float
    name: str = ""
    is_service: bool = False
    is_discountable: bool = True


@dataclass
class PurchasePriceInput:
    base_price_net: float
    options: List[PurchasePriceOption]
    discount_pct: float
    add_gsm_device: bool
    gsm_hardware_cost: float


@dataclass
class PurchasePriceResult:
    total_capex: float
    discounted_base: float
    total_discount_amount: float
    total_options_capex: float
    discountable_options_total: float
    non_discountable_options_total: float


class PurchasePriceCalculator:
    def __init__(self, data: PurchasePriceInput):
        self.data = data

    def calculate(self) -> PurchasePriceResult:
        # 1. Discount Factor Calculation
        # Assuming discount_pct is a percentage between 0 and 100
        discount_factor = 1.0 - (self.data.discount_pct / 100.0)

        # 2. Discount the base price
        discounted_base = self.data.base_price_net * discount_factor

        # 3. Separate discountable and non-discountable options (ignoring services)
        discountable_opts = sum(
            opt.price_net
            for opt in self.data.options
            if not opt.is_service and opt.is_discountable
        )
        non_discountable_opts = sum(
            opt.price_net
            for opt in self.data.options
            if not opt.is_service and not opt.is_discountable
        )

        # 4. Total CAPEX calculation
        total_capex = (
            discounted_base
            + (discountable_opts * discount_factor)
            + non_discountable_opts
        )

        # 5. GSM Capitalization
        if self.data.add_gsm_device:
            total_capex += self.data.gsm_hardware_cost

        # 6. Aggregate metadata
        total_discount_amount = (self.data.base_price_net - discounted_base) + (
            discountable_opts - (discountable_opts * discount_factor)
        )
        total_options_capex = discountable_opts + non_discountable_opts

        return PurchasePriceResult(
            total_capex=total_capex,
            discounted_base=discounted_base,
            total_discount_amount=total_discount_amount,
            total_options_capex=total_options_capex,
            discountable_options_total=discountable_opts,
            non_discountable_options_total=non_discountable_opts,
        )
