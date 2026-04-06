import fitz  # PyMuPDF


def extract_text(pdf_path, outfile):
    try:
        doc = fitz.open(pdf_path)
        text = f"\n--- Wczytuje: {pdf_path} ---\n"
        for page in doc:
            text += page.get_text()

        outfile.write(text[:5000])  # Zapisujemy do 5000 znaków
        outfile.write("\n=========================================\n")
        doc.close()
    except Exception as e:
        outfile.write(f"Blad przy {pdf_path}: {e}\n")


if __name__ == "__main__":
    files = [
        r"C:\Users\proma\Downloads\PrintKalkulacjaMatrix (1).pdf",
        r"C:\Users\proma\Downloads\car-card-CBYBLMLM.pdf",
        r"C:\Users\proma\Downloads\PrintKalkulacjaMatrix.pdf",
    ]
    with open("pdf_extracted.txt", "w", encoding="utf-8") as f:
        for file in files:
            extract_text(file, f)
