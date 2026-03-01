import time
from dotenv import load_dotenv

from core.pipeline_discounts import match_fleet_discount

# Wczytaj środowisko
load_dotenv()


def run_test():
    brand = "SKODA"
    model = "SUPERB"
    vehicle_summary = {
        "digital_twin": {"metadata": {"document_type": "Oferta na samochód"}},
        "card_summary": {"brand": brand, "model": model, "powertrain": "2.0 TSI"},
    }

    print("Sending to Gemini Flash matched via new Pipeline...")
    start_llm = time.time()
    try:
        match_result = match_fleet_discount(vehicle_summary)
        print("Match result:", match_result)
    except Exception as e:
        print("Error:", e)
    print(f"Pipeline call took {time.time() - start_llm:.2f}s")


if __name__ == "__main__":
    run_test()
