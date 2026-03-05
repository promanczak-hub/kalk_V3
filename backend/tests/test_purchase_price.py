import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.LTRSubCalculatorCenaZakupu import (
    PurchasePriceCalculator,
    PurchasePriceInput,
    PurchasePriceOption,
)


def test_purchase_price_base_no_options():
    input_data = PurchasePriceInput(
        base_price_net=100000.0,
        options=[],
        discount_pct=0.0,
        add_gsm_device=False,
        gsm_hardware_cost=0.0,
    )
    calc = PurchasePriceCalculator(input_data)
    result = calc.calculate()

    assert result.total_capex == 100000.0
    assert result.discounted_base == 100000.0
    assert result.total_discount_amount == 0.0


def test_purchase_price_with_discount_and_options():
    # 100k base, 5k discountable options, 10% discount
    options = [
        PurchasePriceOption(
            price_net=5000.0, is_service=False, is_discountable=True, name="Lakier"
        )
    ]
    input_data = PurchasePriceInput(
        base_price_net=100000.0,
        options=options,
        discount_pct=10.0,
        add_gsm_device=False,
        gsm_hardware_cost=0.0,
    )
    calc = PurchasePriceCalculator(input_data)
    result = calc.calculate()

    # Base: 100k * 0.9 = 90k
    # Options: 5k * 0.9 = 4.5k
    # Total CAPEX: 94.5k
    # Total Discount: 10k (base) + 500 (options) = 10.5k

    assert result.total_capex == 94500.0
    assert result.discounted_base == 90000.0
    assert result.total_discount_amount == 10500.0


def test_purchase_price_with_non_discountable_options():
    options = [
        PurchasePriceOption(
            price_net=5000.0, is_service=False, is_discountable=True, name="Lakier"
        ),
        PurchasePriceOption(
            price_net=2000.0, is_service=False, is_discountable=False, name="Dywaniki"
        ),
    ]
    input_data = PurchasePriceInput(
        base_price_net=100000.0,
        options=options,
        discount_pct=10.0,
        add_gsm_device=False,
        gsm_hardware_cost=0.0,
    )
    calc = PurchasePriceCalculator(input_data)
    result = calc.calculate()

    # Base: 100k * 0.9 = 90k
    # Options Discountable: 5k * 0.9 = 4.5k
    # Options Non-Discountable: 2k
    # Total CAPEX: 90k + 4.5k + 2k = 96.5k
    # Total Discount: 10.5k

    assert result.total_capex == 96500.0
    assert result.discounted_base == 90000.0
    assert result.total_discount_amount == 10500.0


def test_purchase_price_service_options_included_no_discount():
    """Service options are included in CAPEX but NEVER discounted (V1 parity)."""
    options = [
        PurchasePriceOption(
            price_net=5000.0, is_service=False, is_discountable=True, name="Lakier"
        ),
        PurchasePriceOption(
            price_net=1000.0,
            is_service=True,
            is_discountable=True,  # ignored — service always non-discountable
            name="Pakiet Serwisowy",
        ),
    ]
    input_data = PurchasePriceInput(
        base_price_net=100000.0,
        options=options,
        discount_pct=10.0,
        add_gsm_device=False,
        gsm_hardware_cost=0.0,
    )
    calc = PurchasePriceCalculator(input_data)
    result = calc.calculate()

    # Base: 100k * 0.9 = 90k
    # Factory discountable: 5k * 0.9 = 4.5k
    # Service (always full): 1k
    # Total CAPEX: 90k + 4.5k + 1k = 95.5k
    assert result.total_capex == 95500.0
    assert result.total_service_options == 1000.0
    assert result.total_discount_amount == 10500.0  # only base + factory discounted


def test_purchase_price_with_gsm_device():
    input_data = PurchasePriceInput(
        base_price_net=100000.0,
        options=[],
        discount_pct=10.0,
        add_gsm_device=True,
        gsm_hardware_cost=469.0 + 150.0,  # Device + Install
    )
    calc = PurchasePriceCalculator(input_data)
    result = calc.calculate()

    # Base: 90k
    # GSM Cost: 619
    # Total: 90619.0
    assert result.total_capex == 90619.0
    assert result.discounted_base == 90000.0
    assert result.total_discount_amount == 10000.0


def test_purchase_price_with_pakiet_serwisowy():
    """Pakiet serwisowy is added to CAPEX without discount."""
    input_data = PurchasePriceInput(
        base_price_net=100000.0,
        options=[],
        discount_pct=10.0,
        add_gsm_device=False,
        gsm_hardware_cost=0.0,
        pakiet_serwisowy_net=3000.0,
    )
    calc = PurchasePriceCalculator(input_data)
    result = calc.calculate()

    # Base: 100k * 0.9 = 90k
    # Pakiet serwisowy: 3k (no discount)
    # Total CAPEX: 93k
    assert result.total_capex == 93000.0
    assert result.pakiet_serwisowy_net == 3000.0
    assert result.total_discount_amount == 10000.0


def test_purchase_price_full_scenario():
    """Full scenario: factory + service options + pakiet + GSM + discount."""
    options = [
        PurchasePriceOption(
            price_net=5000.0, is_service=False, is_discountable=True, name="Lakier"
        ),
        PurchasePriceOption(
            price_net=2000.0, is_service=False, is_discountable=False, name="Dywaniki"
        ),
        PurchasePriceOption(
            price_net=1500.0,
            is_service=True,
            is_discountable=False,
            name="Zabudowa Serwisowa",
        ),
    ]
    input_data = PurchasePriceInput(
        base_price_net=100000.0,
        options=options,
        discount_pct=10.0,
        add_gsm_device=True,
        gsm_hardware_cost=619.0,
        pakiet_serwisowy_net=2400.0,
    )
    calc = PurchasePriceCalculator(input_data)
    result = calc.calculate()

    # Base: 100k * 0.9 = 90k
    # Factory discountable: 5k * 0.9 = 4.5k
    # Factory non-discountable: 2k
    # Service (always full): 1.5k
    # Pakiet serwisowy: 2.4k
    # GSM: 619
    # Total: 90000 + 4500 + 2000 + 1500 + 2400 + 619 = 101019
    assert result.total_capex == 101019.0
    assert result.total_service_options == 1500.0
    assert result.pakiet_serwisowy_net == 2400.0
    assert result.total_options_capex == 8500.0  # 5k + 2k + 1.5k
    assert result.total_discount_amount == 10500.0
