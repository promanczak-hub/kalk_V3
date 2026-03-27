import json
import psycopg2

# Używamy najnowszego poolera sesyjnego wskazanego przez dashboard
db_url = "postgresql://postgres.gnpsdiarmwvqhqbyetce:Rockyramboa17%40@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"


def run_diagnostics():
    results = {}

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("Uruchamianie diagnozy constraints...")
        query_constraints = """
            SELECT conname, convalidated, contype, relname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            WHERE n.nspname = 'public' AND c.convalidated = false;
        """
        cur.execute(query_constraints)
        res = cur.fetchall()
        invalid_constraints = [
            {"constraint": r[0], "validated": r[1], "type": r[2], "table": r[3]}
            for r in res
        ]
        results["invalid_constraints"] = invalid_constraints

        print("Uruchamianie diagnozy sekwencji...")
        query_seq = """
        SELECT
            t.relname AS table_name,
            c.relname AS sequence_name
        FROM pg_class c
        JOIN pg_depend d ON d.objid = c.oid
        JOIN pg_class t ON d.refobjid = t.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relkind = 'S' AND n.nspname = 'public';
        """
        cur.execute(query_seq)
        res_seq = cur.fetchall()
        sequences = [{"table": r[0], "sequence": r[1]} for r in res_seq]

        seq_issues = []
        for seq in sequences:
            table = seq["table"]
            sequence = seq["sequence"]
            try:
                # Get max id
                cur.execute(f'SELECT MAX(id) FROM public."{table}"')
                max_id = cur.fetchone()[0] or 0

                # Get sequence current value
                cur.execute(f"SELECT last_value FROM {sequence}")
                curr_val = cur.fetchone()[0] or 0

                if curr_val < max_id:
                    seq_issues.append(
                        {
                            "table": table,
                            "sequence": sequence,
                            "max_id": max_id,
                            "current_sequence": curr_val,
                        }
                    )
            except Exception:
                pass

        results["sequence_issues"] = seq_issues

        cur.close()
        conn.close()
    except Exception as e:
        print("ERROR:", e)
        return

    with open("diagnostics_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("Diagnoza zakończona. Wyniki zapisano do diagnostics_output.json")


if __name__ == "__main__":
    run_diagnostics()
