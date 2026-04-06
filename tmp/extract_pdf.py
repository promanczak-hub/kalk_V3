import pymupdf
import sys

def extract_pdf_data(pdf_path):
    print(f"Opening PDF: {pdf_path}")
    doc = pymupdf.open(pdf_path)
    text = ""
    for page_num, page in enumerate(doc):
        text += f"\n--- PAGE {page_num + 1} ---\n"
        text += page.get_text()
    return text

if __name__ == "__main__":
    pdf_path = r"C:\Users\proma\Downloads\Segmentacja rynku SAMAR 202510 (1).pdf"
    try:
        content = extract_pdf_data(pdf_path)
        # Use an absolute path in the current workspace or relative to cwd
        with open("pdf_extracted.txt", "w", encoding="utf-8") as f:
            f.write(content)
        print("Extraction complete. Text saved to pdf_extracted.txt")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
