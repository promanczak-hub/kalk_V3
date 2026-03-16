import asyncio
from backend.core.LTRKalkulator import LTRKalkulator
from backend.models_features import CalculatorInput

def main():
    payload = CalculatorInput(
        calculation_id='test',
        vehicle_id='10452',
        base_price_net=175528.45,
        discount_pct=15,
        factory_options=[],
        service_options=[],
        CzynszKwota=0,
        CzynszProcent=0,
        wibor_pct=4.82,
        pricing_margin_pct=15.0,
    )
    from backend.api.settings import get_settings
    
    k = LTRKalkulator(payload, samar_id="32")
    cells = k.build_matrix()
    c = [cell for cell in cells if cell["Okres"] == 48 and cell["Przebieg"] == 160000]
    
    if c:
        c = c[0]
        print("--- TARGET CELL (48m / 160k) ---")
        print("Stawka (LacznaStawka):", c["LacznaStawka"])
        print("CenaZakupu / CAPEX:", c["CenaZakupu"])
        print("VR / WR:", c["WR"])
        print("Utrata Wartosci:", c["UtrataWartosci"])
        print("KosztFinansowyLacznie:", c["KosztFinansowyLacznie"])
        print("SumaOdsetekZczynszem:", c["Koszt"][0]["KosztPlusMarzaKorekta"])
        print("Podstawa Marzy:", c["PodstawaMarzy"])
        print("Marza Na Kontrakcie PLN:", c["MarzaNaKontrakcie"])
        print("Marza Na Kontrakcie Procent:", c["MarzaNaKontrakcieProcent"])
    else:
        print("Cell not found.")

if __name__ == '__main__':
    main()
