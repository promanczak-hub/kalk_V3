from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")
with e.connect() as conn:
    r = conn.execute(text("SELECT * FROM koszty_opon ORDER BY srednica"))
    cols = r.keys()
    with open(r"d:\kalk_v3\backend\final_verify.md", "w", encoding="utf-8") as f:
        f.write("# Final koszty_opon table\n\n")
        header = " | ".join(str(c) for c in cols)
        f.write(f"| {header} |\n")
        f.write("|" + "|".join("---" for _ in cols) + "|\n")
        for row in r:
            vals = " | ".join(f"{float(v):.0f}" if v is not None else "-" for v in row)
            f.write(f"| {vals} |\n")

print("Written to final_verify.md")
