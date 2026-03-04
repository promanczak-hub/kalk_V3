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


def test_purchase_price_with_service_options_ignored():
    options = [
        PurchasePriceOption(
            price_net=5000.0, is_service=False, is_discountable=True, name="Lakier"
        ),
        PurchasePriceOption(
            price_net=1000.0,
            is_service=True,
            is_discountable=True,
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

    # Service option should be completely ignored in CAPEX
    assert result.total_capex == 94500.0


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
