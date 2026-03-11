"""
Side-by-side V1 vs V3 CAPEX formula trace for Skoda Superb.
Saves output to diag_capex_trace.txt
"""
import sys
sys.path.insert(0, ".")

OUT = "diag_capex_trace.txt"

# === INPUTS (identical for both) ===
CENA_CENNIKOWA_BRUTTO = 212350.0  # V1: CenaCennikowa (brutto)
OPCJE_FABRYCZNE_BRUTTO = 28950.0  # V1: Sum(OpcjeFabryczne.CenaCennikowa) (brutto)
RABAT_V1 = 0.23  # V1 screenshot: 0.2300
RABAT_V3 = 0.24  # User said 24%
VAT = 1.23

# V1 extras
OPLATA_TRANSPORTOWA_BRUTTO = 0.0  # Skoda — brak
OPCJE_NIERABATOWANE_BRUTTO = 0.0  # assume none
GSM_URZADZENIE_NETTO = 469.0
GSM_MONTAZ_NETTO = 150.0
CZY_GPS = True
PAKIET_SERWISOWY = 0.0
KOSZT_1KPL_OPON_NETTO = 9420.0  # from V3 diag (IloscOpon)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("=" * 70 + "\n")
    f.write("V1 CAPEX (LTRSubCalculatorCenaZakupu.cs) — arytmetyka BRUTTO\n")
    f.write("=" * 70 + "\n\n")

    f.write(f"CenaCennikowa (brutto):        {CENA_CENNIKOWA_BRUTTO:>12.2f}\n")
    f.write(f"OpcjeFabryczne (brutto):       {OPCJE_FABRYCZNE_BRUTTO:>12.2f}\n")

    v1_cena_z_opcjami = CENA_CENNIKOWA_BRUTTO + OPCJE_FABRYCZNE_BRUTTO
    f.write(f"cenaKatalogowaZOpcjami:         {v1_cena_z_opcjami:>12.2f}  (baza+opcje brutto)\n\n")

    f.write(f"Rabat V1:                       {RABAT_V1*100:.0f}%\n")
    v1_po_rabacie = (v1_cena_z_opcjami - OPLATA_TRANSPORTOWA_BRUTTO - OPCJE_NIERABATOWANE_BRUTTO) \
                    * (1 - RABAT_V1) \
                    + OPLATA_TRANSPORTOWA_BRUTTO + OPCJE_NIERABATOWANE_BRUTTO
    f.write(f"poRabacie (brutto):             {v1_po_rabacie:>12.2f}\n")

    v1_rabat_kwotowo = v1_cena_z_opcjami - v1_po_rabacie
    f.write(f"rabatKwotowo:                   {v1_rabat_kwotowo:>12.2f}  (V1 screenshot=55499)\n\n")

    # GSM as opcja serwisowa
    v1_gsm_brutto = 0.0
    if CZY_GPS:
        v1_gsm_brutto = (GSM_URZADZENIE_NETTO + GSM_MONTAZ_NETTO) * VAT
        f.write(f"GSM opcja serwisowa (brutto):   {v1_gsm_brutto:>12.2f}  ({GSM_URZADZENIE_NETTO}+{GSM_MONTAZ_NETTO})*{VAT}\n")

    v1_opony_brutto = KOSZT_1KPL_OPON_NETTO * VAT
    f.write(f"Opony 1 komplet (brutto):       {v1_opony_brutto:>12.2f}  {KOSZT_1KPL_OPON_NETTO}*{VAT}\n\n")

    v1_final_brutto = v1_po_rabacie + v1_gsm_brutto + v1_opony_brutto + PAKIET_SERWISOWY
    f.write(f"CAPEX FINAL (brutto):           {v1_final_brutto:>12.2f}\n")

    v1_netto = v1_final_brutto / VAT
    f.write(f"CAPEX FINAL (netto = /1.23):    {v1_netto:>12.2f}  ← V1 CenaZakupu\n")
    f.write(f"V1 screenshot CenaZakupu:       {154278.97:>12.2f}\n")
    f.write(f"Różnica:                        {v1_netto - 154278.97:>12.2f}\n\n")

    # V1 BEZ opon (CenaZakupuBezOpon)
    v1_bez_opon_brutto = v1_final_brutto - v1_opony_brutto
    v1_bez_opon_netto = v1_bez_opon_brutto / VAT
    f.write(f"V1 BEZ opon (netto):            {v1_bez_opon_netto:>12.2f}\n")

    # V1 BEZ opon i serwisowych
    v1_bez_opon_serw_brutto = v1_bez_opon_brutto - v1_gsm_brutto
    v1_bez_opon_serw_netto = v1_bez_opon_serw_brutto / VAT
    f.write(f"V1 BEZ opon+serwisowych (netto):{v1_bez_opon_serw_netto:>12.2f}\n")

    f.write("\n" + "=" * 70 + "\n")
    f.write("V3 CAPEX (PurchasePriceCalculator) — arytmetyka NETTO\n")
    f.write("=" * 70 + "\n\n")

    # V3 inputs (from diag_superb.py)
    v3_base_net = CENA_CENNIKOWA_BRUTTO  # ← HERE IS THE ISSUE
    v3_opcje_net = OPCJE_FABRYCZNE_BRUTTO  # ← AND HERE
    v3_rabat = RABAT_V3

    f.write(f"base_price_net:                 {v3_base_net:>12.2f}  ← CO TU TRAFIA?\n")
    f.write(f"opcje fabryczne (net):          {v3_opcje_net:>12.2f}  ← CO TU TRAFIA?\n")
    f.write(f"discount_pct:                   {v3_rabat*100:.0f}%\n\n")

    v3_discount_factor = 1.0 - v3_rabat
    v3_discounted_base = v3_base_net * v3_discount_factor
    f.write(f"discounted_base:                {v3_discounted_base:>12.2f}\n")

    v3_disc_opts = v3_opcje_net * v3_discount_factor
    f.write(f"opcje po rabacie:               {v3_disc_opts:>12.2f}\n")

    v3_gsm_capex = GSM_URZADZENIE_NETTO + GSM_MONTAZ_NETTO
    v3_tires_capex = 0.0  # NOT added in my diag

    v3_total = v3_discounted_base + v3_disc_opts + v3_gsm_capex + v3_tires_capex
    f.write(f"GSM capex (netto):              {v3_gsm_capex:>12.2f}\n")
    f.write(f"Opony capex (netto):            {v3_tires_capex:>12.2f}  ← NIE DODANE!\n\n")
    f.write(f"V3 total_capex:                 {v3_total:>12.2f}\n")
    f.write(f"V3 diag output:                 {184007.00:>12.2f}\n\n")

    f.write("=" * 70 + "\n")
    f.write("KLUCZOWE PYTANIE: czy base_price_net to BRUTTO czy NETTO?\n")
    f.write("=" * 70 + "\n\n")

    # If base_price_net is actually NETTO (/ 1.23):
    v3_base_netto = CENA_CENNIKOWA_BRUTTO / VAT
    v3_opcje_netto = OPCJE_FABRYCZNE_BRUTTO / VAT
    f.write(f"Jeśli base_price_net = brutto/VAT: {v3_base_netto:>12.2f}\n")
    f.write(f"Jeśli opcje netto = brutto/VAT:    {v3_opcje_netto:>12.2f}\n\n")

    v3_disc_base_netto = v3_base_netto * (1 - v3_rabat)
    v3_disc_opts_netto = v3_opcje_netto * (1 - v3_rabat)
    v3_total_netto = v3_disc_base_netto + v3_disc_opts_netto + v3_gsm_capex
    f.write(f"discounted_base (netto):        {v3_disc_base_netto:>12.2f}\n")
    f.write(f"opcje po rabacie (netto):       {v3_disc_opts_netto:>12.2f}\n")
    f.write(f"total CAPEX (netto, bez opon):  {v3_total_netto:>12.2f}\n\n")

    # Compare with V1 netto result (also without tires)
    f.write(f"V1 BEZ opon (netto):            {v1_bez_opon_netto:>12.2f}\n")
    f.write(f"Różnica (V3_netto - V1_netto):  {v3_total_netto - v1_bez_opon_netto:>12.2f}\n")
    f.write(f"  → z czego 1% rabatu:          {(v3_rabat - RABAT_V1)*100:.0f}% = ")
    extra_rabat = (v3_base_netto + v3_opcje_netto) * 0.01
    f.write(f"{extra_rabat:>12.2f} per 1%\n\n")

    # What would V3 give with 23% rabat (same as V1)?
    v3_disc_base_23 = v3_base_netto * (1 - 0.23)
    v3_disc_opts_23 = v3_opcje_netto * (1 - 0.23)
    v3_total_23 = v3_disc_base_23 + v3_disc_opts_23 + v3_gsm_capex
    f.write(f"V3 z 23% rabatu (netto):        {v3_total_23:>12.2f}\n")
    f.write(f"V1 z 23% (netto, z GSM):        {v1_bez_opon_netto:>12.2f}\n")
    f.write(f"Różnica przy tym samym 23%:     {v3_total_23 - v1_bez_opon_netto:>12.2f}\n")
    f.write("  → powinno być 0 jeśli formuły identyczne\n\n")

    f.write("=" * 70 + "\n")
    f.write("WNIOSEK\n")
    f.write("=" * 70 + "\n")
    f.write("""
Jeśli CenaCennikowa i Opcje Fabryczne to wartości BRUTTO (z frontendu),
to V3 musi je NAJPIERW przeliczyć na netto (/1.23) zanim zastosuje rabat.

V1 robi: rabat na brutto → dzieli przez VAT na końcu
V3 robi: rabat na wartość „jak jest" (base_price_net) — jeśli to brutto,
         to rabat się aplikuje do brutto, ale potem nigdzie nie dzieli /VAT.

To oznacza CAPEX V3 jest w brutto, nie w netto, mimo nazwy „base_price_net"!
""")

print(f"Output zapisany do {OUT}")
