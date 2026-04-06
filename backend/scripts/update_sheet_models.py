import os
import logging
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
CLASSES_GID = 802400199

# Mapping of Row Index (1-indexed) to New Content for Column C
MODEL_MAPPING = {
    2: "",
    3: "Citroen Jumper, Fiat Ducato, Ford Transit, Iveco Daily, Mercedes Sprinter, Renault Master, Volkswagen Crafter",
    4: "Citroen Berlingo, Ford Transit Connect, Mercedes Citan, Opel Combo, Peugeot Rifter, Renault Kangoo, Volkswagen Caddy",
    5: "Citroen Berlingo, Fiat Doblo, Ford Transit Connect, Peugeot Partner, Renault Kangoo Van, Toyota Proace City, Volkswagen Caddy",
    6: "Citroen C3 Van, Dacia Spring Cargo, Ford Transit Courier, Kia Niro Van, Opel Corsa Van, Peugeot 208 Van, Renault Clio Societe",
    7: "Ford Tourneo Custom, Hyundai Staria, Mercedes Vito/V-Class, Renault Trafic, Toyota Proace Verso, Volkswagen Multivan/Caravelle",
    8: "Ford Ranger, Isuzu D-Max, Ssangyong Musso, Toyota Hilux, Volkswagen Amarok",
    9: "Dacia Spring, Fiat Panda, Fiat 500, Hyundai i10, Kia Picanto, Toyota Aygo X",
    10: "Audi A1, Dacia Sandero, Hyundai i20, Opel Corsa, Peugeot 208, Renault Clio, Skoda Fabia, Toyota Yaris, Volkswagen Polo",
    11: "Audi A3, BMW 1 Seria, Ford Focus, Hyundai i30, Kia Ceed, Mercedes A-Klasa, Opel Astra, Renault Megane, Skoda Octavia, Toyota Corolla, Volkswagen Golf",
    12: "Audi A5, BMW 3 Seria, Mercedes C-Klasa, Peugeot 508, Skoda Superb, Tesla Model 3, Toyota Camry, Volkswagen Passat, Volvo S60/V60",
    13: "Audi A6, BMW 5 Seria, Mercedes E-Klasa, Tesla Model S, Volvo S90/V90",
    14: "Audi A8, BMW 7 Seria, Lexus LS, Mercedes S-Klasa, Porsche Panamera",
    15: "Bentley Flying Spur, Rolls Royce Ghost, Rolls Royce Phantom",
    16: "Abarth 500 Cabrio, Fiat 500 Cabrio",
    17: "Mini Mini Cabrio",
    18: "BMW 4 Seria, Ford Mustang, Porsche 718",
    19: "Mercedes CLE",
    20: "Alpine A110, BMW 2 Seria, BMW Z4, Mazda MX-5",
    21: "BMW 8 Seria, Mercedes SL, Porsche 911",
    22: "Aston Martin Vantage, Bentley Continental, Ferrari 296, Lamborghini Revuelto, Maserati MC20, Rolls-Royce Spectre",
    23: "Citroen Jumpy, Fiat Scudo, Ford Transit Custom, Mercedes Vito, Opel Vivaro, Peugeot Expert, Renault Trafic, Toyota Proace, Volkswagen Transporter",
    24: "Audi Q2, Ford Puma, Hyundai Kona, Jeep Renegade, Kia Stonic, Peugeot 2008, Renault Captur, Skoda Kamiq, Toyota Yaris Cross, Volkswagen T-Roc",
    25: "Audi Q3, BMW X1, Dacia Duster, Hyundai Tucson, Kia Sportage, Nissan Qashqai, Peugeot 3008, Renault Austral, Skoda Karoq, Toyota Corolla Cross, Volkswagen Tiguan",
    26: "Audi Q5, BMW X3, Ford Kuga, Hyundai Santa Fe, Kia Sorento, Lexus NX, Mercedes GLC, Nissan X-Trail, Skoda Kodiaq, Toyota RAV4, Volvo XC60",
    27: "BMW X7, Hongqi E-HS9, Lotus Eletre, Mercedes EQS SUV, Mercedes GLS",
    28: "Aston Martin DBX, Bentley Bentayga, Ferrari Purosangue, Lamborghini Urus, Rolls Royce Cullinan",
    29: "Audi Q7, Audi Q8, BMW X5, BMW X6, Jeep Grand Cherokee, Lexus RX, Mercedes GLE, Porsche Cayenne, Tesla Model X, Toyota Land Cruiser, Volkswagen Touareg, Volvo XC90",
    30: "Honda Jazz",
    31: "BMW 2 Active Tourer, Dacia Jogger, Mercedes B-Klasa, Volkswagen Touran",
    32: "Forthing U-Tour",
    33: "Lexus LM",
    34: "Forthing V-Tour, Voyah Dream"
}

def get_gspread_client():
    key_path = "D:/kalk_v3/backend/google_sa_key.json"
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)

def update_sheet():
    logger.info("Connecting to Google Sheets...")
    gc = get_gspread_client()
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = next((w for w in ss.worksheets() if w.id == CLASSES_GID), None)

    if not ws:
        logger.error(f"Worksheet with gid {CLASSES_GID} not found!")
        return

    logger.info(f"Updating Column C in worksheet: {ws.title}")
    
    # We'll build a batch update to minimize API calls
    # Column C is the 3rd column. We start from Row 2 to 34.
    # range_name = 'C2:C34'
    
    rows_to_update = []
    for r in range(2, 35):
        val = MODEL_MAPPING.get(r, "")
        rows_to_update.append([val])
    
    ws.update(range_name='C2:C34', values=rows_to_update)
    logger.info("Successfully updated Column C (Rows 2-34).")

if __name__ == "__main__":
    update_sheet()
