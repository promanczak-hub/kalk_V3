"""Extract PDF annotations/comments cleanly to a file."""

import fitz  # pymupdf

pdf_path = r"C:\Users\proma\Downloads\opisapki.pdf"
doc = fitz.open(pdf_path)

output_lines: list[str] = []
output_lines.append(f"PDF: {pdf_path}")
output_lines.append(f"Stron: {len(doc)}")
output_lines.append("=" * 80)

for page_num, page in enumerate(doc, 1):
    annots = list(page.annots()) if page.annots() else []
    if not annots:
        output_lines.append(f"\n### Strona {page_num}: Brak adnotacji")
        continue

    output_lines.append(f"\n### Strona {page_num}: {len(annots)} adnotacji")
    output_lines.append("-" * 60)

    for i, annot in enumerate(annots, 1):
        annot_type = annot.type
        content = annot.info.get("content", "").strip()
        title = annot.info.get("title", "").strip()
        subject = annot.info.get("subject", "").strip()
        creation_date = annot.info.get("creationDate", "").strip()
        rect = annot.rect

        output_lines.append(
            f"\n  [{i}] Typ: {annot_type[1]} | Autor: {title} | Data: {creation_date}"
        )
        output_lines.append(f"      Pozycja: x={rect.x0:.0f}, y={rect.y0:.0f}")
        output_lines.append("      TREŚĆ:")
        # Split content by lines for readability
        for line in content.split("\n"):
            output_lines.append(f"        {line}")

output_lines.append("\n" + "=" * 80)

result = "\n".join(output_lines)
with open("pdf_annotations_clean.txt", "w", encoding="utf-8") as f:
    f.write(result)

print(f"Zapisano {len(output_lines)} linii do pdf_annotations_clean.txt")
doc.close()
