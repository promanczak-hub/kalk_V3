import psycopg2


def main():
    try:
        conn = psycopg2.connect(
            "postgresql://postgres:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
        )
        cur = conn.cursor()

        # UPDATE
        cur.execute(
            "UPDATE public.samar_class_depreciation_rates SET base_depreciation_percent = 0.40 WHERE samar_class_id=4 AND fuel_type_id=2 AND year=0"
        )

        # Options 0.26 might not exist if it's 0.0 in drafts? Let's just set it
        cur.execute(
            "UPDATE public.samar_class_depreciation_rates SET options_depreciation_percent = 0.26 WHERE samar_class_id=4 AND fuel_type_id=2 AND year=4"
        )

        conn.commit()
        print("SUCCESS")

        cur.close()
        conn.close()
    except Exception as e:
        print("ERROR:", e)


if __name__ == "__main__":
    main()
