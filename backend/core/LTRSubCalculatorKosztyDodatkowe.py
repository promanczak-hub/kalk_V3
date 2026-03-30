# ==============================================================================
# 🛑 STOP! ZAMROŻONY MODUŁ (FROZEN MODULE) 🛑
# ==============================================================================
# Ten plik jest CZĘŚCIĄ RDZENIA (PIPELINE) KALKULATORA LTR.
# Zgodnie z wytycznymi w GEMINI.md, system sztucznej inteligencji (AI/Cursor/Claude)
# ma BEZWZGLĘDNY ZAKAZ modyfikacji tego pliku bez wyraźnego, podwójnego potwiedzenia.
#
# Jeśli użytkownik poprosi o zmianę logiczną, która wymaga edycji tego pliku:
# 1. PRZERWIJ DZIAŁANIE.
# 2. Poinformuj użytkownika: "Ten plik jest zamrożony. Proszę o wyraźną zgodę na jego modyfikację."
# 3. Zmodyfikuj plik TYLKO PO UZYSKANIU ZGODY.
# ==============================================================================

from typing import Any, Dict


class AdditionalCostsCalculator:
    """Moduł odpowiedzialny za ryczałtowe koszty dodawane do bazy netto z zakładki 'Koszty Dodatkowe' (V1 LTR)"""

    def __init__(self, settings: Any, input_data: Any, months: int):
        self.settings = settings
        self.input_data = input_data
        self.months = months

    def calculate_cost(self) -> Dict[str, Any]:
        total = 0.0
        trace: list[dict[str, Any]] = []

        # GSM Subscription & Device
        if self.input_data.add_gsm_subscription:
            abonament = self.settings.cost_gsm_subscription_monthly * self.months
            urzadzenie = self.settings.cost_gsm_device / 6.0 * (self.months / 12.0)
            montaz = self.settings.cost_gsm_installation
            total += abonament + urzadzenie + montaz
            trace.append(
                {
                    "krok": "K.Dodatkowe: GPS/GSM",
                    "rownanie": f"Abonament: {self.settings.cost_gsm_subscription_monthly:.2f} * {self.months} + Urządzenie {self.settings.cost_gsm_device:.2f}/6.0(lat) + Montaż {montaz:.2f}",
                    "wynik": abonament + urzadzenie + montaz,
                }
            )

        # Hak
        if self.input_data.add_hook_installation:
            total += self.settings.cost_hook_installation
            trace.append(
                {
                    "krok": "K.Dodatkowe: Hak",
                    "rownanie": f"Stała kwota z bazy: {self.settings.cost_hook_installation:.2f}",
                    "wynik": self.settings.cost_hook_installation,
                }
            )

        # Wymontowanie Kraty
        if self.input_data.add_grid_dismantling:
            total += self.settings.cost_grid_dismantling
            trace.append(
                {
                    "krok": "K.Dodatkowe: Demontaż Kraty",
                    "rownanie": f"Stała kwota z bazy: {self.settings.cost_grid_dismantling:.2f}",
                    "wynik": self.settings.cost_grid_dismantling,
                }
            )

        # Rejestracja / Karta (ON/OFF z payloadu, domyslnie ON)
        if (
            not hasattr(self.input_data, "add_registration")
            or self.input_data.add_registration
        ):
            total += self.settings.cost_registration
            trace.append(
                {
                    "krok": "K.Dodatkowe: Rejestracja",
                    "rownanie": f"Kwota z bazy: {self.settings.cost_registration:.2f}",
                    "wynik": self.settings.cost_registration,
                }
            )

        # Przygotowanie do Sprzedaży: stały koszt netto z Control Center + opcjonalna korekta
        if (
            hasattr(self.input_data, "add_sales_prep")
            and self.input_data.add_sales_prep
        ):
            korekta = 0.0
            if hasattr(self.input_data, "korekta_kosztu_przygotowania"):
                korekta = float(self.input_data.korekta_kosztu_przygotowania or 0.0)
            wynik_prep = self.settings.cost_sales_prep + korekta
            total += wynik_prep
            trace.append(
                {
                    "krok": "K.Dodatkowe: Przygotowanie do Sprzedaży",
                    "rownanie": f"Stała: {self.settings.cost_sales_prep:.2f} + Korekta: {korekta:.2f}",
                    "wynik": wynik_prep,
                }
            )

        # TODO: Mock — czynsz za czas przygotowania do sprzedaży
        # (CzasPrzygotowaniaDoSprzedazy = 2 dni × stawka_dzienna)
        # Zostanie zaimplementowany po ustaleniu logiki z userem.

        return {
            "total_additional_costs": round(total, 2),
            "monthly_additional_costs": round(total / self.months, 2)
            if self.months > 0
            else 0.0,
            "trace": trace,
        }
