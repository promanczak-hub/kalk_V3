import pdfplumber

try:
    with pdfplumber.open(r"C:\Users\proma\Downloads\opisapki.pdf") as pdf:
        text = [page.extract_text() for page in pdf.pages]

    with open("opisapki.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(t for t in text if t))
    print("Extraction successful.")
except Exception as e:
    print(f"Error: {e}")
