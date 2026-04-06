"""Cached DB fetch functions for SAMAR RV calculator.

All database lookups use @redis_cache with TTL to ensure data freshness
when admin updates rates without server restart.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from core.redis_cache import redis_cache

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Słownik kanonicznych rodzajów paliwa
# ═══════════════════════════════════════════════════════════════════

# Muszą dokładnie odpowiadać wartościom w kolumnie `rodzaj_silnika`
# tabeli `tab_okres_final`.
KNOWN_FUEL_TYPES: frozenset[str] = frozenset(
    [
        "Benzyna",
        "Diesel",
        "Elektryczny",
        "Hybryda Plug-in",
        "Hybryda (HEV)",
        "Benzyna+LPG",
        "Wodór",
    ]
)


def _normalize_fuel_name(brand: str, engine_name: str) -> str:
    """Ujednolica nazwy paliw na potrzeby lookupów w V3 (rodzaj_silnika).

    Mapuje wyłącznie na wartości z KNOWN_FUEL_TYPES (1:1 z tab_okres_final).
    Przy nieznanym paliwie rzuca ValueError (Fail-Fast — GEMINI.md §2A).
    """
    normalized = engine_name.strip().upper()

    if "BENZYNA" in normalized and "LPG" in normalized:
        return "Benzyna+LPG"
    if "LPG" in normalized:
        return "Benzyna+LPG"
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
    if "WODÓR" in normalized or "WODOR" in normalized or "H2" in normalized:
        return "Wodór"

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

        # 2. Fallback: general brand + fuel (model IS NULL)
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

    except ValueError:
        raise  # Propagate fuel normalization errors
    except Exception as exc:
        logger.warning("Błąd pobierania brand correction dla %s: %s", brand, exc)
    return 0.0


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_color_correction_cached(
    paint_type_id: Optional[int], is_metalic: bool
) -> float:
    """Korekta za kolor z paint_types.wr_correction."""
    if not paint_type_id:
        return 0.0
    from core.database import supabase

    try:
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


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_body_correction_cached(
    engine_id: int, brand_name: str, body_type_id: Optional[int]
) -> float:
    """Korekta nadwozia z kaskadą fallbacków (marka + nadwozie + silnik).

    ORAZ globalny fallback z body_types.utrata_wartosci.
    """
    if not body_type_id:
        return 0.0

    from core.database import supabase

    brand = brand_name.strip().upper() if brand_name else ""

    def _extract(rows: list[dict]) -> float:  # type: ignore[type-arg]
        return float(rows[0].get("correction_percent") or 0.0)

    try:
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


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_zabudowa_correction_cached(
    body_type_id: Optional[int], samar_class_id: int
) -> float:
    """Korekta zabudowy dla dostawczych (Typ Zabudowy + Klasa SAMAR) bez marki."""
    if not body_type_id:
        return 0.0

    from core.database import supabase

    def _extract(rows: list[dict]) -> float:  # type: ignore[type-arg]
        return float(rows[0].get("zabudowa_correction_percent") or 0.0)

    try:
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
        logger.warning("Błąd zabudowa correction: %s", exc)

    return 0.0


@redis_cache(ttl_seconds=3600, prefix="samar_rv:")
def fetch_vintage_correction_cached(rocznik: str) -> float:
    """Korekta za rocznik z ltr_admin_korekta_wr_roczniks."""
    from core.database import supabase

    vintage_map = {"current": "bieżący", "previous": "bieżący-1"}
    db_key = vintage_map.get(rocznik, rocznik)
    try:
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


@redis_cache(ttl_seconds=900, prefix="samar_rv:")
def fetch_lo_param_cached() -> float:
    """PrzewidywanaCenaSprzedazyLO z control_center (kolumna)."""
    from core.database import supabase

    try:
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
        res = (
            supabase.table("samar_class_mileage_corrections")
            .select("korekta_lt_prog, korekta_gt_prog, prog_przebiegu_km")
            .eq("klasa_samar", samar_class_id)
            .ilike("rodzaj_silnika", f"%{fuel_norm}%")
            .limit(1)
            .execute()
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
