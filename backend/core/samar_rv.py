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
from core.samar_rv_fetchers import (
    fetch_base_options_rate_cached,
    fetch_base_rv_percent_cached,
    fetch_brand_correction_cached,
    fetch_body_correction_cached,
    fetch_color_correction_cached,
    fetch_depreciation_rates_cached,
    fetch_lo_param_cached,
    fetch_mileage_corrections_cached,
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
            res = supabase.table("samar_classes").select("id, name").execute()
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

            Wzór z arkusza SOT JŁ (2503_wynik_JŁ.xlsx, KALKULATOR DH (dubel)):
              4Y baseline: BC = base_rate_4y (np. 0.39 dla CPb)
              WSTECZ (1Y-3Y): BC × (1 + delta) gdzie delta = tab_okres_final[km_<okres-1>k]
                              dla 3Y: BC × (1 + km_140000) — neutralne (delta=0)
                              dla 2Y: WR_3Y × (1 + km_105000)
                              dla 1Y: WR_2Y × (1 + km_70000)
              WPRZÓD (5Y-7Y): BC × (1 - delta) gdzie delta = tab_okres_final[km_<okres>k]
                              dla 5Y: BC × (1 - km_175000)
                              dla 6Y: WR_5Y × (1 - km_210000)
                              dla 7Y: WR_6Y × (1 - km_245000)

            Wcześniejsza implementacja używała sumy addytywnej delt (modifier_sum),
            co rozjeżdżało się drastycznie z SOT JŁ dla okresów ≠ 4Y (rozjazd
            +27% dla 3Y, -46% dla 7Y). Multiplikatywna kaskada daje 1:1 zgodność.
            """
            if yr < 1:
                yr = 1
            if yr > 7:
                yr = 7
            factor = 1.0
            if yr <= 4:
                # Kaskada wstecz z 4Y baseline (zmniejszamy rok, mnożymy przez (1+delta))
                for y_inner in range(4, yr, -1):
                    delta_col = ordered_keys[y_inner - 1]
                    factor *= 1.0 + float(mileage_rates.get(delta_col, 0.0))
            else:
                # Kaskada wprzód z 4Y baseline (zwiększamy rok, mnożymy przez (1-delta))
                for y_inner in range(5, yr + 1):
                    delta_col = ordered_keys[y_inner - 1]
                    factor *= 1.0 - float(mileage_rates.get(delta_col, 0.0))
            return base_rate_4y * factor

        years_exact = self.data.months / 12.0

        import math

        lower_yr = max(1, math.floor(years_exact))
        upper_yr = min(7, math.ceil(years_exact))

        if lower_yr == upper_yr:
            effective_base_pct = get_wr_percent_for_year(lower_yr)
        else:
            p_lower = get_wr_percent_for_year(lower_yr)
            p_upper = get_wr_percent_for_year(upper_yr)
            ratio = years_exact - lower_yr
            effective_base_pct = p_lower + ratio * (p_upper - p_lower)

        # FINALNY WSPÓŁCZYNNIK:
        effective_pct = effective_base_pct + brand_correction
        rv_base_netto = base_netto * effective_pct

        debug["krok1_years_exact"] = years_exact
        debug["krok1_interpolated_base_pct"] = effective_base_pct
        debug["krok1_brand_correction"] = brand_correction
        debug["krok1_effective_pct"] = effective_pct
        debug["krok1_wr_value_netto"] = round(rv_base_netto, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 3:  Ręczne ułamkowe WR doposażenia (Amortyzacja Opcji)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        options_rate = fetch_base_options_rate_cached(
            self.data.samar_class_id, self.data.engine_id, years
        )

        if options_rate > 0.0:
            # Stosujemy kaskadę deprecjacji dla opcji (uproszczoną do l. lat)
            # W V3 PARITY bierzemy po prostu stawkę bazową amortyzacji i ewentualnie ją skalujemy
            rv_options_netto = options_netto * options_rate
        else:
            divisor = 1.0 + years
            rv_options_netto = options_netto / divisor if divisor > 0 else options_netto

        rv_total_netto = rv_base_netto + rv_options_netto

        debug["krok3_years"] = years
        debug["krok3_rv_base_netto"] = round(rv_base_netto, 2)
        debug["krok3_rv_options_netto"] = round(rv_options_netto, 2)
        debug["krok3_rv_total_netto"] = round(rv_total_netto, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 4: Korekta przebiegu — NIEAKTYWNA (zgodność 1:1 z 2503 JŁ SOT)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Arkusz SOT JŁ (2503_wynik_JŁ.xlsx) oblicza korektę przebiegu (kolumna AK
        # = AI*(AD/10) + AJ*(AF/10)) ale formuła końcowa BV = BR + KOLOR*L + NADWOZIE*L
        # NIE zużywa AK. Czyli w SOT korekta przebiegu jest mathematycznie obliczana
        # ale nieaktywna. Tu replikujemy ten sam design — liczymy raw values do
        # debug trace, ale nie modyfikujemy rv_total_netto.
        #
        # Historycznie tu była aktywna korekta (paczki 10k pod/nad 190k z stawkami
        # under/over_rate z samar_class_mileage_corrections), ale dawała ona rozjazdy
        # ±10-30% vs 2503 SOT dla przebiegów nieproporcjonalnych. Decyzja biznesowa
        # 2026-05-16: zgodność z 2503 JŁ ma priorytet.
        under_rate, over_rate, threshold_km = self._fetch_mileage_corrections()

        base_mileage = (self.data.months / 12.0) * 35000.0
        przebieg_ponizej = min(self.data.total_km, threshold_km) - base_mileage
        przebieg_powyzej = max(self.data.total_km - threshold_km, 0.0)
        p1 = przebieg_ponizej / 10000.0
        p2 = przebieg_powyzej / 10000.0

        # Korekta NIEAKTYWNA — zachowujemy wyłącznie w trace dla audytu
        korekta_przebieg_netto = 0.0
        rv_netto_post_krok4 = rv_total_netto

        debug["krok4_base_mileage"] = base_mileage
        debug["krok4_threshold_km"] = threshold_km
        debug["krok4_przebieg_ponizej"] = przebieg_ponizej
        debug["krok4_przebieg_powyzej"] = przebieg_powyzej
        debug["krok4_p1"] = p1
        debug["krok4_p2"] = p2
        debug["krok4_under_rate"] = under_rate
        debug["krok4_over_rate"] = over_rate
        debug["krok4_korekta_przebieg_netto"] = 0.0
        debug["krok4_korekta_disabled_per_sot"] = True

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
