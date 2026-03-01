from sqlalchemy import create_engine, text


def populate_prices():
    engine = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")

    # Base estimated budget prices per inch based on market averages in PLN
    base_budget = {
        13: 150,
        14: 165,
        15: 180,
        16: 220,
        17: 260,
        18: 300,
        19: 350,
        20: 400,
        21: 480,
        22: 560,
        23: 650,
    }

    with engine.begin() as conn:
        for size, budget in base_budget.items():
            medium = round(budget * 1.4, 0)
            premium = round(budget * 1.9, 0)

            wzm_budget = round(budget * 1.15, 0)
            wzm_medium = round(medium * 1.15, 0)
            wzm_premium = round(premium * 1.15, 0)

            wiel_budget = round(budget * 1.18, 0)
            wiel_medium = round(medium * 1.18, 0)
            wiel_premium = round(premium * 1.18, 0)

            wiel_wzm_budget = round(budget * 1.35, 0)
            wiel_wzm_medium = round(medium * 1.35, 0)
            wiel_wzm_premium = round(premium * 1.35, 0)

            query = text("""
            UPDATE koszty_opon
            SET 
                budget = :budget,
                medium = :medium,
                premium = :premium,
                wzmocnione_budget = :wzm_budget,
                wzmocnione_medium = :wzm_medium,
                wzmocnione_premium = :wzm_premium,
                wielosezon_budget = :wiel_budget,
                wielosezon_medium = :wiel_medium,
                wielosezon_premium = :wiel_premium,
                wielosezon_wzmocnione_budget = :wiel_wzm_budget,
                wielosezon_wzmocnione_medium = :wiel_wzm_medium,
                wielosezon_wzmocnione_premium = :wiel_wzm_premium
            WHERE srednica = :size
            """)

            params = {
                "budget": budget,
                "medium": medium,
                "premium": premium,
                "wzm_budget": wzm_budget,
                "wzm_medium": wzm_medium,
                "wzm_premium": wzm_premium,
                "wiel_budget": wiel_budget,
                "wiel_medium": wiel_medium,
                "wiel_premium": wiel_premium,
                "wiel_wzm_budget": wiel_wzm_budget,
                "wiel_wzm_medium": wiel_wzm_medium,
                "wiel_wzm_premium": wiel_wzm_premium,
                "size": size,
            }
            conn.execute(query, params)

    print("Populated real-world estimated prices in koszty_opon table.")


if __name__ == "__main__":
    populate_prices()
