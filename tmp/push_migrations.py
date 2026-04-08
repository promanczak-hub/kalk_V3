import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

MIGRATIONS_DIR = Path(r"D:\kalk_v3\supabase\migrations")

# Supabase Online Details (EU-Central-1)
DB_HOST = "aws-0-eu-central-1.pooler.supabase.com"
DB_NAME = "postgres"
DB_USER = "postgres.gnpsdiarmwvqhqbyetce"


def get_ordered_migrations() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def main():
    db_password = sys.argv[1] if len(sys.argv) > 1 else None

    files = get_ordered_migrations()
    print(f"Found {len(files)} migration files to apply.\n")

    ports = [5432, 6543]
    passwords = [db_password] if db_password else []

    conn = None
    for pwd in passwords:
        for port in ports:
            print(f"Connecting to {DB_HOST} on port {port}...", end=" ", flush=True)
            try:
                conn = psycopg2.connect(
                    host=DB_HOST,
                    port=port,
                    dbname=DB_NAME,
                    user=DB_USER,
                    password=pwd,
                    sslmode="require",
                    connect_timeout=15,
                )
                conn.autocommit = True
                print("CONNECTED ✓")
                break
            except Exception as e:
                print(f"FAILED: {str(e).split('\\n')[0]}")
        if conn:
            break

    if not conn:
        print("\n❌ FATAL: Could not establish connection to Supabase pooler.")
        sys.exit(1)

    cur = conn.cursor()
    success, failed = 0, 0

    for i, migration_file in enumerate(files, 1):
        name = migration_file.name
        # Skip if already in the migrations we know
        if "20260402214700_add_alternatives_rpcs.sql" not in name:
            # We ONLY want to apply the new one to avoid double applying?
            # Or we can check if it exists or let it fail?
            # Wait, the script just runs EVERYTHING. I should only run the new one to be safe, or just run the unapplied ones.
            pass

        if "20260402214700" not in name:
            # Let's skip older ones to avoid breaking anything or errors
            continue

        sql = migration_file.read_text(encoding="utf-8")
        if not sql.strip():
            continue

        print(f"[{i:3d}/{len(files)}] Applying {name}...", end=" ", flush=True)
        try:
            cur.execute(sql)
            print("OK")
            success += 1
        except Exception as e:
            print(f"ERROR: {str(e).strip().split('\\n')[0]}")
            failed += 1
            # don't rollback since we are in autocommit mode

    print(f"\nMigration Summary: {success} Success, {failed} Failed.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
