"""
Kalkulator Wartości Rezydualnej (SAMAR V3).

Algorytm:
  1. WR bazy = cena_bazowa x (WR_klasa% + korekta_marka%)
  2. Kaskadowa deprecjacja rok->rok (compound, 7 lat)
  3. RV opcji = opcje x stawka_opcji_per_rok[delta_lat]
  4. Korekta przebiegu
  5. Korekty: kolor, nadwozie (z zabudowa), rocznik
  6. Korekta reczna + wynik koncowy

Kluczowe tabele: samar_class_depreciation_rates,
                 samar_class_mileage_corrections,
                 body_types (kolumna utrata_wartosci), paint_types.

Moduly pomocnicze:
  - core.samar_rv_fetchers  -- cached DB fetchers + _normalize_fuel_name

"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from core.database import supabase
from core.supabase_retry import execute_with_retry
from core.samar_rv_fetchers import (
    fetch_base_options_rate_cached,
    fetch_base_rv_percent_cached,
    fetch_brand_correction_cached,
    fetch_body_correction_cached,
    fetch_color_correction_cached,
    fetch_depreciation_rates_cached,
    fetch_lo_param_cached,
    fetch_mileage_corrections_cached,
    fetch_resale_time_days_cached,
    fetch_vintage_correction_cached,
)

logger = logging.getLogger(__name__)

# ===============================================================
# Cache klasy SAMAR
# ===============================================================

_SAMAR_CACHE: Dict[str, int] = {}


def get_samar_class_id(class_name: str) -> Optional[int]:
    """Mapuje nazwę klasy SAMAR na ID z tabeli samar_classes. Wspiera formaty nowe i stare."""
    global _SAMAR_CACHE
    if not _SAMAR_CACHE:
        try:
            res = execute_with_retry(supabase.table("samar_classes").select("id, name"))
            for row in res.data or []:
                nazwa = str(row.get("name", "")).strip()
                row_id = int(row.get("id", 0))
                if nazwa:
                    _SAMAR_CACHE[nazwa.upper()] = row_id
        except Exception as exc:
            logger.warning("Błąd pobierania samar_classes: %s", exc)
            return None

    c_name = class_name.strip().upper()
    if c_name in _SAMAR_CACHE:
        return _SAMAR_CACHE[c_name]

    # Miękkie dopasowanie (Fuzzy Matching) dla starych stringów (np. "Podstawowa E WYŻSZA")
    import re

    # Usuwamy słowo KLASA i redukujemy spacje
    c_name_norm = (
        re.sub(r"\s+", " ", c_name).replace("KLASA ", "").replace("SAMAR: ", "")
    )
    search_norm = c_name_norm.replace("-", " ").replace("(SUV)", "").strip()

    for db_name, db_id in _SAMAR_CACHE.items():
        db_norm = db_name.replace("-", " ").replace("(SUV)", "").replace("KLASA ", "")
        db_norm = re.sub(r"\s+", " ", db_norm).strip()

        # 1. Dokładne dopasowanie po znormalizowaniu
        if db_norm == search_norm:
            _SAMAR_CACHE[c_name] = db_id
            return db_id

        # 2. Przecięcie słów kluczowych (np. brakuje spójnika w grupie)
        parts = search_norm.split()
        if all(p in db_norm for p in parts) and len(parts) >= 2:
            _SAMAR_CACHE[c_name] = db_id
            return db_id

    return None


@dataclass
class RVInput:
    """Dane wejściowe do kalkulacji RV."""

    samar_class_id: int
    engine_id: int
    engine_name: str = ""  # New field for exact silnik match in V3
    fuel_name: str = ""
    brand_name: str = ""
    model_name: str = ""
    months: int = 48
    total_km: int = 140000
    catalog_base_net: float = 0.0
    catalog_options_net: float = 0.0
    capex_base_net: float = 0.0  # Nowa zmienna dla utraty wartosci (CAPEX)
    capex_options_net: float = 0.0  # Nowa zmienna dla utraty wartosci (CAPEX opcje)
    paint_type_id: Optional[int] = None
    is_metalic: bool = True  # fallback when paint_type_id is None
    body_type_id: Optional[int] = None
    rocznik: str = "current"
    zabudowa_apr_wr: bool = False
    zabudowa_type_id: Optional[int] = None
    manual_wr_correction: float = 0.0


@dataclass
class RVOutput:
    """Wynik kalkulacji RV."""

    wr_net: float = 0.0
    wr_lo_net: float = 0.0
    utrata_wartosci_net: float = 0.0
    wr_percent: float = 0.0
    debug: Dict[str, Any] = field(default_factory=dict)


class SamarRVCalculator:
    """Kalkulator Wartości Rezydualnej oparty na tabelach SAMAR.

    Wiernie odtwarza algorytm z Excela JŁ (KALKULATOR DH):
      1. WR bazy = cena_bazowa × (WR_klasa% + korekta_marka%)
      2. Kaskadowa deprecjacja rok→rok (compound, 7 lat)
      3. RV opcji = opcje × stawka_opcji[delta_lat]
      4. Korekta przebiegu
      5. Korekty: kolor, nadwozie, rocznik
      6. Korekta ręczna
    """

    LICZBA_LAT: int = 7  # ZAWSZE przelicz przez 7 lat (gemini.md §5)

    def __init__(self, rv_input: RVInput) -> None:
        self.data = rv_input

    # ── Fetchery danych z DB ──────────────────────────────────────

    def _fetch_base_rv_percent(self) -> float:
        """Pobiera 4-letnią bazę dla klasy + silnika (samar_class_base_rv)."""
        return fetch_base_rv_percent_cached(
            self.data.samar_class_id, self.data.engine_id
        )

    def _fetch_depreciation_rates(self) -> Dict[str, float]:
        """Pobiera mnożniki przyrostów modyfikujących (delta) z tab_okres_final (V3)."""
        engine_name = self.data.engine_name or self.data.fuel_name or "BENZYNA"
        rates = fetch_depreciation_rates_cached(
            self.data.samar_class_id, self.data.brand_name, engine_name
        )
        if not rates:
            raise ValueError(
                f"Brak rekordów z tabeli tab_okres_final (delta) dla klasy={self.data.samar_class_id}, silnik={engine_name}"
            )
        return rates

    def _fetch_brand_correction(self) -> float:
        """Korekta za markę z samar_brand_corrections (V3)."""
        brand = self.data.brand_name.strip().upper()
        model = self.data.model_name.strip().upper() if self.data.model_name else ""
        engine_name = self.data.engine_name or self.data.fuel_name or "BENZYNA"
        return fetch_brand_correction_cached(
            self.data.samar_class_id, brand, model, engine_name
        )

    def _fetch_mileage_corrections(self) -> tuple[float, float, int]:
        """Stawki korekty przebiegu: (below, above, threshold)."""
        engine_name = self.data.engine_name or self.data.fuel_name or "BENZYNA"
        return fetch_mileage_corrections_cached(
            self.data.samar_class_id, self.data.brand_name, engine_name
        )

    def _fetch_base_options_rate(self, years: int) -> float:
        """Stawka amortyzacji opcji per rok z samar_class_options_rv (2005 SOT)."""
        return fetch_base_options_rate_cached(
            self.data.samar_class_id, self.data.engine_id, years
        )

    def fetch_color_correction(self) -> float:
        """Korekta za kolor z paint_types.wr_correction."""
        return fetch_color_correction_cached(
            self.data.paint_type_id, self.data.is_metalic
        )

    def fetch_body_correction(self) -> float:
        """Korekta WR per typ nadwozia (z body_types.utrata_wartosci).

        Composite cabin+zabudowa name (np. "Podwozie Brygadowe Skrzynia") jest
        pojedynczym body_type, więc korekta pokrywa też zabudowę.
        """
        return fetch_body_correction_cached(self.data.body_type_id)

    def fetch_vintage_correction(self) -> float:
        """Korekta za rocznik z ltr_admin_korekta_wr_roczniks (per klasa SAMAR)."""
        return fetch_vintage_correction_cached(
            self.data.rocznik, self.data.samar_class_id
        )

    def fetch_lo_param(self) -> float:
        """PrzewidywanaCenaSprzedazyLO z control_center (kolumna)."""
        return fetch_lo_param_cached()

    def _calculate_liczba_lat_v1(self) -> int:
        """V1 RMS calendar-year-diff for cascade selection.

        Replicates `LTRSubCalculatorUtrataWartosciNew.CalculateWiekSamochodu`:
            dataZakonczeniaKontraktu = dataKalkulacji.AddMonths(okresUzytkowania)
                                        .AddMonths(czasPrzygotowaniaDoSprzedazy);
            liczbaLat = dataZakonczeniaKontraktu.Year - dataKalkulacji.Year;

        Reads `flota.resale_time_days` from control_center (EAV). Default 60 days
        (~2 months) per current production config. Converts days→months as
        round(days / 30) to match C# `.AddMonths(int)` semantics.
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta

        # Cache'owane — czytane raz na komórkę matrycy (patrz fetcher docstring).
        resale_days = fetch_resale_time_days_cached()
        prep_months = round(resale_days / 30)

        today = date.today()
        end_date = today + relativedelta(months=self.data.months + prep_months)
        return end_date.year - today.year

    def calculate(self) -> RVOutput:
        """Oblicza RV wg algorytmu Excel JŁ (6 kroków)."""
        debug: Dict[str, Any] = {}

        # ── Pobranie danych ──
        rates = self._fetch_depreciation_rates()

        if not rates:
            raise ValueError(
                f"Brak stawek deprecjacji w tabeli `samar_class_depreciation_rates` "
                f"dla klasy {self.data.samar_class_id} "
                f"(marka: {self.data.brand_name}, model: {self.data.model_name}). "
                f"Kalkulacja zatrzymana (Reguła Fail-Fast)."
            )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # V1 PARITY: Przeliczenia per se operowały na wartościach Netto przed rabatem (Katalog)
        # Cena Katalogowa "goła" (często z opcjami jako całość, wedle wejścia V1)
        # jest deprecjonowana przez tabele, ale Opcje starzały się OSOBNO ułamkowo.
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        base_netto = self.data.catalog_base_net
        options_netto = self.data.catalog_options_net

        # Przybliżenie dniowe stosowane w modelu Excelowym (~30.5 dnia)
        years = int((self.data.months * 30.5) / 365)
        years = max(0, min(years, self.LICZBA_LAT))

        # V1 RMS calendar-year-diff (per LTRSubCalculatorUtrataWartosciNew.cs:111-117):
        #   liczbaLat = (today.AddMonths(okres + czasPrzygotowania)).Year - today.Year
        # czasPrzygotowania jest w MIESIĄCACH w V1; control_center.flota.resale_time_days
        # przechowuje to w DNIACH. Konwertujemy days→months używając 30 dni/mc (V1 .AddMonths(int)).
        liczba_lat_v1 = self._calculate_liczba_lat_v1()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 1 & 2: ODCZYT BAZY I WYLICZENIE DELT Z tab_okres_final
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        brand_correction = self._fetch_brand_correction()
        base_rate_4y = (
            self._fetch_base_rv_percent()
        )  # Pobrane dla 4 lat (140,000 km) z samar_class_base_rv

        mileage_rates = rates  # Słownik pobrany z tab_okres_final
        if not mileage_rates:
            raise ValueError(
                f"Brak stawek w tab_okres_final dla klasy {self.data.samar_class_id}"
            )

        ordered_keys = [
            "km_35000",
            "km_70000",
            "km_105000",
            "km_140000",
            "km_175000",
            "km_210000",
            "km_245000",
        ]
        base_key = "km_140000"
        base_idx = ordered_keys.index(base_key)

        def get_wr_percent_for_year(yr: int) -> float:
            """Oblicza WR% per rok (1-7) wg multiplikatywnej kaskady z 4Y baseline.

            Formuła (post 2026-05-17 off-by-one fix dla zgodności V1 RMS):
              4Y baseline: BC = base_rate_4y (np. 0.36 dla DPb)
              WSTECZ (1Y-3Y): kaskada cofa rok-po-roku, używając delty dla
                              ROKU DOCELOWEGO (year_destination):
                              Y3 = Y4 × (1 + delta_year_3)   gdzie delta_year_3 = km_105000
                              Y2 = Y3 × (1 + delta_year_2)   gdzie delta_year_2 = km_70000
                              Y1 = Y2 × (1 + delta_year_1)   gdzie delta_year_1 = km_35000
              WPRZÓD (5Y-7Y): kaskada idzie wprzód, używając delty dla
                              ROKU AKTUALNEGO:
                              Y5 = Y4 × (1 - delta_year_5)   gdzie delta_year_5 = km_175000
                              Y6 = Y5 × (1 - delta_year_6)   gdzie delta_year_6 = km_210000
                              Y7 = Y6 × (1 - delta_year_7)   gdzie delta_year_7 = km_245000

            BUGFIX 2026-05-17: poprzednio kaskada WSTECZ używała ordered_keys[y_inner-1]
            zamiast [y_inner-2], przez co Y3 dostawała delta z km_140000 (=0 baseline
            marker) zamiast km_105000 (właściwa Y3 delta). To zmieniało Y3 z
            ~40.9% catalog na płaskie 36% catalog — niezgodne z V1 RMS. Po fixie
            Y2/Y3/Y4/Y5 są zgodne z V1 sweep 172207 dla Octavii (cascade per okres).
            """
            if yr < 1:
                yr = 1
            if yr > 7:
                yr = 7
            factor = 1.0
            if yr <= 4:
                # Kaskada wstecz: dla każdego kroku wstecz (Y_n → Y_(n-1)) używamy
                # delty dla roku docelowego (n-1). Indeks: ordered_keys[(n-1)-1] = [n-2].
                for y_inner in range(4, yr, -1):
                    year_dest = y_inner - 1  # destination year of this cascade step
                    delta_col = ordered_keys[year_dest - 1]  # km marker for that year
                    factor *= 1.0 + float(mileage_rates.get(delta_col, 0.0))
            else:
                # Kaskada wprzód: dla każdego kroku w przód (Y_n → Y_(n+1)) używamy
                # delty dla roku docelowego (n+1). Indeks: ordered_keys[(n+1)-1] = [n].
                # y_inner pełni rolę year_destination tutaj.
                for y_inner in range(5, yr + 1):
                    delta_col = ordered_keys[y_inner - 1]
                    factor *= 1.0 - float(mileage_rates.get(delta_col, 0.0))
            return base_rate_4y * factor

        # V1 RMS uses INTEGER calendar-year-diff (liczbaLat) for cascade selection
        # — NO interpolation. Per LTRSubCalculatorUtrataWartosciNew.cs:73-109.
        # For round-12 okres (24/36/48/60mc) this gives the same result as
        # months/12, but for non-round okres it picks the integer cascade step.
        liczba_lat = max(1, min(liczba_lat_v1, 7))
        effective_base_pct = get_wr_percent_for_year(liczba_lat)

        # FINALNY WSPÓŁCZYNNIK:
        effective_pct = effective_base_pct + brand_correction
        rv_base_netto = base_netto * effective_pct

        debug["krok1_liczba_lat_v1"] = liczba_lat
        debug["krok1_interpolated_base_pct"] = effective_base_pct
        debug["krok1_brand_correction"] = brand_correction
        debug["krok1_effective_pct"] = effective_pct
        debug["krok1_wr_value_netto"] = round(rv_base_netto, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 3:  Amortyzacja Opcji — Path A (2005 Excel SOT)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2005 SOT (arkusz TAB.DOPOSAŻENIA, kolumna BC51): opcje amortyzują się
        # WŁASNĄ stawką per rok z `samar_class_options_rv` — NIE stawką bazy.
        # Dla klasy C / Benzyna PB / rok 4 = 0.24. Po tej zmianie rv_total == BE
        # z Excela (base×0.39 + opcje×0.24), więc baza korekty przebiegu się zgadza.
        # (Wcześniej "Path B" = options × base_pct dla V1 RMS parity — porzucone
        # decyzją usera 2026-05-21: 2005 Excel = SOT kalkulatora WR.)
        # Opcje: osobna stawka per rok (Path A). Pobieramy tylko gdy auto MA opcje —
        # pojazd bez doposażenia nie może zależeć od samar_class_options_rv.
        # _fetch_base_options_rate jest Fail-Fast (raise przy braku rekordu).
        options_rate = (
            self._fetch_base_options_rate(liczba_lat) if options_netto > 0 else 0.0
        )
        rv_options_netto = options_netto * options_rate
        rv_total_netto = rv_base_netto + rv_options_netto

        debug["krok3_years"] = years
        debug["krok3_rv_base_netto"] = round(rv_base_netto, 2)
        debug["krok3_rv_options_netto"] = round(rv_options_netto, 2)
        debug["krok3_rv_total_netto"] = round(rv_total_netto, 2)
        debug["krok3_options_rate_used"] = options_rate

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 4: Korekta przebiegu — V1 RMS parity formula
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # V1 RMS formula (zweryfikowana na 7 punktach sweep'u KALK 172207 Octavia):
        #   baseline = 140_000 km **STAŁA** (NIE okres × 35k/12 — niezależna od okresu)
        #   threshold = 190_000 km
        #   paczki_lt = (od baseline do threshold lub poniżej baseline) / 10k
        #   paczki_gt = (powyżej threshold) / 10k
        #   znak: + gdy actual > baseline (penalty, odejmuje od WR), − gdy < (bonus, dodaje)
        #
        # Korekta jest WYŁĄCZONA dla nadwozi z `body_types.utrata_wartosci != 0`
        # (np. Furgon Brygadowy = 0.4) — tam mileage correction jest zbundlowana w body
        # correction (memory `body_types_sot`). Dla normalnych nadwozi (Kombi, Sedan,
        # Hatchback z utrata_wartosci=0.0) Krok 4 aktywny.
        #
        # Historycznie wyłączony per 2503 SOT (Excel TAB.PRZEBIEG nieaktywne w końcowej
        # formule BV). Decyzja 2026-05-17: priorytet V1 RMS parity nad Excel 2503 SOT.
        under_rate, over_rate, threshold_km = self._fetch_mileage_corrections()
        body_correction_pct_for_krok4 = self.fetch_body_correction()
        krok4_active = abs(body_correction_pct_for_krok4) < 1e-6  # 0.0 → aktywny

        # V1 RMS baseline = 140_000 km STAŁA
        V1_BASELINE_KM = 140_000.0
        excess_km = float(self.data.total_km) - V1_BASELINE_KM

        if excess_km > 0:
            # Powyżej baseline → penalty (odejmie od WR)
            paczki_lt_kor = min(excess_km, threshold_km - V1_BASELINE_KM) / 10_000.0
            paczki_gt_kor = max(excess_km - (threshold_km - V1_BASELINE_KM), 0.0) / 10_000.0
            korekta_sign = 1.0  # deduct
        else:
            # Poniżej baseline → bonus (doda do WR)
            paczki_lt_kor = abs(excess_km) / 10_000.0
            paczki_gt_kor = 0.0
            korekta_sign = -1.0  # add

        korekta_przebieg_netto = (
            paczki_lt_kor * under_rate + paczki_gt_kor * over_rate
        ) * rv_total_netto

        if krok4_active:
            rv_netto_post_krok4 = rv_total_netto - korekta_sign * korekta_przebieg_netto
        else:
            rv_netto_post_krok4 = rv_total_netto
            korekta_przebieg_netto = 0.0

        debug["krok4_baseline_km"] = V1_BASELINE_KM
        debug["krok4_threshold_km"] = threshold_km
        debug["krok4_excess_km"] = excess_km
        debug["krok4_paczki_lt"] = paczki_lt_kor
        debug["krok4_paczki_gt"] = paczki_gt_kor
        debug["krok4_under_rate"] = under_rate
        debug["krok4_over_rate"] = over_rate
        debug["krok4_korekta_sign"] = korekta_sign
        debug["krok4_korekta_przebieg_netto"] = round(korekta_sign * korekta_przebieg_netto, 2)
        debug["krok4_active"] = krok4_active
        # Per CLAUDE.md "Golden Rule" — emit the spec-named flag so external
        # consumers (parity tests, debug surfaces) can rely on a stable key:
        # 1.0 ↔ Krok 4 disabled because body type has its own utrata_wartosci.
        debug["krok4_korekta_disabled_per_sot"] = 0.0 if krok4_active else 1.0
        debug["krok4_body_correction_pct"] = body_correction_pct_for_krok4

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 5: Korekta administracyjna (Zgodność V3)
        # W nowym modelu procentowa stawka za kolor uderza wyłącznie
        # w "gołą" cenę katalogową samochodu (bez opcji).
        # Wyliczona sztywna kwota jest addytywnie dodawana do głównej puli WR.
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        color_correction_pct = self.fetch_color_correction()
        body_correction_pct = self.fetch_body_correction()
        catalog_total_netto = base_netto + options_netto

        color_value_netto = color_correction_pct * base_netto
        body_value_netto = body_correction_pct * base_netto

        korekta_admin_sum_netto = color_value_netto + body_value_netto

        rv_netto_pre_manual = rv_netto_post_krok4 + korekta_admin_sum_netto

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 6: Korekta za Rocznik oraz na samym końcu Korekta Ręczna (V3 PARITY z Excelem)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Korekta za rocznik jest addytywną wartością liczoną od ceny katalogowej (catalog_total)
        vintage_correction_pct = self.fetch_vintage_correction()
        vintage_value_netto = catalog_total_netto * vintage_correction_pct

        rv_z_rocznikiem_netto = rv_netto_pre_manual + vintage_value_netto

        # Korekta ręczna "z palca" znajduje się na samym końcu logicznego potoku
        manual_correction_netto = self.data.manual_wr_correction
        final_rv_netto = rv_z_rocznikiem_netto + manual_correction_netto

        debug["krok5_color_netto"] = round(color_value_netto, 2)
        debug["krok5_body_netto"] = round(body_value_netto, 2)
        debug["krok5_korekta_admin_sum_netto"] = round(korekta_admin_sum_netto, 2)
        debug["krok5_color_correction_pct"] = color_correction_pct
        debug["krok5_body_correction_pct"] = body_correction_pct
        debug["krok5_rv_netto_pre_manual"] = round(rv_netto_pre_manual, 2)
        debug["krok6_vintage_pct"] = vintage_correction_pct
        debug["krok6_vintage_netto"] = round(vintage_value_netto, 2)
        debug["krok6_manual_correction_netto"] = manual_correction_netto
        debug["krok6_final_rv_netto"] = round(final_rv_netto, 2)

        # WRdlaLO
        lo_param = self.fetch_lo_param()
        wr_lo_netto = final_rv_netto * (1.0 + lo_param)

        # Utrata wartości jest różnicą pomiędzy prawdziwymi kosztami zakupu (CAPEX z rabatami)
        # powiększonymi o opcje netto, a Wartością Rezydualną obliczoną powyżej z ceny katalogowej.
        capex_total = self.data.capex_base_net + self.data.capex_options_net
        # V1 Parity Fallback: If capex is missing (legacy API call), substitute with catalog value.
        if capex_total <= 0:
            capex_total = catalog_total_netto

        utrata = max(capex_total - final_rv_netto, 0.0)
        wr_pct = (
            final_rv_netto / catalog_total_netto if catalog_total_netto > 0 else 0.0
        )

        debug["krok6_capex_total"] = round(capex_total, 2)
        debug["krok6_utrata"] = round(utrata, 2)
        debug["krok6_wr_pct"] = round(wr_pct, 4)

        return RVOutput(
            wr_net=final_rv_netto,
            wr_lo_net=wr_lo_netto,
            utrata_wartosci_net=utrata,
            wr_percent=wr_pct,
            debug=debug,
        )

    # (cached functions are defined in core.samar_rv_fetchers for @redis_cache)
