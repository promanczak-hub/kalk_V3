from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony


def test_seasonal_tires_basic():
    """
    Test 1: Verify seasonal tire cost calculation for 3 years / 90,000 km.
    Expected: 1 set needed, 6 swaps (2/year), 6 storage units (2/year).
    """
    calc = LTRSubCalculatorOpony(
        all_season_tires=False,
        tire_buyback=0.0,
        srednica_felgi=16,
        klasa_opony="budget",
    )

    # Mocking DB calls for consistent test results
    calc.swap_cost = 120.0
    calc.storage_cost = 216.0
    calc.tire_set_price = 1000.0  # Assumed price for 16" budget

    months = 36
    mileage = 90000

    total_cost_dict = calc.calculate_cost(months, mileage)
    total_cost = total_cost_dict["total_monthly_tire_cost"] * months

    # Expected calculations:
    # 1. Sets Needed: < 120k -> 1 additional set
    # 2. Hardware Cost: 1 set * 1000.0 = 1000.0
    # 3. Swap Cost: (36 / 12) * 2 * 120.0 = 6 * 120 = 720.0
    # 4. Storage Cost: (36 / 12) * 2 * 216.0 = 6 * 216 = 1296.0
    # Total = 1000 + 720 + 1296 = 3016.0

    assert total_cost == 3016.0


def test_all_season_tires_basic():
    """
    Test 2: Verify all-season tire cost calculation for 4 years / 100,000 km.
    Expected: 2 sets needed, ~2 swaps (100k/60k rounded up), 0 storage.
    """
    calc = LTRSubCalculatorOpony(
        all_season_tires=True,
        tire_buyback=0.0,
        srednica_felgi=17,
        klasa_opony="premium",
    )

    calc.swap_cost = 120.0
    calc.storage_cost = 216.0
    calc.tire_set_price = 2000.0  # Assumed price for 17" premium all-season

    months = 48
    mileage = 100000

    total_cost_dict = calc.calculate_cost(months, mileage)
    total_cost = total_cost_dict["total_monthly_tire_cost"] * months

    # Expected calculations:
    # 1. Sets Needed: 100000 < 120k -> 2 additional sets? (Actually V1 logic for AS: mileage / 60k rounded up. 100k -> 2 sets needed total. But hardware cost is proportional: base + ((100k - 60k)/60k)*base)
    # Hardware Cost (V1 logic proportional):
    # Base: 2000.0
    # Add: ((100000 - 60000) / 60000) * 2000.0 = (40000 / 60000) * 2000.0 = 0.6666... * 2000.0 = 1333.33
    # Total Hardware: 3333.33
    # 2. Swaps (All Season logic): ceil(100000 / 60000) = 2. Swaps = 2 * 120.0 = 240.0
    # 3. Storage: 0.0
    # Total = 3333.33 + 240.0 = 3573.33

    assert round(total_cost, 2) == 3573.33


def test_mileage_edge_cases():
    """
    Test 3: Mileage threshold edge cases (exactly 60k, exactly 120k)
    """
    calc = LTRSubCalculatorOpony(
        all_season_tires=True, tire_buyback=0.0, srednica_felgi=16, klasa_opony="budget"
    )

    calc.swap_cost = 100.0
    calc.storage_cost = 200.0
    calc.tire_set_price = 1000.0

    # Exactly 60k -> Hardware: base (1000), Swaps: ceil(60k/60k)=1 -> 1*100=100. Total = 1100
    c1 = calc.calculate_cost(24, 60000)
    assert round(c1["total_monthly_tire_cost"] * 24, 2) == 1100.0

    # Exactly 120k -> Hardware: 1000 + ((120k-60k)/60k)*1000 = 1000 + 1000 = 2000
    # Swaps: ceil(120k/60k)=2 -> 2*100=200. Total = 2200
    c2 = calc.calculate_cost(48, 120000)
    assert round(c2["total_monthly_tire_cost"] * 48, 2) == 2200.0
