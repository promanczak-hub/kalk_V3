from sqlalchemy import create_engine, text


def create_and_seed_table():
    engine = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")

    create_sql = """
    CREATE TABLE IF NOT EXISTS koszty_opon (
        srednica INT PRIMARY KEY,
        budget NUMERIC DEFAULT 0,
        medium NUMERIC DEFAULT 0,
        premium NUMERIC DEFAULT 0,
        wzmocnione_budget NUMERIC DEFAULT 0,
        wzmocnione_medium NUMERIC DEFAULT 0,
        wzmocnione_premium NUMERIC DEFAULT 0,
        wielosezon_budget NUMERIC DEFAULT 0,
        wielosezon_medium NUMERIC DEFAULT 0,
        wielosezon_premium NUMERIC DEFAULT 0,
        wielosezon_wzmocnione_budget NUMERIC DEFAULT 0,
        wielosezon_wzmocnione_medium NUMERIC DEFAULT 0,
        wielosezon_wzmocnione_premium NUMERIC DEFAULT 0
    );
    """

    with engine.begin() as conn:
        conn.execute(text(create_sql))

        # Check if empty before seeding
        res = conn.execute(text("SELECT COUNT(*) FROM koszty_opon")).scalar()
        if res == 0:
            for size in range(13, 24):
                conn.execute(
                    text("INSERT INTO koszty_opon (srednica) VALUES (:srednica)"),
                    {"srednica": size},
                )
            print("Seeded table with sizes 13-23.")
        else:
            print(f"Table already has {res} rows. No seeding needed.")


if __name__ == "__main__":
    create_and_seed_table()
