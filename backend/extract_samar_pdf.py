import fitz
import sys

pdf_path = r"C:\Users\proma\Downloads\Segmentacja rynku SAMAR 202510 (1).pdf"
try:
    doc = fitz.open(pdf_path)
except Exception as e:
    print(f"Error opening pdf: {e}")
    sys.exit(1)

text = ""
for page in doc:
    text += page.get_text("text") + "\n"

out_path = "extracted_samar.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Extracted length: {len(text)} characters. Saved to {out_path}.")
