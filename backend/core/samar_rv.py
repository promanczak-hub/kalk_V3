"""
Kalkulator Wartości Rezydualnej (SAMAR V3).

Algorytm wiernie odtwarza formułę z Excela JŁ (KALKULATOR DH):
  1. WR bazy = cena_bazowa × (WR_klasa% + korekta_marka%)
  2. Kaskadowa deprecjacja rok→rok (compound, 7 lat)
  3. RV opcji = opcje × stawka_opcji_per_rok[delta_lat]
  4. Korekta przebiegu (2 pasma: ≤ próg / > próg nadprzebiegu)
  5. Korekty: kolor, nadwozie (z zabudową), rocznik
  6. Korekta ręczna + wynik końcowy

Klucze w DB: samar_class_id (INT FK) + engine_id (INT FK).
Tabele: samar_class_depreciation_rates, samar_class_mileage_corrections,
        ltr_admin_korekta_wr_markas, body_type_wr_corrections,
        paint_types, ltr_admin_korekta_wr_roczniks.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Optional, cast

from core.database import supabase

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Cache klasy SAMAR
# ═══════════════════════════════════════════════════════════════════

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
    c_name_norm = re.sub(r"\s+", " ", c_name).replace("KLASA ", "")
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


# ═══════════════════════════════════════════════════════════════════
# Readiness Check
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ReadinessItem:
    """Wynik sprawdzenia jednego parametru."""

    param: str
    status: str  # "ok", "warn", "error"
    value: str = ""


def check_rv_readiness(
    samar_class_id: int,
    engine_id: int,
    brand_name: str,
    body_type_id: Optional[int],
    paint_type_id: Optional[int],
    rocznik: str,
    model_name: str = "",
) -> list[ReadinessItem]:
    """Sprawdza pokrycie parametrów w DB przed kalkulacją."""
    checks: list[ReadinessItem] = []

    # 1. WR bazy + deprecjacja (ta sama tabela samar_class_depreciation_rates)
    try:
        res = (
            supabase.table("samar_class_depreciation_rates")
            .select("year, base_depreciation_percent")
            .eq("samar_class_id", samar_class_id)
            .eq("fuel_type_id", engine_id)
            .execute()
        )
        rows = res.data or []
        years_found = len(rows)
        # Szukamy WR bazy (year=0)
        base_row = next((r for r in rows if int(r["year"]) == 0), None)

        if base_row and years_found >= 8:
            pct = float(base_row["base_depreciation_percent"]) * 100
            checks.append(
                ReadinessItem(
                    "WR bazy (klasa×silnik)",
                    "ok",
                    f"{pct:.0f}%, {years_found} lat",
                )
            )
        elif base_row:
            pct = float(base_row["base_depreciation_percent"]) * 100
            checks.append(
                ReadinessItem(
                    "WR bazy (klasa×silnik)",
                    "warn",
                    f"{pct:.0f}%, tylko {years_found} lat",
                )
            )
        else:
            checks.append(
                ReadinessItem("WR bazy (klasa×silnik)", "error", "brak wpisu")
            )
    except Exception:
        checks.append(ReadinessItem("WR bazy (klasa×silnik)", "error", "błąd DB"))

    # 3. Korekta marka (z kaskadą na model)
    try:
        model = model_name.strip().upper() if model_name else ""
        brand = brand_name.strip().upper()
        found_val = None
        found_type = ""

        # Exact match with model
        if model:
            res_ex = (
                supabase.table("ltr_admin_korekta_wr_markas")
                .select("korekta_procent")
                .eq("samar_class_id", samar_class_id)
                .eq("rodzaj_paliwa", engine_id)
                .eq("brand_name", brand)
                .eq("model_name", model)
                .limit(1)
                .execute()
            )
            if res_ex.data:
                found_val = float(res_ex.data[0]["korekta_procent"])
                found_type = "(Exact Model)"

        # Fallback to general brand (model_name IS NULL)
        if found_val is None:
            res_gen = (
                supabase.table("ltr_admin_korekta_wr_markas")
                .select("korekta_procent")
                .eq("samar_class_id", samar_class_id)
                .eq("rodzaj_paliwa", engine_id)
                .eq("brand_name", brand)
                .is_("model_name", "null")
                .limit(1)
                .execute()
            )
            if res_gen.data:
                found_val = float(res_gen.data[0]["korekta_procent"])
                found_type = "(Brand Fallback)"

        if found_val is not None:
            checks.append(
                ReadinessItem("Korekta marka", "ok", f"{found_val:+.1%} {found_type}")
            )
        else:
            checks.append(ReadinessItem("Korekta marka", "warn", "brak wpisu → 0%"))
    except Exception:
        checks.append(ReadinessItem("Korekta marka", "warn", "błąd odczytu → 0%"))

    # 4. Korekta przebieg
    try:
        res = (
            supabase.table("samar_class_mileage_corrections")
            .select("under_threshold_percent, over_threshold_percent")
            .eq("samar_class_id", samar_class_id)
            .eq("fuel_type_id", engine_id)
            .limit(1)
            .execute()
        )
        if res.data:
            u = float(res.data[0]["under_threshold_percent"])
            o = float(res.data[0]["over_threshold_percent"])
            checks.append(ReadinessItem("Korekta przebieg", "ok", f"{u}/{o}"))
        else:
            checks.append(ReadinessItem("Korekta przebieg", "warn", "brak wpisu → 0"))
    except Exception:
        checks.append(ReadinessItem("Korekta przebieg", "warn", "brak wpisu → 0"))

    # 5. Korekta kolor
    if paint_type_id:
        try:
            res = (
                supabase.table("paint_types")
                .select("wr_correction, name")
                .eq("id", paint_type_id)
                .limit(1)
                .execute()
            )
            if res.data:
                val = float(res.data[0].get("wr_correction") or 0)
                name = res.data[0].get("name", "")
                checks.append(
                    ReadinessItem("Korekta kolor", "ok", f"{name}: {val:+.1%}")
                )
            else:
                checks.append(ReadinessItem("Korekta kolor", "warn", "brak wpisu"))
        except Exception:
            checks.append(ReadinessItem("Korekta kolor", "warn", "brak wpisu"))
    else:
        checks.append(ReadinessItem("Korekta kolor", "warn", "nie podano typu lakieru"))

    # 6. Korekta nadwozie
    if body_type_id:
        try:
            res = (
                supabase.table("body_type_wr_corrections")
                .select("correction_percent, zabudowa_correction_percent")
                .eq("samar_class_id", samar_class_id)
                .eq("brand_name", brand_name.upper())
                .eq("body_type_id", body_type_id)
                .limit(1)
                .execute()
            )
            if res.data:
                val = float(res.data[0]["correction_percent"])
                checks.append(ReadinessItem("Korekta nadwozie", "ok", f"{val:+.1%}"))
            else:
                checks.append(
                    ReadinessItem("Korekta nadwozie", "warn", "brak wpisu → 0%")
                )
        except Exception:
            checks.append(ReadinessItem("Korekta nadwozie", "warn", "brak wpisu → 0%"))
    else:
        checks.append(
            ReadinessItem("Korekta nadwozie", "warn", "nie podano typu nadwozia")
        )

    # 7. Korekta rocznik
    _vintage_map = {"current": "bieżący", "previous": "bieżący-1"}
    db_key = _vintage_map.get(rocznik, rocznik)
    try:
        res = (
            supabase.table("ltr_admin_korekta_wr_roczniks")
            .select("korekta_procent")
            .ilike("rocznik", f"%{db_key}%")
            .limit(1)
            .execute()
        )
        if res.data:
            val = float(res.data[0]["korekta_procent"])
            checks.append(ReadinessItem("Korekta rocznik", "ok", f"{val:+.1%}"))
        else:
            checks.append(ReadinessItem("Korekta rocznik", "warn", "brak wpisu → 0%"))
    except Exception:
        checks.append(ReadinessItem("Korekta rocznik", "warn", "brak wpisu → 0%"))

    return checks


# ═══════════════════════════════════════════════════════════════════
# Główny kalkulator RV
# ═══════════════════════════════════════════════════════════════════


@dataclass
class RVInput:
    """Dane wejściowe do kalkulacji RV."""

    samar_class_id: int
    engine_id: int
    brand_name: str = ""
    model_name: str = ""
    months: int = 48
    total_km: int = 140000
    capex_base_net: float = 0.0
    capex_options_net: float = 0.0
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


@lru_cache(maxsize=128)
def fetch_depreciation_rates_cached(
    samar_class_id: int, fuel_type_id: int
) -> Dict[int, Dict[str, float]]:
    """Pobiera stawki deprecjacji lat 0-7 z samar_class_depreciation_rates."""
    result: Dict[int, Dict[str, float]] = {}
    try:
        from core.database import supabase

        res = (
            supabase.table("samar_class_depreciation_rates")
            .select("year, base_depreciation_percent, options_depreciation_percent")
            .eq("samar_class_id", samar_class_id)
            .eq("fuel_type_id", fuel_type_id)
            .order("year")
            .execute()
        )
        for row in res.data or []:
            yr = int(row["year"])
            result[yr] = {
                "base": float(row.get("base_depreciation_percent", 0.0)),
                "options": float(row.get("options_depreciation_percent", 0.0)),
            }
    except Exception as exc:
        logger.warning("Błąd pobierania depreciation_rates: %s", exc)
    return result


@lru_cache(maxsize=128)
def fetch_brand_correction_cached(
    samar_class_id: int, fuel_type_id: int, brand: str, model: str
) -> float:
    """Korekta za markę z ltr_admin_korekta_wr_markas z fallbackiem na model."""
    if not brand:
        return 0.0
    try:
        from core.database import supabase

        # 1. Exact match with model
        if model:
            res_exact = (
                supabase.table("ltr_admin_korekta_wr_markas")
                .select("korekta_procent")
                .eq("samar_class_id", samar_class_id)
                .eq("rodzaj_paliwa", fuel_type_id)
                .eq("brand_name", brand)
                .eq("model_name", model)
                .limit(1)
                .execute()
            )
            if res_exact.data:
                return float(res_exact.data[0].get("korekta_procent", 0.0))

        # 2. Fallback to general brand correction (model_name IS NULL)
        res_gen = (
            supabase.table("ltr_admin_korekta_wr_markas")
            .select("korekta_procent")
            .eq("samar_class_id", samar_class_id)
            .eq("rodzaj_paliwa", fuel_type_id)
            .eq("brand_name", brand)
            .is_("model_name", "null")
            .limit(1)
            .execute()
        )
        if res_gen.data:
            return float(res_gen.data[0].get("korekta_procent", 0.0))
    except Exception as exc:
        logger.warning("Błąd brand correction cascade: %s", exc)
    return 0.0


@lru_cache(maxsize=128)
def fetch_mileage_corrections_cached(
    samar_class_id: int, fuel_type_id: int
) -> tuple[float, float]:
    """Stawki korekty przebiegu: (under_threshold, over_threshold)."""
    try:
        from core.database import supabase

        res = (
            supabase.table("samar_class_mileage_corrections")
            .select("under_threshold_percent, over_threshold_percent")
            .eq("samar_class_id", samar_class_id)
            .eq("fuel_type_id", fuel_type_id)
            .limit(1)
            .execute()
        )
        if res.data:
            row = res.data[0]
            return (
                float(row.get("under_threshold_percent", 0.0)),
                float(row.get("over_threshold_percent", 0.0)),
            )
    except Exception as exc:
        logger.warning("Błąd mileage corrections: %s", exc)
    return (0.0, 0.0)


@lru_cache(maxsize=128)
def fetch_class_config_cached(samar_class_id: int) -> Dict[str, Any]:
    """Konfiguracja klasy SAMAR (progi przebiegowe itp.)."""
    try:
        from core.database import supabase

        res = (
            supabase.table("samar_classes")
            .select("base_mileage_km, mileage_threshold_km, base_period_months")
            .eq("id", samar_class_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return cast(Dict[str, Any], res.data[0])
    except Exception as exc:
        logger.warning("Błąd class config: %s", exc)
    return {
        "base_mileage_km": 140000,
        "mileage_threshold_km": 190000,
        "base_period_months": 48,
    }


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

    def _fetch_depreciation_rates(self) -> Dict[int, Dict[str, float]]:
        """Pobiera stawki deprecjacji lat 0-7 z samar_class_depreciation_rates."""
        return fetch_depreciation_rates_cached(
            self.data.samar_class_id, self.data.engine_id
        )

    def _fetch_brand_correction(self) -> float:
        """Korekta za markę z ltr_admin_korekta_wr_markas z fallbackiem na model."""
        brand = self.data.brand_name.strip().upper()
        model = (
            self.data.model_name.strip().upper()
            if hasattr(self.data, "model_name") and self.data.model_name
            else ""
        )
        return fetch_brand_correction_cached(
            self.data.samar_class_id, self.data.engine_id, brand, model
        )

    def _fetch_mileage_corrections(self) -> tuple[float, float]:
        """Stawki korekty przebiegu: (under_threshold, over_threshold)."""
        return fetch_mileage_corrections_cached(
            self.data.samar_class_id, self.data.engine_id
        )

    def _fetch_class_config(self) -> Dict[str, Any]:
        """Konfiguracja klasy SAMAR (progi przebiegowe itp.)."""
        return fetch_class_config_cached(self.data.samar_class_id)

    def fetch_color_correction(self) -> float:
        """Korekta za kolor z paint_types.wr_correction."""
        return fetch_color_correction_cached(
            self.data.paint_type_id, self.data.is_metalic
        )

    def fetch_body_correction(self) -> tuple[float, float]:
        """Korekta nadwozia z kaskadą fallbacków (sparse storage)."""
        return fetch_body_correction_cached(
            self.data.samar_class_id,
            self.data.engine_id,
            self.data.brand_name,
            self.data.body_type_id,
        )

    def fetch_vintage_correction(self) -> float:
        """Korekta za rocznik z ltr_admin_korekta_wr_roczniks."""
        return fetch_vintage_correction_cached(self.data.rocznik)

    def fetch_lo_param(self) -> float:
        """PrzewidywanaCenaSprzedazyLO z control_center (kolumna)."""
        return fetch_lo_param_cached()

    def calculate(self) -> RVOutput:
        """Oblicza RV wg algorytmu Excel JŁ (6 kroków)."""
        debug: Dict[str, Any] = {}

        # ── Pobranie danych ──
        rates = self._fetch_depreciation_rates()
        config = self._fetch_class_config()
        base_mileage = float(config.get("base_mileage_km", 140000))
        mileage_threshold = float(config.get("mileage_threshold_km", 190000))

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 1: WR bazy = cena_bazowa × (WR_klasa% + korekta_marka)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        wr_base_pct = rates.get(0, {"base": 0.0})["base"]
        brand_correction = self._fetch_brand_correction()
        effective_pct = wr_base_pct + brand_correction

        # BS = L × BT (Excel)
        wr_value = self.data.capex_base_net * effective_pct

        debug["krok1_wr_base_pct"] = wr_base_pct
        debug["krok1_brand_correction"] = brand_correction
        debug["krok1_effective_pct"] = effective_pct
        debug["krok1_wr_value"] = wr_value

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 2: Kaskadowa deprecjacja rok→rok (ZAWSZE 7 lat)
        # Rok 0 = bazowy WR. Rok 4 (col F w Excelu) = 0 (punkt bazowy).
        # Lata < 4 → aprecjacja (dodajemy).
        # Lata > 4 → deprecjacja (odejmujemy).
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        # Excel: BC=BS (rok 4→0), potem kaskadowo w obie strony
        # Wg Excela: kolumna F(rok4)=0, kolumny B-E(rok0-3) = aprecjacja,
        # kolumny G-I(rok5-7) = deprecjacja.
        # Efektywna formuła: w przód od roku 0 (bazowego=rok4 w Excelu):
        #   rok<4: wartość rośnie (1 + rate)
        #   rok=4: baza (rate=0)
        #   rok>4: wartość maleje (1 - rate)

        # Budujemy tabelę wartości od roku bazowego (0 w DB = rok 4 w Excelu)
        # APRECJACJA: od roku 0 wstecz do roku -3 (Excel: rok3 do rok1)
        # → ale w naszej DB rate na rok 1 = aprecjacja z Excela rok 3
        # → rate na rok 2 = aprecjacja z Excela rok 2
        # → rate na rok 3 = aprecjacja z Excela rok 1

        # Budujemy tak:
        # year=0 (rok bazowy 48mc): wr_value (już obliczone)
        # year=1 → Excel rok3: aprecjacja
        #   value = prev * (1 + rates[1])
        #   ALE to jest WSTECZ, więc: value_at_rok3 = wr_value * (1+rate_rok3_do_rok4)
        # etc.

        # W Excelu:
        # AN (rok 0/bieżący) = AR × (1 + AL)  gdzie AL = rate rok 0→1
        # AR (rok 1)          = AV × (1 + AP)  gdzie AP = rate rok 1→2
        # AV (rok 2)          = AZ × (1 + AT)  gdzie AT = rate rok 2→3
        # AZ (rok 3)          = BC × (1 + AX)  gdzie AX = rate rok 3→4
        # BC (rok 4)          = BS = baza       (rate = 0)
        # BG (rok 5)          = BS - BE × BS = BS × (1 - BE)
        # BK (rok 6)          = BG - BI × BG = BG × (1 - BI)
        # BO (rok 7)          = BK - BM × BK = BK × (1 - BM)

        # Więc: od bazy (rok 4) w DÓŁ (roki 5+): multiplier = (1-rate)
        #        od bazy (rok 4) w GÓRĘ (roki 3-): multiplier = (1+rate)
        # Uwaga: Excel col I(rok7) i col H(rok6) i col G(rok5) to deprecjacje
        #         Excel col E(rok3) i col D(rok2) i col C(rok1) i col B(rok0) to aprecjacje

        # W DB: year=0 → bazowe WR% (z TAB.WR KLASA)
        #        year=1..3 → stawki aprecjacji (odwrotność: rok4→rok1)
        #        year=4 → 0 (punkt bazowy)
        #        year=5..7 → stawki deprecjacji

        # Aprecjacja (roki przed bazowym)
        apreciated = wr_value
        for yr in range(1, 4):  # rok 3, 2, 1 w Excelu
            rate = rates.get(yr, {"base": 0.0})["base"]
            apreciated = apreciated * (1.0 + rate)
            # yr=1 → dane z DB rok 1 = aprecjacja Excel rok 3→4
            # yr=2 → dane z DB rok 2 = aprecjacja Excel rok 2→3
            # yr=3 → dane z DB rok 3 = aprecjacja Excel rok 1→2

        # Teraz mamy wartość po pełnej aprecjacji (rok 0 Excel = rok bieżący)
        # Deprecjacja (roki po bazowym)
        depreciated = wr_value
        for yr in range(5, 8):  # rok 5, 6, 7
            rate = rates.get(yr, {"base": 0.0})["base"]
            depreciated = depreciated * (1.0 - rate)

        # Tabelka wartości per rok (0=bieżący, 7=najstarszy)
        # Budujemy ją kaskadowo od bazy (rok 4)
        value_table: Dict[int, float] = {4: wr_value}

        # W górę (od bazy do bieżącego)
        v = wr_value
        for yr in [3, 2, 1, 0]:
            if yr == 0:
                rate = rates.get(0, {"base": 0.0})["base"]
                # Rok 0 w Excelu: col B → to powinno być rate aprecjacji
                # ale w DB year=0 to bazowe WR% → nie do kaskady
                # W Excelu kolumna B (rok 0) = 0.05 (5%), to INNA aprecjacja
                # Musimy obsłużyć to specjalnie
                v = v * (1.0 + rate)
            else:
                rate = rates.get(4 - yr, {"base": 0.0})["base"]
                v = v * (1.0 + rate)
            value_table[yr] = v

        # W dół (od bazy do roku 7)
        v = wr_value
        for yr in [5, 6, 7]:
            rate = rates.get(yr, {"base": 0.0})["base"]
            v = v * (1.0 - rate)
            value_table[yr] = v

        debug["krok2_value_table"] = {
            k: round(v, 2) for k, v in sorted(value_table.items())
        }

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 3: Wybierz wartość per delta_lat + RV opcji
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        years = self.data.months // 12
        years = max(0, min(years, self.LICZBA_LAT))

        # Potrzebujemy: AB (delta_lat) z Excela = ile lat trwa leasing
        # W Excelu AB = rok_konca - rok_startu
        # U nas: years = months // 12

        rv_base = value_table.get(years, wr_value)

        # RV opcji: z tabeli options (year w DB = delta_lat w Excelu)
        options_rv_pct = rates.get(years, {"options": 0.0})["options"]
        rv_options = self.data.capex_options_net * options_rv_pct

        rv_total = rv_base + rv_options

        debug["krok3_years"] = years
        debug["krok3_rv_base"] = round(rv_base, 2)
        debug["krok3_options_rv_pct"] = options_rv_pct
        debug["krok3_rv_options"] = round(rv_options, 2)
        debug["krok3_rv_total"] = round(rv_total, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 4: Korekta przebiegu
        # Excel: nadprzebieg w tyś km, 2 pasma: do50 i ponad50
        # W naszej DB: progi base_mileage i mileage_threshold
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        nadprzebieg_km = self.data.total_km - base_mileage
        nadprzebieg_tkm = nadprzebieg_km / 1000.0  # tyś km

        # Excel: AD = nadprzebieg do progu (max 50 tyś km nad bazą)
        #   AF = nadprzebieg ponad próg
        threshold_delta_tkm = (mileage_threshold - base_mileage) / 1000.0  # 50
        nadprzebieg_do_progu = min(max(nadprzebieg_tkm, 0), threshold_delta_tkm)
        nadprzebieg_ponad_prog = max(nadprzebieg_tkm - threshold_delta_tkm, 0)

        under_rate, over_rate = self._fetch_mileage_corrections()
        unit_10tkm = 10.0  # per 10 tyś km

        # Excel: AK = AG × BR × (AD/10) + AH × BR × (AF/10)
        korekta_przebieg = under_rate * rv_total * (
            nadprzebieg_do_progu / unit_10tkm
        ) + over_rate * rv_total * (nadprzebieg_ponad_prog / unit_10tkm)

        debug["krok4_nadprzebieg_tkm"] = round(nadprzebieg_tkm, 1)
        debug["krok4_do_progu"] = round(nadprzebieg_do_progu, 1)
        debug["krok4_ponad_prog"] = round(nadprzebieg_ponad_prog, 1)
        debug["krok4_under_rate"] = under_rate
        debug["krok4_over_rate"] = over_rate
        debug["krok4_korekta_przebieg"] = round(korekta_przebieg, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 5: Korekty dodatkowe (kolor, nadwozie, rocznik)
        # NotebookLM: rocznik = MULTIPLIKATYWNA, reszta = addytywna
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        color_correction_pct = self.fetch_color_correction()
        color_value = color_correction_pct * self.data.capex_base_net

        body_correction_pct, zabudowa_correction_pct = self.fetch_body_correction()
        capex_total = self.data.capex_base_net + self.data.capex_options_net
        body_value = body_correction_pct * capex_total
        zabudowa_value = 0.0
        if self.data.zabudowa_apr_wr:
            zabudowa_value = zabudowa_correction_pct * capex_total

        # Korekty addytywne (kolor, nadwozie, zabudowa, przebieg)
        rv_pre_vintage = (
            rv_total + color_value + body_value + zabudowa_value - korekta_przebieg
        )

        # Korekta rocznika — MULTIPLIKATYWNA (NotebookLM §4)
        # WR × (1 + vintage%) zamiast vintage% × cena_bazowa
        vintage_correction_pct = self.fetch_vintage_correction()
        rv_after_corrections = rv_pre_vintage * (1.0 + vintage_correction_pct)

        debug["krok5_color"] = round(color_value, 2)
        debug["krok5_body"] = round(body_value, 2)
        debug["krok5_zabudowa"] = round(zabudowa_value, 2)
        debug["krok5_vintage_pct"] = vintage_correction_pct
        debug["krok5_rv_pre_vintage"] = round(rv_pre_vintage, 2)
        debug["krok5_rv_after"] = round(rv_after_corrections, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 6: Korekta ręczna + wynik
        # Excel: BX = BV + BW (ręczna)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        final_rv = rv_after_corrections + self.data.manual_wr_correction

        # WRdlaLO
        lo_param = self.fetch_lo_param()
        wr_lo = final_rv * (1.0 + lo_param)

        # Utrata wartości = max(CAPEX - WR, 0)
        utrata = max(capex_total - final_rv, 0.0)

        # % retencji
        wr_pct = final_rv / capex_total if capex_total > 0 else 0.0

        debug["krok6_manual_correction"] = self.data.manual_wr_correction
        debug["krok6_final_rv"] = round(final_rv, 2)
        debug["krok6_wr_lo"] = round(wr_lo, 2)
        debug["krok6_utrata"] = round(utrata, 2)
        debug["krok6_wr_pct"] = round(wr_pct, 4)

        return RVOutput(
            wr_net=final_rv,
            wr_lo_net=wr_lo,
            utrata_wartosci_net=utrata,
            wr_percent=wr_pct,
            debug=debug,
        )

    # (ponieważ cached functions muszą być na poziomie modułu dla @lru_cache)


@lru_cache(maxsize=128)
def fetch_color_correction_cached(
    paint_type_id: Optional[int], is_metalic: bool
) -> float:
    """Korekta za kolor z paint_types.wr_correction."""
    if not paint_type_id:
        return 0.0 if is_metalic else -0.01
    try:
        from core.database import supabase

        res = (
            supabase.table("paint_types")
            .select("wr_correction")
            .eq("id", paint_type_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return float(res.data[0].get("wr_correction") or 0.0)
    except Exception as exc:
        logger.warning("Błąd color correction: %s", exc)
    return 0.0 if is_metalic else -0.01


@lru_cache(maxsize=128)
def fetch_body_correction_cached(
    samar_class_id: int, engine_id: int, brand_name: str, body_type_id: Optional[int]
) -> tuple[float, float]:
    """Korekta nadwozia z kaskadą fallbacków (sparse storage)."""
    brand = brand_name.strip().upper() if brand_name else ""

    def _extract(rows: list[dict]) -> tuple[float, float]:
        row = rows[0]
        return (
            float(row.get("correction_percent", 0.0)),
            float(row.get("zabudowa_correction_percent", 0.0)),
        )

    try:
        from core.database import supabase

        tbl = "body_type_wr_corrections"
        cols = "correction_percent, zabudowa_correction_percent"

        # 1. EXACT: klasa + marka + nadwozie + silnik
        if body_type_id and engine_id:
            res = (
                supabase.table(tbl)
                .select(cols)
                .eq("samar_class_id", samar_class_id)
                .eq("brand_name", brand)
                .eq("body_type_id", body_type_id)
                .eq("engine_type_id", engine_id)
                .limit(1)
                .execute()
            )
            if res.data:
                return _extract(res.data)

        # 2. NO-ENGINE: klasa + marka + nadwozie (engine IS NULL)
        if body_type_id:
            res = (
                supabase.table(tbl)
                .select(cols)
                .eq("samar_class_id", samar_class_id)
                .eq("brand_name", brand)
                .eq("body_type_id", body_type_id)
                .is_("engine_type_id", "null")
                .limit(1)
                .execute()
            )
            if res.data:
                return _extract(res.data)

        # 3. NO-BODY: klasa + marka (body IS NULL, engine IS NULL)
        if brand:
            res = (
                supabase.table(tbl)
                .select(cols)
                .eq("samar_class_id", samar_class_id)
                .eq("brand_name", brand)
                .is_("body_type_id", "null")
                .is_("engine_type_id", "null")
                .limit(1)
                .execute()
            )
            if res.data:
                return _extract(res.data)

    except Exception as exc:
        logger.warning("Błąd body correction cascade: %s", exc)

    return (0.0, 0.0)


@lru_cache(maxsize=128)
def fetch_vintage_correction_cached(rocznik: str) -> float:
    """Korekta za rocznik z ltr_admin_korekta_wr_roczniks."""
    vintage_map = {"current": "bieżący", "previous": "bieżący-1"}
    db_key = vintage_map.get(rocznik, rocznik)
    try:
        from core.database import supabase

        res = (
            supabase.table("ltr_admin_korekta_wr_roczniks")
            .select("korekta_procent")
            .ilike("rocznik", f"%{db_key}%")
            .limit(1)
            .execute()
        )
        if res.data:
            return float(res.data[0].get("korekta_procent", 0.0))
    except Exception as exc:
        logger.warning("Błąd vintage correction: %s", exc)
    return 0.0


@lru_cache(maxsize=1)
def fetch_lo_param_cached() -> float:
    """PrzewidywanaCenaSprzedazyLO z control_center (kolumna)."""
    try:
        from core.database import supabase

        res = (
            supabase.table("control_center")
            .select("przewidywana_cena_sprzedazy_lo")
            .limit(1)
            .execute()
        )
        if res.data:
            val = res.data[0].get("przewidywana_cena_sprzedazy_lo", 0.0)
            return float(val) if val is not None else 0.0
    except Exception:
        logger.warning("Nie udało się pobrać PrzewidywanaCenaSprzedazyLO")
    return 0.0


# ═══════════════════════════════════════════════════════════════════
# SamarRVCalculator — metody instancji (kontynuacja klasy z L430)
# Monkey-patching: cached standalone functions powyżej,
# metody instancji przypisane do klasy poniżej.
# ═══════════════════════════════════════════════════════════════════
