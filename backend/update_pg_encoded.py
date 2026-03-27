import psycopg2

conn_str = "postgresql://postgres:ROckyramboa17%40@db.gnpsdiarmwvqhqbyetce.supabase.co:5432/postgres"


def main():
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()

        # Check current value
        cur.execute(
            "SELECT year, base_depreciation_percent, options_depreciation_percent FROM public.samar_class_depreciation_rates WHERE samar_class_id=4 AND fuel_type_id=2"
        )
        rows = cur.fetchall()
        print("BEFORE:", rows)

        # UPDATE
        cur.execute(
            "UPDATE public.samar_class_depreciation_rates SET base_depreciation_percent = 0.40 WHERE samar_class_id=4 AND fuel_type_id=2 AND year=0"
        )

        cur.execute(
            "UPDATE public.samar_class_depreciation_rates SET options_depreciation_percent = 0.26 WHERE samar_class_id=4 AND fuel_type_id=2 AND year=4"
        )

        conn.commit()

        # Check after
        cur.execute(
            "SELECT year, base_depreciation_percent, options_depreciation_percent FROM public.samar_class_depreciation_rates WHERE samar_class_id=4 AND fuel_type_id=2"
        )
        rows2 = cur.fetchall()
        print("AFTER:", rows2)

        cur.close()
        conn.close()
        print("SUCCESS")
    except Exception as e:
        print("ERROR:", e)


if __name__ == "__main__":
    main()
