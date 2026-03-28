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
from typing import Any, Dict, Optional

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
    body_type_id: Optional[int] = None,
    paint_type_id: Optional[int] = None,
    rocznik: str = "current",
    zabudowa_type_id: Optional[int] = None,
    engine_name: str = "",
    model_name: str = "",
) -> list[ReadinessItem]:
    """Sprawdza pokrycie parametrów w DB przed kalkulacją. Dostosowane do 6 Monolitów."""
    checks: list[ReadinessItem] = []

    # 1. Monolit: WR bazy (Tabela deprecjacji - Macierz Przebiegów)
    try:
        # V3 schema: km_35000, km_70000, km_105000, km_140000, km_175000, km_210000, km_245000
        cols = [f"km_{km}" for km in range(35000, 245001, 35000)]
        res = (
            supabase.table("tab_okres_final")
            .select(", ".join(cols))
            .eq("klasa_samar", samar_class_id)
            .ilike(
                "rodzaj_silnika", f"%{_normalize_fuel_name(brand_name, engine_name)}%"
            )
            .execute()
        )
        if res.data:
            row = res.data[0]
            missing_cols = [c for c in cols if row.get(c) is None]
            if not missing_cols:
                # We show the 140k rate as the primary indicator
                pct = float(row.get("km_140000") or 0.0) * 100
                checks.append(
                    ReadinessItem(
                        "1. Bazowa Utrata Wartości", "ok", f"{pct:.1f}%, pełna macierz"
                    )
                )
            else:
                pct = float(row.get("km_140000") or 0.0) * 100
                valid_count = len(cols) - len(missing_cols)
                checks.append(
                    ReadinessItem(
                        "1. Bazowa Utrata Wartości",
                        "warn",
                        f"{pct:.1f}%, tylko {valid_count}/{len(cols)} progów",
                    )
                )
        else:
            checks.append(
                ReadinessItem(
                    "1. Bazowa Utrata Wartości",
                    "error",
                    "brak wpisu w tab_okres_final (Klasa/Silnik)",
                )
            )
    except Exception as exc:
        logger.error("Błąd odczytu tab_okres_final: %s", exc)
        checks.append(
            ReadinessItem("1. Bazowa Utrata Wartości", "error", "błąd odczytu DB")
        )

    # 2. Monolit: Korekta Przebiegu - samar_class_mileage_corrections (V3)
    try:
        res = (
            supabase.table("samar_class_mileage_corrections")
            .select("korekta_lt_prog, korekta_gt_prog")
            .eq("klasa_samar", samar_class_id)
            .limit(1)
            .execute()
        )
        if res.data:
            u = float(res.data[0]["korekta_lt_prog"] or 0.0)
            o = float(res.data[0]["korekta_gt_prog"] or 0.0)
            checks.append(
                ReadinessItem(
                    "2. Korekta Przebiegu", "ok", f"poniżej: {u:.4f}, powyżej: {o:.4f}"
                )
            )
        else:
            checks.append(
                ReadinessItem("2. Korekta Przebiegu", "warn", "brak wpisu → 0")
            )
    except Exception as exc:
        logger.warning("Błąd odczytu mileage corrections: %s", exc)
        checks.append(ReadinessItem("2. Korekta Przebiegu", "warn", "brak wpisu → 0"))

    # 3. Monolit: Korekta Marki - samar_brand_corrections (V3)
    try:
        brand = brand_name.strip().upper()
        # V3 column names: klasa_samar, marka, model, silnik, korekta
        found_val = None
        found_type = ""

        # Use normalized fuel for silnik match
        fuel_norm = _normalize_fuel_name(brand, engine_name)

        if model_name:
            model = model_name.strip().upper()
            res_ex = (
                supabase.table("samar_brand_corrections")
                .select("korekta")
                .eq("klasa_samar", samar_class_id)
                .ilike("marka", brand)
                .ilike("model", model)
                .ilike("silnik", f"%{fuel_norm}%")
                .limit(1)
                .execute()
            )
            if res_ex.data:
                found_val = float(res_ex.data[0]["korekta"] or 0.0)
                found_type = "(Model+Fuel)"

        if found_val is None:
            res_gen = (
                supabase.table("samar_brand_corrections")
                .select("korekta")
                .eq("klasa_samar", samar_class_id)
                .ilike("marka", brand)
                .is_("model", "null")
                .ilike("silnik", f"%{fuel_norm}%")
                .limit(1)
                .execute()
            )
            if res_gen.data:
                found_val = float(res_gen.data[0]["korekta"] or 0.0)
                found_type = "(Brand+Fuel)"

        if found_val is None:
            # Absolute fallback: Brand only (any fuel)
            res_br = (
                supabase.table("samar_brand_corrections")
                .select("korekta")
                .eq("klasa_samar", samar_class_id)
                .ilike("marka", brand)
                .is_("model", "null")
                .limit(1)
                .execute()
            )
            if res_br.data:
                found_val = float(res_br.data[0]["korekta"] or 0.0)
                found_type = "(Brand Only)"

        if found_val is not None:
            checks.append(
                ReadinessItem(
                    "3. Korekta Marki", "ok", f"{found_val:+.1%} {found_type}"
                )
            )
        else:
            checks.append(ReadinessItem("3. Korekta Marki", "warn", "brak wpisu → 0%"))
    except Exception as exc:
        logger.warning("Błąd odczytu brand corrections: %s", exc)
        checks.append(ReadinessItem("3. Korekta Marki", "warn", "błąd odczytu → 0%"))

    # 4. Monolit: Korekta Nadwozia (Osobowe/Bazowe) - body_type_wr_corrections (Marka + Typ Nadwozia + Silnik)
    if body_type_id:
        try:
            brand = brand_name.strip().upper() if brand_name else ""
            found_val = None
            found_type = ""

            # Dokladne dopasowanie: Marka + Nadwozie + Silnik
            if engine_id and brand:
                res_ex = (
                    supabase.table("body_type_wr_corrections")
                    .select("correction_percent")
                    .eq("brand_name", brand)
                    .eq("body_type_id", body_type_id)
                    .eq("engine_type_id", engine_id)
                    .limit(1)
                    .execute()
                )
                if res_ex.data:
                    found_val = float(res_ex.data[0]["correction_percent"])
                    found_type = "(Brand+Body+Engine)"

            # Fallback 1: Marka + Nadwozie (Silnik IS NULL)
            if found_val is None and brand:
                res_gen = (
                    supabase.table("body_type_wr_corrections")
                    .select("correction_percent")
                    .eq("brand_name", brand)
                    .eq("body_type_id", body_type_id)
                    .is_("engine_type_id", "null")
                    .limit(1)
                    .execute()
                )
                if res_gen.data:
                    found_val = float(res_gen.data[0]["correction_percent"])
                    found_type = "(Brand+Body)"

            # Fallback 2: Tylko Marka (Nadwozie i Silnik IS NULL)
            if found_val is None and brand:
                res_br = (
                    supabase.table("body_type_wr_corrections")
                    .select("correction_percent")
                    .eq("brand_name", brand)
                    .is_("body_type_id", "null")
                    .is_("engine_type_id", "null")
                    .limit(1)
                    .execute()
                )
                if res_br.data:
                    found_val = float(res_br.data[0]["correction_percent"])
                    found_type = "(Rozdz. Marki)"

            if found_val is not None:
                checks.append(
                    ReadinessItem(
                        "4. Korekta Nadwozia", "ok", f"{found_val:+.1%} {found_type}"
                    )
                )
            else:
                checks.append(
                    ReadinessItem("4. Korekta Nadwozia", "warn", "brak wpisu → 0%")
                )
        except Exception:
            checks.append(
                ReadinessItem("4. Korekta Nadwozia", "warn", "błąd odczytu → 0%")
            )
    else:
        checks.append(
            ReadinessItem("4. Korekta Nadwozia", "warn", "nie podano typu nadwozia")
        )

    # 5. Monolit: Korekta ZABUDOWY (Dostawcze) - zabudowa_wr_corrections (Typ Zabudowy + Klasa SAMAR)
    if zabudowa_type_id:
        try:
            res = (
                supabase.table("zabudowa_wr_corrections")
                .select("correction_percent")
                .eq("zabudowa_type_id", zabudowa_type_id)
                .eq("samar_class_id", samar_class_id)
                .limit(1)
                .execute()
            )
            if res.data:
                val = float(res.data[0]["correction_percent"])
                checks.append(
                    ReadinessItem(
                        "5. Korekta Zabudowy", "ok", f"{val:+.1%} (Dostawcze/Specjalne)"
                    )
                )
            else:
                # Spróbuj bez klasyfikacji SAMAR (Globalny fallback)
                res_gen = (
                    supabase.table("zabudowa_wr_corrections")
                    .select("correction_percent")
                    .eq("zabudowa_type_id", zabudowa_type_id)
                    .is_("samar_class_id", "null")
                    .limit(1)
                    .execute()
                )
                if res_gen.data:
                    val = float(res_gen.data[0]["correction_percent"])
                    checks.append(
                        ReadinessItem(
                            "5. Korekta Zabudowy", "ok", f"{val:+.1%} (Globalna)"
                        )
                    )
                else:
                    checks.append(
                        ReadinessItem("5. Korekta Zabudowy", "warn", "brak wpisu → 0%")
                    )
        except Exception:
            checks.append(
                ReadinessItem("5. Korekta Zabudowy", "warn", "błąd odczytu → 0%")
            )
    else:
        # Puste by uniknąć straszenia "WARN" jeśli to auto osobowe
        # (Zabudowa ma sens tylko dla dostawczych, zrobimy info)
        checks.append(
            ReadinessItem("5. Korekta Zabudowy", "ok", "Brak zabudowy specjalnej (0%)")
        )

    # 6. Monolit: Korekta Lakieru - paint_types (Globalna)
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
                    ReadinessItem(
                        "6. Korekta Lakieru", "ok", f"{name}: {val:+.1%} (Globalna)"
                    )
                )
            else:
                checks.append(ReadinessItem("6. Korekta Lakieru", "warn", "brak wpisu"))
        except Exception:
            checks.append(ReadinessItem("6. Korekta Lakieru", "warn", "błąd odczytu"))
    else:
        checks.append(
            ReadinessItem(
                "6. Korekta Lakieru", "warn", "nie podano identyfikatora lakieru"
            )
        )

    return checks


