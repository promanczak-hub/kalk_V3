from dataclasses import dataclass, field
from typing import List, Any


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
    CenaZakupu: float = 0.0
    CenaZakupuBezOpon: float = 0.0
    CenaZakupuBezOponIOpcjiSerwisowych: float = 0.0
    CenaZakupuBezOponIOpcjiSerwisowychIPakietu: float = 0.0
    RabatKwotowo: float = 0.0
    trace: list[dict[str, Any]] = field(default_factory=list)


class PurchasePriceCalculator:
    def __init__(self, data: PurchasePriceInput):
        self.data = data

    def calculate(self) -> PurchasePriceResult:
        trace: list[dict[str, Any]] = []
        
        # 1. Discount Factor
        discount_factor = 1.0 - (self.data.discount_pct / 100.0)

        # 2. Base price after discount
        discounted_base = self.data.base_price_net * discount_factor
        trace.append({
            "krok": "Cena Zakupu: Cena Bazowa",
            "rownanie": f"Baza {self.data.base_price_net:.2f} * (1 - Rabat {self.data.discount_pct:.2f}%)",
            "wynik": discounted_base
        })

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
        
        trace.append({
            "krok": "Cena Zakupu: Opcje i Wyposażenie",
            "rownanie": f"Opcje Rabatowalne {discountable_opts:.2f} + Nierabatowalne {non_discountable_opts:.2f} + Serwisowe {service_opts_total:.2f}",
            "wynik": discountable_opts + non_discountable_opts + service_opts_total
        })

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

        trace.append({
            "krok": "Cena Zakupu: Ekstrasy (Transport, Pakiet, Opony)",
            "rownanie": f"Transport {self.data.transport_fee_net:.2f} + PakietS {self.data.pakiet_serwisowy_net:.2f} + 1-komplet Opon {self.data.tires_capex_net:.2f}",
            "wynik": self.data.transport_fee_net + self.data.pakiet_serwisowy_net + self.data.tires_capex_net
        })

        # 7. GSM capitalization (V1 L117-124: urządzenie + montaż)
        gsm_capex = 0.0
        if self.data.add_gsm_to_capex:
            gsm_capex = (
                self.data.gsm_device_cost_net + self.data.gsm_installation_cost_net
            )
            total_capex += gsm_capex
            trace.append({
                "krok": "Cena Zakupu: Kapitalizacja GSM",
                "rownanie": f"Urządzenie {self.data.gsm_device_cost_net:.2f} + Montaż {self.data.gsm_installation_cost_net:.2f}",
                "wynik": gsm_capex
            })

        trace.append({
            "krok": "Cena Zakupu: CAPEX Całkowity",
            "rownanie": "Suma (BazaPoRabacie + OpcjeRabatowane + OpcjeNierab + OpcjeSerw + PakietS + Transport + Opony + GSM)",
            "wynik": total_capex
        })

        # 8. Discount metadata
        total_discount_amount = (self.data.base_price_net - discounted_base) + (
            discountable_opts - (discountable_opts * discount_factor)
        )
        total_options_capex = (
            discountable_opts + non_discountable_opts + service_opts_total
        )

        cena_zakupu_bez_opon = total_capex - self.data.tires_capex_net
        cena_zakupu_bez_opon_i_opcji_serw = cena_zakupu_bez_opon - service_opts_total
        cena_zakupu_bez_opon_i_opcji_serw_i_pakietu = cena_zakupu_bez_opon_i_opcji_serw - self.data.pakiet_serwisowy_net

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
            CenaZakupu=total_capex,
            CenaZakupuBezOpon=cena_zakupu_bez_opon,
            CenaZakupuBezOponIOpcjiSerwisowych=cena_zakupu_bez_opon_i_opcji_serw,
            CenaZakupuBezOponIOpcjiSerwisowychIPakietu=cena_zakupu_bez_opon_i_opcji_serw_i_pakietu,
            RabatKwotowo=total_discount_amount,
            trace=trace,
        )
