"""Readiness check dla kalkulatora SAMAR RV.

Sprawdza pokrycie parametrów w DB przed kalkulacją (6 monolitów).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.database import supabase
from core.samar_rv_fetchers import _normalize_fuel_name

logger = logging.getLogger(__name__)


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
        cols = [f"km_{km}" for km in range(35000, 245001, 35000)]
        try:
            fuel_norm = _normalize_fuel_name(brand_name, engine_name)
        except ValueError as fuel_exc:
            checks.append(
                ReadinessItem(
                    "1. Bazowa Utrata Wartości",
                    "error",
                    f"nieznany rodzaj silnika: '{engine_name}' — {fuel_exc}",
                )
            )
            fuel_norm = ""

        if fuel_norm:
            res = (
                supabase.table("tab_okres_final")
                .select(", ".join(cols))
                .eq("klasa_samar", samar_class_id)
                .ilike("rodzaj_silnika", f"%{fuel_norm}%")
                .execute()
            )
            if res.data:
                row = res.data[0]
                missing_cols = [c for c in cols if row.get(c) is None]
                if not missing_cols:
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

    # 2. Monolit: Korekta Przebiegu - samar_class_mileage_corrections
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
            checks.append(ReadinessItem("2. Korekta Przebiegu", "warn", "brak wpisu → 0"))
    except Exception as exc:
        logger.warning("Błąd odczytu mileage corrections: %s", exc)
        checks.append(ReadinessItem("2. Korekta Przebiegu", "warn", "brak wpisu → 0"))

    # 3. Monolit: Korekta Marki - samar_brand_corrections
    try:
        brand = brand_name.strip().upper()
        found_val = None
        found_type = ""

        try:
            fuel_norm = _normalize_fuel_name(brand, engine_name)
        except ValueError:
            fuel_norm = ""

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
                ReadinessItem("3. Korekta Marki", "ok", f"{found_val:+.1%} {found_type}")
            )
        else:
            checks.append(ReadinessItem("3. Korekta Marki", "warn", "brak wpisu → 0%"))
    except Exception as exc:
        logger.warning("Błąd odczytu brand corrections: %s", exc)
        checks.append(ReadinessItem("3. Korekta Marki", "warn", "błąd odczytu → 0%"))

    # 4. Monolit: Korekta Nadwozia - body_type_wr_corrections
    if body_type_id:
        try:
            brand = brand_name.strip().upper() if brand_name else ""
            found_val = None
            found_type = ""

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

    # 5. Monolit: Korekta Zabudowy (Dostawcze)
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
                        ReadinessItem("5. Korekta Zabudowy", "ok", f"{val:+.1%} (Globalna)")
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
        checks.append(
            ReadinessItem("5. Korekta Zabudowy", "ok", "Brak zabudowy specjalnej (0%)")
        )

    # 6. Monolit: Korekta Lakieru - paint_types
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
        checks.append(ReadinessItem("6. Korekta Lakieru", "ok", "Brak kodu lakieru (0%)"))

    return checks
