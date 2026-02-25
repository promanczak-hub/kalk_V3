import json

# Class diversity mapping
# By KlasaWRId
# 1=A, 2=Asport, 3=B, 4=Bsport, 5=Bsuv, 6=Bvan, 7=C, 8=Csport, 9=Csuv, 10=Cvan
# 11=D, 12=Dsport, 13=Dsuv, 14=Dvan, 15=E, 16=Esuv, 17=F, 18=Fsport, 19=Fsuv
# 20=M, 21=Mvan, 22=R, 23=P, 24=T PICK_UP

CLASS_PROFILES = {
    "A": (0.0090, 0.568, 0.1080),
    "B": (0.0095, 0.544, 0.1140),
    "C": (0.0100, 0.520, 0.1200),
    "D": (0.0105, 0.496, 0.1260),
    "E": (0.0110, 0.472, 0.1320),
    "F": (0.0120, 0.424, 0.1440),
    "SPORT": (0.0115, 0.448, 0.1380),
    "VAN": (0.0105, 0.496, 0.1260),
    "PICKUP": (0.0095, 0.544, 0.1140),
}

CLASS_MAPPING = {
    1: "A",
    20: "A",
    3: "B",
    5: "B",
    22: "B",
    7: "C",
    9: "C",
    23: "C",
    11: "D",
    13: "D",
    15: "E",
    16: "E",
    17: "F",
    19: "F",
    2: "SPORT",
    4: "SPORT",
    8: "SPORT",
    12: "SPORT",
    18: "SPORT",
    6: "VAN",
    10: "VAN",
    14: "VAN",
    21: "VAN",
    24: "PICKUP",
}


def get_profile(klasa_id):
    klasa_id = int(klasa_id)
    profile_name = CLASS_MAPPING.get(klasa_id, "C")
    return CLASS_PROFILES[profile_name]


def run_update():
    print("Reading samar_rv_data.json...")
    with open("samar_rv_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Update LTRAdminTabelaWRKlasas (Base RV 40)
    for row in data.get("LTRAdminTabelaWRKlasas", []):
        klasa_id = row.get("KlasaWRId")
        if klasa_id is not None:
            _, base_rv, _ = get_profile(klasa_id)
            row["KorektaProcent"] = str(base_rv)

    # 2. Update LTRAdminTabelaWRDeprecjacjas (Annual Depr)
    for row in data.get("LTRAdminTabelaWRDeprecjacjas", []):
        klasa_id = row.get("KlasaWRId")
        if klasa_id is not None:
            _, _, annual_depr = get_profile(klasa_id)
            row["KorektaProcent"] = str(annual_depr)

    # 3. Update LTRAdminTabelaWRPrzebiegs (Mileage)
    for row in data.get("LTRAdminTabelaWRPrzebiegs", []):
        row["KorektaProcentPonizej190"] = "0.0020"
        row["KorektaProcentPowyzej190"] = "0.0010"

    # 4. Update LTRAdminTabelaWRDoposazenies (Options)
    for row in data.get("LTRAdminTabelaWRDoposazenies", []):
        row["KorektaProcent"] = "0.5000"

    print("Writing samar_rv_data.json...")
    with open("samar_rv_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Done. Ready to regenerate migrations.")


if __name__ == "__main__":
    run_update()
