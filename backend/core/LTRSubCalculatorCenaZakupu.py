from dataclasses import dataclass, field
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
    # Opony — pierwszy komplet wchodzi do CAPEX (V1 L65, L71)
    tires_capex_net: float = 0.0
    # GSM — urządzenie + montaż wchodzi do CAPEX (V1 L117-124)
    add_gsm_to_capex: bool = False
    gsm_device_cost_net: float = 0.0  # CenaUrzadzeniaGSM = 469
    gsm_installation_cost_net: float = 0.0  # MontazUrzadzeniaGSM = 150
    # Opłata transportowa — per kalkulacja, default 0 (V1: per marka)
    transport_fee_net: float = 0.0
    # Pakiet serwisowy
    pakiet_serwisowy_net: float = 0.0


@dataclass
class PurchasePriceResult:
    total_capex: float
    discounted_base: float
    total_discount_amount: float
    total_options_capex: float
    discountable_options_total: float
    non_discountable_options_total: float
    total_service_options: float = 0.0
    pakiet_serwisowy_net: float = 0.0
    tires_capex_net: float = 0.0
    gsm_capex_net: float = 0.0
    transport_fee_net: float = 0.0


class PurchasePriceCalculator:
    def __init__(self, data: PurchasePriceInput):
        self.data = data

    def calculate(self) -> PurchasePriceResult:
        # 1. Discount Factor
        discount_factor = 1.0 - (self.data.discount_pct / 100.0)

        # 2. Base price after discount
        discounted_base = self.data.base_price_net * discount_factor

        # 3. Factory options — discountable
        discountable_opts = sum(
            opt.price_net
            for opt in self.data.options
            if not opt.is_service and opt.is_discountable
        )
        # 4. Factory options — non-discountable
        non_discountable_opts = sum(
            opt.price_net
            for opt in self.data.options
            if not opt.is_service and not opt.is_discountable
        )

        # 5. Service options — always non-discountable (V1 parity)
        service_opts_total = sum(
            opt.price_net for opt in self.data.options if opt.is_service
        )

        # 6. Total CAPEX = discounted base + options + extras
        total_capex = (
            discounted_base
            + (discountable_opts * discount_factor)
            + non_discountable_opts
            + service_opts_total
            + self.data.pakiet_serwisowy_net
            + self.data.transport_fee_net  # V1: opłata transportowa
            + self.data.tires_capex_net  # V1: 1 komplet opon netto
        )

        # 7. GSM capitalization (V1 L117-124: urządzenie + montaż)
        gsm_capex = 0.0
        if self.data.add_gsm_to_capex:
            gsm_capex = (
                self.data.gsm_device_cost_net + self.data.gsm_installation_cost_net
            )
            total_capex += gsm_capex

        # 8. Discount metadata
        total_discount_amount = (self.data.base_price_net - discounted_base) + (
            discountable_opts - (discountable_opts * discount_factor)
        )
        total_options_capex = (
            discountable_opts + non_discountable_opts + service_opts_total
        )

        return PurchasePriceResult(
            total_capex=total_capex,
            discounted_base=discounted_base,
            total_discount_amount=total_discount_amount,
            total_options_capex=total_options_capex,
            discountable_options_total=discountable_opts,
            non_discountable_options_total=non_discountable_opts,
            total_service_options=service_opts_total,
            pakiet_serwisowy_net=self.data.pakiet_serwisowy_net,
            tires_capex_net=self.data.tires_capex_net,
            gsm_capex_net=gsm_capex,
            transport_fee_net=self.data.transport_fee_net,
        )
