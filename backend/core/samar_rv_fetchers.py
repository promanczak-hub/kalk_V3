"""Cached DB fetch functions for SAMAR RV calculator.

All database lookups use @redis_cache with TTL to ensure data freshness
when admin updates rates without server restart.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from core.redis_cache import redis_cache
from core.supabase_retry import execute_with_retry

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Słownik kanonicznych rodzajów paliwa
# ═══════════════════════════════════════════════════════════════════

# Muszą dokładnie odpowiadać wartościom w kolumnie `rodzaj_silnika`
# tabeli `tab_okres_final` (SOT). Aktualne wartości w DB (9 sztuk):
#   "Benzyna (PB)", "Benzyna mHEV (PB-mHEV)",
#   "Diesel (ON)", "Diesel mHEV (ON-mHEV)",
#   "Hybryda (HEV)", "Plug-in Hybrid (PHEV)",
#   "Elektryczny (BEV)", "Wodór (FCEV)", "LPG"
KNOWN_FUEL_TYPES: frozenset[str] = frozenset(
    [
        "Benzyna (PB)",
        "Benzyna mHEV (PB-mHEV)",
        "Diesel (ON)",
        "Diesel mHEV (ON-mHEV)",
        "Hybryda (HEV)",
        "Plug-in Hybrid (PHEV)",
        "Elektryczny (BEV)",
        "Wodór (FCEV)",
        "LPG",
    ]
)

# Mapowanie engine_type_id (z tabeli `engines`) → kanoniczna nazwa
# z `tab_okres_final.rodzaj_silnika`. Identyczne z engines.name 1:1.
ENGINE_ID_TO_FUEL: dict[int, str] = {
    1: "Benzyna (PB)",
    2: "Diesel (ON)",
    3: "Benzyna mHEV (PB-mHEV)",
    4: "Diesel mHEV (ON-mHEV)",
    5: "Hybryda (HEV)",
    6: "Plug-in Hybrid (PHEV)",
    7: "Elektryczny (BEV)",
    8: "Wodór (FCEV)",
    9: "LPG",
}


def fuel_name_for_engine_id(engine_type_id: int) -> str | None:
    """Zwraca kanoniczną nazwę rodzaj_silnika dla engine_type_id (1-9).

    None gdy nieznane ID — caller może zrobić fallback przez _normalize_fuel_name.
    """
    return ENGINE_ID_TO_FUEL.get(int(engine_type_id) if engine_type_id else 0)


def _normalize_fuel_name(brand: str, engine_name: str) -> str:
    """Ujednolica nazwy paliw na potrzeby lookupów w tab_okres_final.

    Pipeline:
      1. Jeśli engine_name już jest kanoniczną nazwą (w KNOWN_FUEL_TYPES) → zwróć as-is.
      2. Inaczej legacy heurystyki keyword → mapuj na kanoniczną nazwę.
      3. Inaczej ValueError (Fail-Fast).

    Argumenty:
        brand: marka (tylko do error msg, nie wpływa na mapowanie).
        engine_name: dowolna postać (np. "Benzyna (PB)", "BENZYNA", "Diesel", "PHEV").
    """
    if engine_name in KNOWN_FUEL_TYPES:
        return engine_name

    n = engine_name.strip().upper()

    # mHEV warianty (sprawdzić PRZED czystą "BENZYNA"/"DIESEL", bo zawierają te słowa)
    if "MHEV" in n or "PB-MHEV" in n:
        if "DIESEL" in n or "ON" in n:
            return "Diesel mHEV (ON-mHEV)"
        return "Benzyna mHEV (PB-mHEV)"
    if "ON-MHEV" in n:
        return "Diesel mHEV (ON-mHEV)"

    # PHEV (sprawdzić PRZED ogólnym "HEV")
    if "PHEV" in n or "PLUG-IN" in n or "PLUG IN" in n:
        return "Plug-in Hybrid (PHEV)"

    # LPG (sprawdzić PRZED "BENZYNA" bo "Benzyna+LPG" zawiera oba)
    if "LPG" in n:
        return "LPG"

    # BEV / elektryczny
    if "ELEKTRYCZNY" in n or "BEV" in n or n == "EV":
        return "Elektryczny (BEV)"

    # Wodór
    if "WODÓR" in n or "WODOR" in n or "FCEV" in n or "H2" in n:
        return "Wodór (FCEV)"

    # HEV (po PHEV i mHEV)
    if "HEV" in n or "HYBRYDA" in n:
        return "Hybryda (HEV)"

    # Czysta benzyna / diesel
    if "BENZYNA" in n or n == "PB":
        return "Benzyna (PB)"
    if "DIESEL" in n or n == "ON":
        return "Diesel (ON)"

    raise ValueError(
        f"Nieznany rodzaj silnika: '{engine_name}' (brand={brand!r}). "
        f"Musi być jednym z: {sorted(KNOWN_FUEL_TYPES)}. "
        "Uzupełnij mapowanie lub popraw dane pojazdu."
    )


# ═══════════════════════════════════════════════════════════════════
# Cached DB fetchers — Redis TTL zamiast lru_cache
# ═══════════════════════════════════════════════════════════════════


@redis_cache(ttl_seconds=1800, prefix="samar_rv:")
def fetch_base_rv_percent_cached(samar_class_id: int, engine_type_id: int) -> float:
    """Pobiera 4-letnią bazę WR% z samar_class_depreciation_rates."""
    COLUMN_MAP = {
        1: "benzyna_pb",
        2: "diesel_on",
        3: "benzyna_mhev_pb_mhev",
        4: "diesel_mhev_on_mhev",
        5: "hybryda_hev",
        6: "plug_in_hybrid_phev",
        7: "elektryczny_bev",
        8: "wodor_fcev",
        9: "lpg",
    }
    from core.database import supabase

    col_name = COLUMN_MAP.get(engine_type_id, "benzyna_pb")
    try:
        res = execute_with_retry(
            supabase.table("samar_class_depreciation_rates")
            .select(col_name)
            .eq("klasa_samar", samar_class_id)
            .limit(1)
        )
        if res.data and len(res.data) > 0:
            val = res.data[0].get(col_name)
            if val is not None:
                return float(val)
    except Exception as exc:
        logger.warning(
            "Błąd pobierania base_rv_percent dla klasy=%s, silnik=%s: %s",
            samar_class_id,
            engine_type_id,
            exc,
        )
    raise ValueError(
        f"Brak przypisanego Base RV w samar_class_depreciation_rates "
        f"dla klasy={samar_class_id}, silnik={engine_type_id}"
    )


@redis_cache(ttl_seconds=1800, prefix="samar_rv:")
def fetch_depreciation_rates_cached(
    samar_class_id: int, brand_name: str, engine_name: str
) -> Dict[str, float]:
    """Pobiera linię różnic z tab_okres_final aby narzucić ją na BAZĘ 140_000."""
    from core.database import supabase

    try:
        fuel_norm = _normalize_fuel_name(brand_name, engine_name)
        res = execute_with_retry(
            supabase.table("tab_okres_final")
            .select(
                "km_35000, km_70000, km_105000, km_140000, km_175000, km_210000, km_245000"
            )
            .eq("klasa_samar", samar_class_id)
            .ilike("rodzaj_silnika", f"%{fuel_norm}%")
            .limit(1)
        )
        if res.data:
            return dict(res.data[0])
    except ValueError:
        raise  # Propagate fuel normalization errors (Fail-Fast)
    except Exception as exc:
        logger.warning("Błąd pobierania tab_okres_final: %s", exc)
    return {}


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_brand_correction_cached(
    samar_class_id: int, brand: str, model: str, engine_name: str
) -> float:
    """Korekta za markę z samar_brand_corrections (V3)."""
    if not brand:
        return 0.0
    from core.database import supabase

    try:
        brand_norm = brand.strip().upper()
        model_norm = model.strip().upper() if model else ""
        fuel_norm = _normalize_fuel_name(brand, engine_name)

        # 1. Exact match with model + fuel
        if model_norm:
            res_exact = execute_with_retry(
                supabase.table("samar_brand_corrections")
                .select("korekta")
                .eq("klasa_samar", samar_class_id)
                .ilike("marka", brand_norm)
                .ilike("model", model_norm)
                .ilike("silnik", f"%{fuel_norm}%")
                .limit(1)
            )
            if res_exact.data:
                return float(res_exact.data[0].get("korekta") or 0.0)

        # 2. Fallback: general brand + fuel (model IS NULL)
        res_gen = execute_with_retry(
            supabase.table("samar_brand_corrections")
            .select("korekta")
            .eq("klasa_samar", samar_class_id)
            .ilike("marka", brand_norm)
            .is_("model", "null")
            .ilike("silnik", f"%{fuel_norm}%")
            .limit(1)
        )
        if res_gen.data:
            return float(res_gen.data[0].get("korekta") or 0.0)

    except ValueError:
        raise  # Propagate fuel normalization errors
    except Exception as exc:
        logger.warning("Błąd pobierania brand correction dla %s: %s", brand, exc)
    return 0.0


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_color_correction_cached(
    paint_type_id: Optional[int], is_metalic: bool
) -> float:
    """Korekta za kolor z paint_types.wr_correction.

    Gdy `paint_type_id` jest pusty (część payloadów z frontu nie wysyła
    `paint_type_name`/`paint_category_id`), spada się na `is_metalic`:
    False → "Niemetalizowany", True → "Metalizowany". Pearl wymaga
    explicit ID, więc tu nie pasuje.
    """
    from core.database import supabase

    if not paint_type_id:
        try:
            res = execute_with_retry(supabase.table("paint_types").select("name, wr_correction"))
            for row in res.data or []:
                name_upper = str(row.get("name") or "").upper()
                if not is_metalic and name_upper.startswith("NIEMETAL"):
                    return float(row.get("wr_correction") or 0.0)
                if is_metalic and name_upper.startswith("METALIZ"):
                    return float(row.get("wr_correction") or 0.0)
        except Exception as exc:
            logger.warning("Błąd color correction (is_metalic fallback): %s", exc)
        return 0.0

    try:
        res = execute_with_retry(
            supabase.table("paint_types")
            .select("wr_correction")
            .eq("id", paint_type_id)
            .limit(1)
        )
        if res.data:
            return float(res.data[0].get("wr_correction") or 0.0)
    except Exception as exc:
        logger.warning("Błąd color correction: %s", exc)
    return 0.0


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_body_correction_cached(body_type_id: Optional[int]) -> float:
    """Korekta WR per typ nadwozia.

    SOT: GSheet body_types.Korekta (gid=484265370) → DB body_types.utrata_wartosci.
    Composite cabin+zabudowa (np. "Podwozie Brygadowe Skrzynia") jest pojedynczym
    body_type, więc nie potrzebujemy osobnej korekty zabudowy.
    """
    if not body_type_id:
        return 0.0

    from core.database import supabase

    try:
        res = execute_with_retry(
            supabase.table("body_types")
            .select("utrata_wartosci")
            .eq("id", body_type_id)
            .limit(1)
        )
        if res.data:
            return float(res.data[0].get("utrata_wartosci") or 0.0)
    except Exception as exc:
        logger.warning("Błąd body correction: %s", exc)

    return 0.0


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_vintage_correction_cached(
    rocznik: str, samar_class_id: int | None = None
) -> float:
    """Korekta za rocznik z `ltr_admin_korekta_wr_roczniks` (per klasa SAMAR).

    Aktualny schemat DB (2026-05-16):
        klasa_samar_fk          : FK do samar_classes.id
        rocznik_biezacy         : korekta dla "current" rocznika (zwykle 0.0)
        korekta_za_ubiegly_rocznik : korekta dla "previous" (-1) rocznika (zwykle -0.08)

    Wcześniejsza wersja querowała nieistniejące kolumny `rocznik`/`korekta_procent`
    i cicho zwracała 0.0 dla każdego rocznika (catch Exception → 0.0).

    Argumenty:
        rocznik: "current" / "previous" / dowolny inny.
        samar_class_id: opcjonalne — jeśli podane, filtruje per klasa. Bez
            tego bierze pierwszy wiersz (wszystkie klasy w DB mają obecnie
            identyczne wartości, ale design SOT pozwala na różnicowanie).
    """
    from core.database import supabase

    # 2005 Excel SOT (arkusz ROCZNIK): 'bieżący' → 0, 'bieżący -1' (poprzedni) → -0.08.
    # Karę poprzedniego rocznika stosujemy TYLKO dla jawnie poprzedniego rocznika;
    # bieżący / nieznany / pusty / rok kalendarzowy → traktuj jak bieżący (0).
    # (Wcześniej każdy rocznik ≠ dosłownie "current" dostawał karę — np. "2026"
    #  czy "bieżący" → -8%. Bug naprawiony 2026-05-21.)
    _previous_markers = {
        "previous", "prev", "ubiegly", "ubiegły", "poprzedni",
        "bieżący -1", "biezacy -1", "bieżący-1", "biezacy-1", "-1",
    }
    is_previous = str(rocznik).strip().lower() in _previous_markers
    column = "korekta_za_ubiegly_rocznik" if is_previous else "rocznik_biezacy"
    try:
        query = supabase.table("ltr_admin_korekta_wr_roczniks").select(column)
        if samar_class_id:
            query = query.eq("klasa_samar_fk", samar_class_id)
        res = execute_with_retry(query.limit(1))
        if res.data:
            val = res.data[0].get(column)
            if val is not None:
                return float(val)
    except Exception as exc:
        logger.warning(
            "Błąd vintage correction (rocznik=%s, klasa=%s): %s",
            rocznik,
            samar_class_id,
            exc,
        )
    return 0.0


@redis_cache(ttl_seconds=900, prefix="samar_rv:")
def fetch_lo_param_cached() -> float:
    """PrzewidywanaCenaSprzedazyLO z control_center (klucz EAV)."""
    from core.control_center import fetch_control_center_value

    try:
        val = fetch_control_center_value("przewidywana_cena_sprzedazy_lo", default=0.0)
        return float(val) if val is not None else 0.0
    except Exception:
        logger.warning("Nie udało się pobrać PrzewidywanaCenaSprzedazyLO")
    return 0.0


@redis_cache(ttl_seconds=900, prefix="samar_rv:")
def fetch_resale_time_days_cached() -> int:
    """resale_time_days z control_center (EAV).

    Cache'owane bo `SamarRVCalculator._calculate_liczba_lat_v1` czyta tę stałą
    raz NA KOMÓRKĘ matrycy — bez cache to setki round-tripów do Supabase na jedną
    matrycę (objaw: matryca ~2 min → timeout "Failed to fetch" w UI).
    """
    from core.control_center import fetch_control_center_value

    try:
        val = fetch_control_center_value("resale_time_days", default=60)
        return int(val) if val is not None else 60
    except Exception:
        logger.warning("Nie udało się pobrać resale_time_days; fallback 60")
    return 60


@redis_cache(ttl_seconds=1800, prefix="samar_rv:")
def fetch_mileage_corrections_cached(
    samar_class_id: int,
    brand_name: str,
    engine_name: str,
) -> tuple[float, float, float]:
    """Pobiera korekty przebiegu z samar_class_mileage_corrections.

    Filtruje po klasie i znormalizowanym rodzaju silnika (Fail-Fast).

    Returns:
        (korekta_lt_prog, korekta_gt_prog, km_prog)
    """
    from core.database import supabase

    try:
        fuel_norm = _normalize_fuel_name(brand_name, engine_name)
        res = execute_with_retry(
            supabase.table("samar_class_mileage_corrections")
            .select("korekta_lt_prog, korekta_gt_prog, prog_przebiegu_km")
            .eq("klasa_samar", samar_class_id)
            .ilike("rodzaj_silnika", f"%{fuel_norm}%")
            .limit(1)
        )
        if res.data:
            row = res.data[0]
            return (
                float(row.get("korekta_lt_prog") or 0.0),
                float(row.get("korekta_gt_prog") or 0.0),
                float(row.get("prog_przebiegu_km") or 190000.0),
            )
        else:
            # Reverting to Fail-Fast strategy as per GEMINI.md 2A
            logger.error(
                "Brak stawek przebiegu w samar_class_mileage_corrections dla klasy=%s, silnik=%s",
                samar_class_id,
                fuel_norm,
            )
            raise ValueError(
                f"Brak stawek przebiegu (tabela samar_class_mileage_corrections) "
                f"dla klasy {samar_class_id} i silnika '{fuel_norm}'. "
                "Uzupełnij dane w arkuszu/bazie."
            )
    except ValueError:
        raise  # Propagate normalization errors
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        logger.warning(
            "Błąd pobierania mileage corrections dla klasy=%s: %s", samar_class_id, exc
        )
    return 0.0, 0.0, 190000.0


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_base_options_rate_cached(
    samar_class_id: int, engine_type_id: int, years: int
) -> float:
    """Pobiera stawkę amortyzacji opcji z samar_class_options_rv (Fail-Fast).

    NIE łapie wyjątków i NIE zwraca 0.0 przy braku rekordu — bo @redis_cache
    cache'owałby tę 0.0 (nie jest "empty"), zatruwając cache na cały TTL
    (incydent 2026-05-21: transient → 0.0 → fail-fast w kółko). Wyjątek/brak
    rekordu propaguje się jak w fetch_mileage_corrections_cached.
    """
    from core.database import supabase

    res = execute_with_retry(
        supabase.table("samar_class_options_rv")
        .select("options_rv_percent")
        .eq("samar_class_id", samar_class_id)
        .eq("engine_type_id", engine_type_id)
        .eq("year", years)
        .limit(1)
    )
    if res.data:
        val = res.data[0].get("options_rv_percent")
        if val is not None:
            return float(val)
    raise ValueError(
        f"Brak stawki opcji w `samar_class_options_rv` dla klasy={samar_class_id}, "
        f"silnik={engine_type_id}, rok={years} (Reguła Fail-Fast)."
    )
