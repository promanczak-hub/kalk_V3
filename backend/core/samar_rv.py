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
                    "error",
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
                checks.append(ReadinessItem("Korekta kolor", "error", "brak wpisu"))
        except Exception:
            checks.append(ReadinessItem("Korekta kolor", "error", "brak wpisu"))
    else:
        checks.append(ReadinessItem("Korekta kolor", "error", "nie podano typu lakieru"))

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
                checks.append(ReadinessItem("Korekta nadwozie", "warn", "brak wpisu → 0%"))
        except Exception:
            checks.append(ReadinessItem("Korekta nadwozie", "warn", "brak wpisu → 0%"))
    else:
        checks.append(ReadinessItem("Korekta nadwozie", "warn", "brak wpisu → 0%"))

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
        raise ValueError(
            f"Brak wpisu korekty przebiegu w `samar_class_mileage_corrections` "
            f"dla klasy={samar_class_id}, paliwo={fuel_type_id}."
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Blad odczytu `samar_class_mileage_corrections` dla klasy={samar_class_id}, "
            f"paliwo={fuel_type_id}: {exc}"
        ) from exc


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
    return {}


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

    def fetch_body_correction(self) -> float:
        """Korekta nadwozia (marka + nadwozie + silnik, bez klasy SAMAR)."""
        return fetch_body_correction_cached(
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
        if not rates:
            raise ValueError(
                f"Brak stawek deprecjacji w tabeli `samar_class_depreciation_rates` "
                f"dla klasy {self.data.samar_class_id} "
                f"(marka: {self.data.brand_name}, model: {self.data.model_name}). "
                f"Kalkulacja zatrzymana (Reguła Fail-Fast)."
            )

        config = self._fetch_class_config()
        if not config:
            raise ValueError(
                f"Brak konfiguracji klasy SAMAR (`samar_classes`) dla klasy {self.data.samar_class_id}."
            )

        base_mileage = float(config.get("base_mileage_km") or 0.0)
        mileage_threshold = float(config.get("mileage_threshold_km") or 0.0)
        if base_mileage <= 0 or mileage_threshold <= 0:
            raise ValueError(
                f"Nieprawidlowa konfiguracja przebiegu dla klasy {self.data.samar_class_id} "
                f"(base_mileage_km={base_mileage}, mileage_threshold_km={mileage_threshold})."
            )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # V1 PARITY: Przeliczenia per se operowały na wartościach Netto.
        # Cena Katalogowa "goła" (często z opcjami jako całość, wedle wejścia V1)
        # jest deprecjonowana przez tabele, ale Opcje starzały się OSOBNO ułamkowo.
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        base_netto = self.data.capex_base_net
        options_netto = self.data.capex_options_net

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 1: WR bazy = cena_bazowa_netto × (WR_klasa% + korekta_marka)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        wr_base_pct = rates.get(0, {"base": 0.0})["base"]
        brand_correction = self._fetch_brand_correction()
        effective_pct = wr_base_pct + brand_correction

        wr_value_netto = base_netto * effective_pct

        debug["krok1_wr_base_pct"] = wr_base_pct
        debug["krok1_brand_correction"] = brand_correction
        debug["krok1_effective_pct"] = effective_pct
        debug["krok1_wr_value_netto"] = round(wr_value_netto, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 2: Kaskadowa deprecjacja bazy rok→rok (7 lat na sztywno, V1 Parity)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        value_table: Dict[int, float] = {4: wr_value_netto}

        # W górę (od bazy do bieżącego = Delta -)
        v = wr_value_netto
        for yr in [3, 2, 1, 0]:
            rate = (
                rates.get(0, {"base": 0.0})["base"]
                if yr == 0
                else rates.get(4 - yr, {"base": 0.0})["base"]
            )
            v = v * (1.0 + rate)
            value_table[yr] = v

        # W dół (od bazy do roku 7)
        v = wr_value_netto
        for yr in [5, 6, 7]:
            rate = rates.get(yr, {"base": 0.0})["base"]
            v = v * (1.0 - rate)
            value_table[yr] = v

        debug["krok2_value_table_netto"] = {
            k: round(val, 2) for k, val in sorted(value_table.items())
        }

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 3: Wybór WR bazy + Ręczne ułamkowe WR doposażenia
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        years = self.data.months // 12
        years = max(0, min(years, self.LICZBA_LAT))
        rv_base_netto = value_table.get(years, wr_value_netto)

        # V1 PARITY: Opcje starzeją się zgodnie z tabelą (options_depreciation_percent)
        options_rate = rates.get(years, {"options": 0.0})["options"]
        if options_rate > 0.0:
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
        # KROK 4: Korekta przebiegu (V1 PARITY - sztywne 140k twardy start)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        under_rate, over_rate = self._fetch_mileage_corrections()
        # Odtwarzamy bezpiecznie sztywne progi V1 (parity)
        # UWAGA: Usunięto ograniczenie max(..., 0) z przebieg_ponizej_190, aby obsłużyć "bonus"
        # (redukcję kary) dla mniejszych przebiegów zgodnie z formułami V1.

        przebieg_ponizej_190 = min(self.data.total_km, 190000) - 140000
        paczki_under = przebieg_ponizej_190 / 10000.0

        przebieg_powyzej_190 = max(self.data.total_km - 190000, 0)
        paczki_over = przebieg_powyzej_190 / 10000.0

        # Excel podchodził do korekty używając całkowitej zsumowanej wartości WROkres
        korekta_przebieg_netto = (under_rate * rv_total_netto * paczki_under) + (
            over_rate * rv_total_netto * paczki_over
        )

        debug["krok4_paczki_under"] = round(paczki_under, 2)
        debug["krok4_paczki_over"] = round(paczki_over, 2)
        debug["krok4_under_rate"] = under_rate
        debug["krok4_over_rate"] = over_rate
        debug["krok4_korekta_przebieg_netto"] = round(korekta_przebieg_netto, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 5: Korekty dodatkowe (kolor, nadwozie)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        color_correction_pct = self.fetch_color_correction()
        color_value_netto = color_correction_pct * base_netto

        body_correction_pct = self.fetch_body_correction()
        capex_total_netto = base_netto + options_netto
        body_value_netto = body_correction_pct * capex_total_netto

        rv_netto_pre_manual = (
            rv_total_netto
            + color_value_netto
            + body_value_netto
            - korekta_przebieg_netto
        )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 6: Korekta ręczna przed rocznikiem (V1 PARITY)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        manual_correction_netto = self.data.manual_wr_correction
        rv_z_reczna_netto = rv_netto_pre_manual + manual_correction_netto

        # Mnożnik za rocznik zawsze na samym końcu
        vintage_correction_pct = self.fetch_vintage_correction()
        final_rv_netto = rv_z_reczna_netto * (1.0 + vintage_correction_pct)

        debug["krok5_color_netto"] = round(color_value_netto, 2)
        debug["krok5_body_netto"] = round(body_value_netto, 2)
        debug["krok6_manual_correction_netto"] = manual_correction_netto
        debug["krok6_vintage_pct"] = vintage_correction_pct
        debug["krok6_final_rv_netto"] = round(final_rv_netto, 2)

        # WRdlaLO
        lo_param = self.fetch_lo_param()
        wr_lo_netto = final_rv_netto * (1.0 + lo_param)

        utrata = max(capex_total_netto - final_rv_netto, 0.0)
        wr_pct = final_rv_netto / capex_total_netto if capex_total_netto > 0 else 0.0

        debug["krok6_utrata"] = round(utrata, 2)
        debug["krok6_wr_pct"] = round(wr_pct, 4)

        return RVOutput(
            wr_net=final_rv_netto,
            wr_lo_net=wr_lo_netto,
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
        return 0.0
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
    return 0.0


@lru_cache(maxsize=128)
def fetch_body_correction_cached(
    engine_id: int, brand_name: str, body_type_id: Optional[int]
) -> float:
    """Korekta nadwozia z kaskada fallbackow (marka + nadwozie + silnik)."""
    brand = brand_name.strip().upper() if brand_name else ""

    def _extract(rows: list[dict]) -> float:
        row = rows[0]
        return float(row.get("correction_percent", 0.0))

    try:
        from core.database import supabase

        tbl = "body_type_wr_corrections"
        cols = "correction_percent"

        # 1. EXACT: marka + nadwozie + silnik
        if body_type_id and engine_id and brand:
            res = (
                supabase.table(tbl)
                .select(cols)
                .eq("brand_name", brand)
                .eq("body_type_id", body_type_id)
                .eq("engine_type_id", engine_id)
                .limit(1)
                .execute()
            )
            if res.data:
                return _extract(res.data)

        # 2. NO-ENGINE: marka + nadwozie (engine IS NULL)
        if body_type_id and brand:
            res = (
                supabase.table(tbl)
                .select(cols)
                .eq("brand_name", brand)
                .eq("body_type_id", body_type_id)
                .is_("engine_type_id", "null")
                .limit(1)
                .execute()
            )
            if res.data:
                return _extract(res.data)

        # 3. NO-BODY: marka (body IS NULL, engine IS NULL)
        if brand:
            res = (
                supabase.table(tbl)
                .select(cols)
                .eq("brand_name", brand)
                .is_("body_type_id", "null")
                .is_("engine_type_id", "null")
                .limit(1)
                .execute()
            )
            if res.data:
                return _extract(res.data)

    except Exception as exc:
        logger.warning("Blad body correction cascade: %s", exc)

    return 0.0


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
