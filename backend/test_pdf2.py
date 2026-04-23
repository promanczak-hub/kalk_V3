from dotenv import load_dotenv

load_dotenv()
from core.extractor_v2 import extract_vehicle_data_v2


def main():
    file_path = r"C:\Users\proma\Downloads\SANTA FE Hybrid.pdf"

    with open(file_path, "rb") as f:
        data = f.read()

    print("Rozpoczynam ekstrakcję dla:", file_path)
    result = extract_vehicle_data_v2(document_data=data)
    print("\n\n--- WYNIK ---")
    print(result)


if __name__ == "__main__":
    main()
