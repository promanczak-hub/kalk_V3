import json

with open("samar_raw.json", "r", encoding="utf-8") as f:
    data = json.load(f)

dt = data["digital_twin"]["content"]

md_lines = []
md_lines.append("# Segmentacja Rynku SAMAR 2025")
md_lines.append("")

for section in dt:
    title = section.get("section_title", "")
    if title:
        md_lines.append(f"## {title}")
        md_lines.append("")

    if "purpose" in section:
        md_lines.append("**Cel:**")
        for p in section["purpose"]:
            md_lines.append(f"- {p}")
        md_lines.append("")

    if "description" in section:
        md_lines.append(f"{section['description']}")
        md_lines.append("")

    if "classification_parameters" in section:
        md_lines.append("**Parametry podstawowe:**")
        for p in section["classification_parameters"]["primary"]:
            md_lines.append(f"- {p}")
        md_lines.append("")
        md_lines.append("**Parametry wspomagające:**")
        for p in section["classification_parameters"]["supporting"]:
            md_lines.append(f"- {p}")
        md_lines.append("")

    if "definitions" in section:
        for d in section["definitions"]:
            md_lines.append(f"- **{d['term']}**: {d['description']}")
        md_lines.append("")

    if "segmentation_matrix" in section:
        matrix = section["segmentation_matrix"]
        if len(matrix) > 0:
            headers = list(matrix[0].keys())
            # Put "segment" as the first column
            if "segment" in headers:
                headers.remove("segment")
                headers.insert(0, "segment")

            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("|" + "|".join(["---" for _ in headers]) + "|")
            for row in matrix:
                segment_val = str(row.get("segment")) if row.get("segment") else ""
                r_vals = []
                for h in headers:
                    val = row.get(h)
                    if val is None:
                        r_vals.append("-")
                    elif h != "segment" and str(val) == segment_val:
                        r_vals.append("✅")
                    else:
                        r_vals.append(str(val))
                md_lines.append("| " + " | ".join(r_vals) + " |")
        md_lines.append("")

    if "classes" in section:
        classes = section["classes"]
        for cls_name, models in classes.items():
            md_lines.append(f"### {cls_name}")
            md_lines.append(", ".join(models))
            md_lines.append("")

    if "note" in section:
        md_lines.append(f"*{section['note']}*")
        md_lines.append("")

with open("frontend/src/samar_markdown.ts", "w", encoding="utf-8") as f:
    f.write("export const SAMAR_MARKDOWN = `\n")
    f.write("\n".join(md_lines).replace("`", "\\`"))
    f.write("\n`;\n")

print("Generated frontend/src/samar_markdown.ts")
