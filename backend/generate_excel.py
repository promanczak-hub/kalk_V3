import pandas as pd
import os

def create_sample_offers_excel(filepath: str):
    data = [
        {
            "Marka": "Toyota",
            "Model": "Corolla",
            "Wersja": "1.8 Hybrid Comfort",
            "Paliwo": "Hybryda",
            "Rata netto (PLN)": 1500,
            "Czas trwania (mc)": 36,
            "Przebieg (km)": 20000
        },
        {
            "Marka": "Skoda",
            "Model": "Octavia",
            "Wersja": "2.0 TDI Style",
            "Paliwo": "Diesel",
            "Rata netto (PLN)": 1800,
            "Czas trwania (mc)": 48,
            "Przebieg (km)": 30000
        },
        {
            "Marka": "Porsche",
            "Model": "Macan",
            "Wersja": "2.0 TSI",
            "Paliwo": "Benzyna",
            "Rata netto (PLN)": 4500,
            "Czas trwania (mc)": 24,
            "Przebieg (km)": 15000
        }
    ]
    
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, engine='openpyxl')
    print(f"Zapisano plik Excel: {filepath}")

if __name__ == "__main__":
    out_path = os.path.join(os.getcwd(), "oferty_koszyk.xlsx")
    create_sample_offers_excel(out_path)
