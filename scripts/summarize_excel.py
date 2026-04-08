import json

with open("excel_style_dump.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for row in data["rows"]:
    for cell in row:
        if cell["val"] is not None and str(cell["val"]) != "None":
            c_font = cell.get("font") or {}
            c_fill = cell.get("fill")
            print(
                f"{cell['addr']}: {cell['val'][:30]}... | Font: {c_font.get('name')} {c_font.get('size')} bold={c_font.get('bold')} color={c_font.get('color')} | Fill: {c_fill}"
            )
