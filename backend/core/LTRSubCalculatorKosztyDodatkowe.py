from typing import Dict, Any, Optional
from core.database import supabase


class LTRSubCalculatorKosztyDodatkowe:
    """Moduł odpowiedzialny za kalkulację kosztów dodatkowych zgodnie z V1 (LTRSubCalculatorKosztyDodatkowe.cs)."""

    def __init__(
        self,
        okres_uzytkowania: int,
        przebieg: int,
        czy_gps: bool,
        is_demontaz: bool,  # Demontaż kratki
        hak: bool,
        # Identyfikacja pojazdu
        klasa_pojazdu: Optional[
            str
        ],  # np. 'C', 'D' dla zniżek na LTRAdminKategoriaKorekta
        klasa_id: Optional[int],
        typ_zabudowy: Optional[str],
        linia_produktowa: str = "LTR",  # "LTR" lub "RacMTR"
        # Opcjonalne manualne korekty narzucane ryczałtem na froncie
        korekta_kosztu_przygotowania: bool = False,
        koszt_przygotowania_korekta: float = 0.0,
    ):
        self.okres = okres_uzytkowania
        self.przebieg = przebieg
        self.czy_gps = czy_gps
        self.is_demontaz = is_demontaz
        self.hak = hak

        self.klasa_pojazdu = klasa_pojazdu
        self.klasa_id = klasa_id
        self.typ_zabudowy = typ_zabudowy
        self.linia_produktowa = linia_produktowa

        self.korekta_kosztu_przygotowania = korekta_kosztu_przygotowania
        self.koszt_przygotowania_korekta = koszt_przygotowania_korekta

        # Parametry globalne (defaulty zgodne z historycznymi danymi gdyby baza padła)
        self.vat_rate = self._fetch_global_param("StawkaVAT", 1.23)
        self.zarejestrowanie_karta_pojazdu = self._fetch_global_param(
            "ZarejestrowanieKartaPojazdu", 350.0
        )
        self.koszt_wymontowania_kraty = self._fetch_global_param(
            "KosztWymontowaniaKraty", 500.0
        )
        self.hak_holowniczy_koszt = self._fetch_global_param("HakHolowniczy", 1500.0)
        self.cena_urzadzenia_gsm = self._fetch_global_param("CenaUrzadzeniaGSM", 700.0)
        self.montaz_urzadzenia_gsm = self._fetch_global_param(
            "MontazUrzadzeniaGSM", 150.0
        )
        self.przygotowanie_sprzedaz_ltr = self._fetch_global_param(
            "PrzygotowanieDoSprzedazyLtr", 500.0
        )
        self.przygotowanie_sprzedaz_racmtr = self._fetch_global_param(
            "PrzygotowanieDoSprzedazyRacMtr", 400.0
        )

    def _fetch_global_param(self, param_name: str, fallback: float) -> float:
        """Pobiera parametry globalne (np. StawkaVAT, ZarejestrowanieKartaPojazdu) z bazy strumienia czak."""
        try:
            response = (
                supabase.table("LTRAdminParametry_czak")
                .select("col_2")
                .eq("col_1", param_name)
                .limit(1)
                .execute()
            )
            if response.data and isinstance(response.data, list) and len(response.data) > 0:
                row = response.data[0]
                if isinstance(row, dict):
                    val = row.get("col_2")
                    if val is not None:
                        return float(str(val).replace(",", "."))
        except Exception as e:
            print(f"Error fetching param {param_name}: {e}")
        return fallback

    def _get_abonament_gsm(self) -> float:
        """Kalkulacja kosztu abonamentu i instazlacji GSM jeśli włączono Opcję."""
        if not self.czy_gps:
            return 0.0

        # TODO: Dynamika z tabeli LTRAdminGSM_czak zależnie od symbolu modelu, tu nałożymy uproszczony fallback 39 Netto / miesiąc
        abonament_miesieczny = 39.0

        if abonament_miesieczny <= 0.0:
            return 0.0

        # Wzór V1: result = abonament * okresUzytkowania + cenaUrzadzenia / 6m * okresUzytkowania / 12m + montazUrzadzenia;
        koszt_urzadzenia_rozlozony = (self.cena_urzadzenia_gsm / 6.0) * (
            self.okres / 12.0
        )
        total_gsm = (
            (abonament_miesieczny * self.okres)
            + koszt_urzadzenia_rozlozony
            + self.montaz_urzadzenia_gsm
        )

        return total_gsm

    def _get_koszty_dodatkowe_zabudowy(self) -> float:
        """Koszty wynikające z typu zabudowy pojazdu dostawczego (np. chłodnia, plandeka)."""
        if not self.klasa_id or not self.typ_zabudowy:
            return 0.0

        # Oczekujemy istnienia w Supabase tabeli LTRAdminKosztZabudowy_czak
        try:
            response = (
                supabase.table("LTRAdminKosztZabudowy_czak")
                .select("KosztyDodatkoweNettoRok")
                .eq("KlasaId", self.klasa_id)
                .eq("TypZabudowy", self.typ_zabudowy)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                roczny_koszt = float(
                    response.data[0].get("KosztyDodatkoweNettoRok", 0.0)
                )
                return (self.okres / 12.0) * roczny_koszt
        except Exception:
            pass

        return 0.0

    def _get_korekta_for_klasa(self) -> float:
        """Współczynnik klasy auta dla LTR (z LTRAdminKategoriaKorekta_czak)."""
        if not self.klasa_pojazdu:
            return 1.0

        try:
            response = (
                supabase.table("LTRAdminKategoriaKorekta_czak")
                .select("WspolczynnikKorektyProcent")
                .eq("Kategoria", self.klasa_pojazdu)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                val = response.data[0].get("WspolczynnikKorektyProcent")
                if val is not None:
                    return float(str(val).replace(",", "."))
        except Exception:
            pass
        return 1.0

    def _get_korekta_for_przebieg(self) -> float:
        """Współczynnik przebiegu auta dla LTR (z LTRAdminPrzebiegKorekta_czak).
        Zwraca korektę dla pierwszego przebiegu <= target_przebieg (posortowane malejąco w V1, tutaj uproszczenie do >=)."""
        try:
            # W V1: OrderByDescending(Przebieg) -> FirstOrDefault(k => k.Przebieg <= przebieg)
            response = (
                supabase.table("LTRAdminPrzebiegKorekta_czak")
                .select("Przebieg, WspolczynnikKorektyProcent")
                .lte("Przebieg", self.przebieg)
                .order("Przebieg", desc=True)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                val = response.data[0].get("WspolczynnikKorektyProcent")
                if val is not None:
                    return float(str(val).replace(",", "."))
            else:
                # Fallback: Weź element z na samym dole (LastOrDefault - czyli tu najmniejszy przebieg)
                response = (
                    supabase.table("LTRAdminPrzebiegKorekta_czak")
                    .select("WspolczynnikKorektyProcent")
                    .order("Przebieg", desc=False)
                    .limit(1)
                    .execute()
                )
                if response.data and len(response.data) > 0:
                    val = response.data[0].get("WspolczynnikKorektyProcent")
                    if val is not None:
                        return float(str(val).replace(",", "."))
        except Exception:
            pass
        return 1.0

    def _calculate_przygotowanie_do_sprzedazy(self) -> float:
        result = 1.0
        if self.linia_produktowa == "LTR":
            # Korekty występują tylko w segmencie LTR
            korekta_klasa = self._get_korekta_for_klasa()
            korekta_przebieg = self._get_korekta_for_przebieg()
            result = korekta_klasa * korekta_przebieg * self.przygotowanie_sprzedaz_ltr
        else:
            # Prawopodobnie RacMtr
            result = self.przygotowanie_sprzedaz_racmtr

        if self.korekta_kosztu_przygotowania:
            # Manualny Override zdejmujący VAT
            result += self.koszt_przygotowania_korekta / self.vat_rate

        return result

    def get_elementy_ryczaltowe(self) -> float:
        """Tutaj umieszczamy dodatkowe ryczałty ze starych list V1 - w tym momencie mock na 0.0"""
        # Dla V1 iterowano tablicę ElementyRyczaltowe po StawkaMiesiecznaNetto lub StawkaZa10TysKmNetto
        return 0.0

    def calculate_cost(self) -> Dict[str, Any]:
        """Główna metoda łącząca koszty w jedną sumę na wzór Policz() w C#."""
        abonament_gsm = self._get_abonament_gsm()
        przygotowanie = self._calculate_przygotowanie_do_sprzedazy()
        rejestracja = self.zarejestrowanie_karta_pojazdu
        elementy_ryczaltowe = self.get_elementy_ryczaltowe()
        koszty_zabudowy = self._get_koszty_dodatkowe_zabudowy()

        demontaz = self.koszt_wymontowania_kraty if self.is_demontaz else 0.0
        koszt_hak = self.hak_holowniczy_koszt if self.hak else 0.0

        total_koszty_dodatkowe = sum(
            [
                abonament_gsm,
                przygotowanie,
                rejestracja,
                elementy_ryczaltowe,
                koszty_zabudowy,
                demontaz,
                koszt_hak,
            ]
        )

        return {
            "abonament_gsm": abonament_gsm,
            "przygotowanie_do_sprzedazy": przygotowanie,
            "rejestracja": rejestracja,
            "demontaz_kraty": demontaz,
            "hak_holowniczy": koszt_hak,
            "elementy_ryczaltowe": elementy_ryczaltowe,
            "koszty_zabudowy": koszty_zabudowy,
            "total_koszty_dodatkowe_netto": total_koszty_dodatkowe,
        }
