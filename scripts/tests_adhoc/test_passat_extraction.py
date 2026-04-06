from dotenv import load_dotenv

# Load env before importing core which uses env keys
load_dotenv("../frontend/.env.local")

from core.extractor_v2 import extract_vehicle_data_v2  # noqa: E402


def main():
    file_path = "passat_test.pdf"

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    print("Running extraction...")
    result_json_str = extract_vehicle_data_v2(file_bytes, "application/pdf")

    # Save the result to a file for inspection
    with open("passat_extraction_result.json", "w", encoding="utf-8") as out_file:
        out_file.write(result_json_str)

    print("Done! Saved to passat_extraction_result.json")


if __name__ == "__main__":
    main()
