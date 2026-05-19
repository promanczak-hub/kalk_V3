"""Add AC/OC default columns to control_center.

DEPRECATED: This was a one-off migration to the LEGACY wide-row `control_center`
schema. The table is now EAV (key/value) — see memory `control_center_eav` and
`core/control_center.py` adapter. Set new defaults via the adapter, not via
ALTER COLUMN.

Kept for historical reproducibility against a stock local Supabase dev DB.
Reads credentials from env (`SUPABASE_DB_*`) so no secret lives in source.
"""

import os
import sys


def main() -> None:
    sys.path.insert(0, ".")
    import psycopg2

    host = os.environ.get("SUPABASE_DB_HOST", "127.0.0.1")
    port = int(os.environ.get("SUPABASE_DB_PORT", "54322"))
    dbname = os.environ.get("SUPABASE_DB_NAME", "postgres")
    user = os.environ.get("SUPABASE_DB_USER", "postgres")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        sys.exit(
            "SUPABASE_DB_PASSWORD env var required. Refusing to use a default "
            "credential. For Supabase local dev: `export SUPABASE_DB_PASSWORD=postgres`."
        )

    conn = psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(
        """
        ALTER TABLE control_center
        ADD COLUMN IF NOT EXISTS ins_default_ac_rate NUMERIC DEFAULT 0.015;
        """
    )
    cur.execute(
        """
        ALTER TABLE control_center
        ADD COLUMN IF NOT EXISTS ins_default_oc_rate NUMERIC DEFAULT 1476.0;
        """
    )

    cur.execute(
        """
        UPDATE control_center
        SET ins_default_ac_rate = 0.015,
            ins_default_oc_rate = 1476.0
        WHERE id = 1;
        """
    )

    cur.execute(
        "SELECT ins_default_ac_rate, ins_default_oc_rate FROM control_center WHERE id = 1;"
    )
    row = cur.fetchone()
    print(f"AC rate: {row[0]}, OC rate: {row[1]}")

    cur.close()
    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
