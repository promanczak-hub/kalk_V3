from backend.core.database import supabase

# Class diversity mapping
# By klasa_wr_id
# 1=A, 2=Asport, 3=B, 4=Bsport, 5=Bsuv, 6=Bvan, 7=C, 8=Csport, 9=Csuv, 10=Cvan
# 11=D, 12=Dsport, 13=Dsuv, 14=Dvan, 15=E, 16=Esuv, 17=F, 18=Fsport, 19=Fsuv
# 20=M, 21=Mvan, 22=R, 23=P, 24=T PICK_UP

CLASS_PROFILES = {
    # (monthly_loss, base_rv_4y, annual_depr)
    "A": (0.0090, 0.568, 0.1080),  # A, M (1, 20)
    "B": (0.0095, 0.544, 0.1140),  # B, Bsuv, R (3, 5, 22)
    "C": (0.0100, 0.520, 0.1200),  # C, Csuv, P (7, 9, 23)
    "D": (0.0105, 0.496, 0.1260),  # D, Dsuv (11, 13)
    "E": (0.0110, 0.472, 0.1320),  # E, Esuv (15, 16)
    "F": (0.0120, 0.424, 0.1440),  # F, Fsuv (17, 19)
    "SPORT": (
        0.0115,
        0.448,
        0.1380,
    ),  # Asport, Bsport, Csport, Dsport, Fsport (2, 4, 8, 12, 18)
    "VAN": (0.0105, 0.496, 0.1260),  # Bvan, Cvan, Dvan, Mvan (6, 10, 14, 21)
    "PICKUP": (0.0095, 0.544, 0.1140),  # T PICK_UP (24)
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
    profile_name = CLASS_MAPPING.get(klasa_id, "C")
    return CLASS_PROFILES[profile_name]


def run_update():
    print(
        "Updating ltr_admin_tabela_wr_klasas (Base RV 4Y) and ltr_admin_tabela_wr_deprecjacjas (Annual Depreciation)..."
    )
    for klasa_id in range(1, 25):
        _, base_rv, annual_depr = get_profile(klasa_id)

        # Update base RV for this class
        supabase.table("ltr_admin_tabela_wr_klasas").update(
            {"korekta_procent": base_rv}
        ).eq("klasa_wr_id", klasa_id).execute()

        # Update annual depreciation for this class
        supabase.table("ltr_admin_tabela_wr_deprecjacjas").update(
            {"korekta_procent": annual_depr}
        ).eq("klasa_wr_id", klasa_id).execute()

    print("Updating ltr_admin_tabela_wr_przebiegs...")
    supabase.table("ltr_admin_tabela_wr_przebiegs").update(
        {"korekta_procent_ponizej_190": 0.0020, "korekta_procent_powyzej_190": 0.0010}
    ).neq("id", 0).execute()

    print("Updating ltr_admin_tabela_wr_doposazenies...")
    supabase.table("ltr_admin_tabela_wr_doposazenies").update(
        {"korekta_procent": 0.50}
    ).neq("id", 0).execute()

    print("Mock DB Update complete.")


if __name__ == "__main__":
    run_update()
