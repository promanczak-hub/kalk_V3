import csv
import sys

sys.path.append(r"d:\kalk_v3\backend")
from core.samar_mapper import _extract_short_code


def main():
    # 1. Zbudowanie mapy: V1 KlasaId -> Nowy SAMAR Code
    class_map = {}
    print("--- 1. ODPOWIEDNIKI Z KLASY.CSV ---")
    with open(r"C:\Users\proma\Downloads\klasy.csv", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # pomiń nagłówek
        for row in reader:
            if row and len(row) > 1:
                class_id = row[0]
                class_name = row[1]
                samar_code = _extract_short_code(class_name)
                class_map[class_id] = samar_code
                print(
                    f"ID z V1: {class_id:2} -> Pełna nazwa: {class_name[:40]:40s} -> Kod docelowy w Apce: {samar_code}"
                )

    # 2. Odczyt wspolczynników i nałożenie nowego SAMAR Code na podstawie KlasaId
    print("\n--- 2. POŁĄCZONE WSPÓŁCZYNNIKI SZKODOWE Z 36.CSV ---")
    results = {}
    with open(r"C:\Users\proma\Downloads\36.csv", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if row and len(row) >= 11:
                wsp_wartosc = row[1]
                wsp_przebieg = row[2]
                klasa_id = row[10]

                # Czysty join po ID
                if klasa_id in class_map:
                    samar_code = class_map[klasa_id]
                    results[samar_code] = {
                        "v1_id": klasa_id,
                        "wsp_wartosc": wsp_wartosc,
                        "wsp_przebieg": wsp_przebieg,
                    }

    print(
        f"{'Klasa (Apka V3)':<15} | {'V1 ID':<5} | {'WspWartoscSzkody':<18} | {'WspSredniPrzebieg':<18}"
    )
    print("-" * 65)
    for code, vals in sorted(results.items()):
        print(
            f"{code:<15} | {vals['v1_id']:<5} | {vals['wsp_wartosc']:<18} | {vals['wsp_przebieg']:<18}"
        )


if __name__ == "__main__":
    main()