# ═══════════════════════════════════════════════════════════════════
# Główny kalkulator RV
# ═══════════════════════════════════════════════════════════════════


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
    capex_base_net: float = 0.0      # Nowa zmienna dla utraty wartosci (CAPEX)
    capex_options_net: float = 0.0   # Nowa zmienna dla utraty wartosci (CAPEX opcje)
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
def fetch_base_rv_percent_cached(samar_class_id: int, engine_type_id: int) -> float:
    """Pobiera 4-letnią bazę WR% z samar_class_depreciation_rates dla danej klasy i silnika."""
    COLUMN_MAP = {
        1: "benzyna_pb",
        2: "diesel_on",
        3: "benzyna_mhev_pb_mhev",
        4: "diesel_mhev_on_mhev",
        5: "hybryda_hev",
        6: "plug_in_hybrid_phev",
        7: "elektryczny_bev",
        8: "wodor_fcev",
        9: "lpg"
    }
    col_name = COLUMN_MAP.get(engine_type_id, "benzyna_pb")
    try:
        from core.database import supabase
        res = (
            supabase.table("samar_class_depreciation_rates")
            .select(col_name)
            .eq("klasa_samar", samar_class_id)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            val = res.data[0].get(col_name)
            if val is not None:
                return float(val)
    except Exception as exc:
        logger.warning(f"Błąd pobierania base_rv_percent z samar_class_depreciation_rates dla klasy {samar_class_id}, silnik {engine_type_id}: {exc}")
    # Fallback fail-fast na wypadek błędu logicznego
    raise ValueError(f"Brak przypisanego Base RV w samar_class_depreciation_rates dla klasy={samar_class_id}, silnik={engine_type_id}")

@lru_cache(maxsize=128)
def fetch_depreciation_rates_cached(
    samar_class_id: int, brand_name: str, engine_name: str
) -> Dict[str, float]:
    """Pobiera linię różnic z tab_okres_final (V3) aby narzucić ją na BAZĘ 140_000."""
    try:
        from core.database import supabase

        fuel_norm = _normalize_fuel_name(brand_name, engine_name)
        res = (
            supabase.table("tab_okres_final")
            .select(
                "km_35000, km_70000, km_105000, km_140000, km_175000, km_210000, km_245000"
            )
            .eq("klasa_samar", samar_class_id)
            .ilike("rodzaj_silnika", f"%{fuel_norm}%")
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
    except Exception as exc:
        logger.warning("Błąd pobierania tab_okres_final: %s", exc)
    return {}


def _normalize_fuel_name(brand: str, engine_name: str) -> str:
    """Ujednolica nazwy paliw na potrzeby lookupów w V3 (rodzaj_silnika)."""
    normalized = engine_name.strip().upper()
    if "BENZYNA" in normalized:
        return "Benzyna"
    if "DIESEL" in normalized:
        return "Diesel"
    if "ELEKTRYCZNY" in normalized or "BEV" in normalized:
        return "Elektryczny"
    if "HYBRYDA PLUG-IN" in normalized or "PHEV" in normalized:
        return "Hybryda Plug-in"
    if "HYBRYDA (HEV)" in normalized or "HEV" in normalized:
        return "Hybryda (HEV)"
    if "LPG" in normalized:
        return "Benzyna+LPG"
    return "Benzyna"  # Safe fallback per Rule 2


@lru_cache(maxsize=128)
def fetch_brand_correction_cached(
    samar_class_id: int, brand: str, model: str, engine_name: str
) -> float:
    """Korekta za markę z samar_brand_corrections (V3)."""
    if not brand:
        return 0.0
    try:
        from core.database import supabase

        brand_norm = brand.strip().upper()
        model_norm = model.strip().upper() if model else ""
        fuel_norm = _normalize_fuel_name(brand, engine_name)

        # 1. Exact match with model + fuel
        if model_norm:
            res_exact = (
                supabase.table("samar_brand_corrections")
                .select("korekta")
                .eq("klasa_samar", samar_class_id)
                .ilike("marka", brand_norm)
                .ilike("model", model_norm)
                .ilike("silnik", f"%{fuel_norm}%")
                .limit(1)
                .execute()
            )
            if res_exact.data:
                return float(res_exact.data[0].get("korekta") or 0.0)

        # 2. Fallback to general brand + fuel (model IS NULL)
        res_gen = (
            supabase.table("samar_brand_corrections")
            .select("korekta")
            .eq("klasa_samar", samar_class_id)
            .ilike("marka", brand_norm)
            .is_("model", "null")
            .ilike("silnik", f"%{fuel_norm}%")
            .limit(1)
            .execute()
        )
        if res_gen.data:
            return float(res_gen.data[0].get("korekta") or 0.0)

        # 3. Absolute fallback: Brand only
        res_br = (
            supabase.table("samar_brand_corrections")
            .select("korekta")
            .eq("klasa_samar", samar_class_id)
            .ilike("marka", brand_norm)
            .is_("model", "null")
            .limit(1)
            .execute()
        )
        if res_br.data:
            return float(res_br.data[0].get("korekta") or 0.0)

    except Exception as exc:
        logger.warning("Błąd brand correction: %s", exc)
    return 0.0


@lru_cache(maxsize=128)
def fetch_base_options_rate_cached(
    samar_class_id: int, engine_type_id: int, years: int
) -> float:
    """Pobiera stawkę amortyzacji opcji z samar_class_options_rv."""
    try:
        from core.database import supabase

        res = (
            supabase.table("samar_class_options_rv")
            .select("options_rv_percent")
            .eq("samar_class_id", samar_class_id)
            .eq("engine_type_id", engine_type_id)
            .eq("year", years)
            .limit(1)
            .execute()
        )
        if res.data:
            return float(res.data[0].get("options_rv_percent") or 0.0)
    except Exception as exc:
        logger.warning("Błąd options rate fetch: %s", exc)
    return 0.0


@lru_cache(maxsize=128)
def fetch_mileage_corrections_cached(samar_class_id: int) -> tuple[float, float, int]:
    """Stawki korekty przebiegu: (below, above, threshold_km)."""
    try:
        from core.database import supabase

        res = (
            supabase.table("samar_class_mileage_corrections")
            .select("korekta_lt_prog, korekta_gt_prog, prog_przebiegu_km")
            .eq("klasa_samar", samar_class_id)
            .limit(1)
            .execute()
        )
        if res.data:
            row = res.data[0]
            return (
                float(row.get("korekta_lt_prog", 0.0)),
                float(row.get("korekta_gt_prog", 0.0)),
                int(row.get("prog_przebiegu_km") or 140000),
            )
    except Exception as exc:
        logger.warning("Błąd mileage corrections: %s", exc)
    return (0.0, 0.0, 140000)


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
        return fetch_base_rv_percent_cached(self.data.samar_class_id, self.data.engine_id)

    def _fetch_depreciation_rates(self) -> Dict[str, float]:
        """Pobiera mnożniki przyrostów modyfikujących (delta) z tab_okres_final (V3)."""
        engine_name = self.data.engine_name or self.data.fuel_name or "BENZYNA"
        rates = fetch_depreciation_rates_cached(
            self.data.samar_class_id, self.data.brand_name, engine_name
        )
        if not rates:
            raise ValueError(f"Brak rekordów z tabeli tab_okres_final (delta) dla klasy={self.data.samar_class_id}, silnik={engine_name}")
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
        return fetch_mileage_corrections_cached(self.data.samar_class_id)

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

    def fetch_zabudowa_correction(self) -> float:
        """Korekta zabudowy dla aut dostawczych."""
        if not self.data.zabudowa_apr_wr:
            return 0.0
        # Zabudowa IDs współdzielą tabelę z body_types
        target_id = self.data.zabudowa_type_id or self.data.body_type_id
        return fetch_zabudowa_correction_cached(target_id, self.data.samar_class_id)

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
        print(
            f"\n[DEBUG_RV_DUMP] START calculate_values for class {self.data.samar_class_id}"
        )
        rates = self._fetch_depreciation_rates()
        print(f"[DEBUG_RV_DUMP] Rates keys: {list(rates.keys())}")
        print(f"[DEBUG_RV_DUMP] Rate 0: {rates.get(0)}")

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
        print(
            f"[DEBUG_RV_DUMP] Base Netto: {base_netto}, Options Netto: {options_netto}"
        )

        # Przybliżenie dniowe stosowane w modelu Excelowym (~30.5 dnia)
        years = int((self.data.months * 30.5) / 365)
        years = max(0, min(years, self.LICZBA_LAT))

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 1 & 2: ODCZYT BAZY I WYLICZENIE DELT Z tab_okres_final
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        brand_correction = self._fetch_brand_correction()
        base_rate_4y = self._fetch_base_rv_percent()  # Pobrane dla 4 lat (140,000 km) z samar_class_base_rv
        
        mileage_rates = rates  # Słownik pobrany z tab_okres_final
        if not mileage_rates:
            raise ValueError(f"Brak stawek w tab_okres_final dla klasy {self.data.samar_class_id}")
            
        ordered_keys = ["km_35000", "km_70000", "km_105000", "km_140000", "km_175000", "km_210000", "km_245000"]
        base_key = "km_140000"
        base_idx = ordered_keys.index(base_key)

        def get_wr_percent_for_year(yr: int) -> float:
            """Oblicza skumulowane WR% (Base_4Y + delty) dla zadanego roku (1-7)."""
            if yr < 1:
                yr = 1
            if yr > 7:
                yr = 7
            target_key = ordered_keys[yr - 1]
            target_idx = ordered_keys.index(target_key)
            modifier_sum = 0.0
            
            if target_idx < base_idx:
                for i in range(target_idx, base_idx):
                    modifier_sum += float(mileage_rates.get(ordered_keys[i], 0.0))
            elif target_idx > base_idx:
                for i in range(base_idx + 1, target_idx + 1):
                    # W tabeli wpisane są dodatnie kwoty utraty wartości dla lat > 4, więc je odejmujemy
                    modifier_sum -= float(mileage_rates.get(ordered_keys[i], 0.0))
            return base_rate_4y + modifier_sum

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
        # KROK 4: Korekta przebiegu (1:1 z GSheets - TAB.PRZEBIEG)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        under_rate, over_rate, threshold_km = self._fetch_mileage_corrections()

        base_mileage = (self.data.months / 12.0) * 35000.0
        
        przebieg_ponizej = min(self.data.total_km, threshold_km) - base_mileage
        przebieg_powyzej = max(self.data.total_km - threshold_km, 0.0)

        p1 = przebieg_ponizej / 10000.0
        p2 = przebieg_powyzej / 10000.0

        # Wzór: korektaProcentPonizej190 * okresPlusDoposazenie * (przebiegPonizej190 / 10000.0m) 
        #       + korektaProcentPowyzej190 * okresPlusDoposazenie * (przebiegPowyzej190 / 10000.0m)
        korekta_przebieg_netto = (under_rate * rv_total_netto * p1) + (over_rate * rv_total_netto * p2)
        
        # Odejmowanie ujemnej wartości tworzy aprecjację (zwiększa rv_netto_post_krok4).
        rv_netto_post_krok4 = rv_total_netto - korekta_przebieg_netto

        debug["krok4_base_mileage"] = base_mileage
        debug["krok4_threshold_km"] = threshold_km
        debug["krok4_przebieg_ponizej"] = przebieg_ponizej
        debug["krok4_przebieg_powyzej"] = przebieg_powyzej
        debug["krok4_p1"] = p1
        debug["krok4_p2"] = p2
        debug["krok4_under_rate"] = under_rate
        debug["krok4_over_rate"] = over_rate
        debug["krok4_korekta_przebieg_netto"] = round(korekta_przebieg_netto, 2)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KROK 5: Korekty dodatkowe (kolor, nadwozie)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        color_correction_pct = self.fetch_color_correction()
        color_value_netto = color_correction_pct * base_netto

        body_correction_pct = self.fetch_body_correction()
        zabudowa_correction_pct = self.fetch_zabudowa_correction()
        catalog_total_netto = base_netto + options_netto
        body_value_netto = body_correction_pct * catalog_total_netto
        zabudowa_value_netto = zabudowa_correction_pct * catalog_total_netto

        # Zgodnie z Monolitem nadwozie + zabudowa sumują się do korekty dodatkowej
        krok5_body_netto = body_value_netto + zabudowa_value_netto

        rv_netto_pre_manual = (
            rv_netto_post_krok4
            + color_value_netto
            + krok5_body_netto
        )

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
        debug["krok5_body_netto"] = round(krok5_body_netto, 2)
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
    """Korekta nadwozia z kaskada fallbackow (marka + nadwozie + silnik)
    ORAZ globalny fallback z body_types.utrata_wartosci.
    """
    if not body_type_id:
        return 0.0

    brand = brand_name.strip().upper() if brand_name else ""

    def _extract(rows: list[dict]) -> float:
        return float(rows[0].get("correction_percent") or 0.0)

    # 1. Kaskada lookupów w body_type_wr_corrections
    try:
        from core.database import supabase

        tbl = "body_type_wr_corrections"
        cols = "correction_percent"

        # 1.1 EXACT: marka + nadwozie + silnik
        if brand and engine_id:
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

        # 1.2 NO-ENGINE: marka + nadwozie (engine IS NULL)
        if brand:
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

        # 1.3 NO-BODY: marka (body IS NULL, engine IS NULL)
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

        # 1.4 GLOBAL FALLBACK w tabeli korekt (brand='', engine=NULL)
        res = (
            supabase.table(tbl)
            .select(cols)
            .eq("brand_name", "")
            .eq("body_type_id", body_type_id)
            .is_("engine_type_id", "null")
            .limit(1)
            .execute()
        )
        if res.data:
            return _extract(res.data)

    except Exception as exc:
        logger.warning("Błąd kaskady body correction: %s", exc)

    return 0.0


@lru_cache(maxsize=128)
def fetch_zabudowa_correction_cached(
    body_type_id: Optional[int], samar_class_id: int
) -> float:
    """Korekta zabudowy dla dostawczych (Typ Zabudowy + Klasa SAMAR) bez marki."""
    if not body_type_id:
        return 0.0

    def _extract(rows: list[dict]) -> float:
        return float(rows[0].get("zabudowa_correction_percent") or 0.0)

    try:
        from core.database import supabase

        tbl = "body_type_wr_corrections"
        cols = "zabudowa_correction_percent"

        # 1. Typ Zabudowy + Klasa SAMAR (brand='')
        res = (
            supabase.table(tbl)
            .select(cols)
            .eq("body_type_id", body_type_id)
            .eq("samar_class_id", samar_class_id)
            .eq("brand_name", "")
            .limit(1)
            .execute()
        )
        if res.data:
            return _extract(res.data)

        # 2. GLOBAL FALLBACK: tylko Typ Zabudowy (samar_class IS NULL)
        res2 = (
            supabase.table(tbl)
            .select(cols)
            .eq("body_type_id", body_type_id)
            .is_("samar_class_id", "null")
            .eq("brand_name", "")
            .limit(1)
            .execute()
        )
        if res2.data:
            return _extract(res2.data)

    except Exception as exc:
        logger.warning("Blad zabudowa correction: %s", exc)

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
