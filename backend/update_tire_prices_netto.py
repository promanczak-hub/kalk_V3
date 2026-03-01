from sqlalchemy import create_engine, text


def update_prices_to_netto():
    engine = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")

    query = text("""
    UPDATE koszty_opon
    SET 
        budget = ROUND(budget / 1.23, 2),
        medium = ROUND(medium / 1.23, 2),
        premium = ROUND(premium / 1.23, 2),
        wzmocnione_budget = ROUND(wzmocnione_budget / 1.23, 2),
        wzmocnione_medium = ROUND(wzmocnione_medium / 1.23, 2),
        wzmocnione_premium = ROUND(wzmocnione_premium / 1.23, 2),
        wielosezon_budget = ROUND(wielosezon_budget / 1.23, 2),
        wielosezon_medium = ROUND(wielosezon_medium / 1.23, 2),
        wielosezon_premium = ROUND(wielosezon_premium / 1.23, 2),
        wielosezon_wzmocnione_budget = ROUND(wielosezon_wzmocnione_budget / 1.23, 2),
        wielosezon_wzmocnione_medium = ROUND(wielosezon_wzmocnione_medium / 1.23, 2),
        wielosezon_wzmocnione_premium = ROUND(wielosezon_wzmocnione_premium / 1.23, 2)
    """)

    with engine.begin() as conn:
        conn.execute(query)

    print("Updated all tire prices to net values (divided by 1.23).")


if __name__ == "__main__":
    update_prices_to_netto()
