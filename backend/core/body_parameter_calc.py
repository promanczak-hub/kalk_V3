"""Deterministic cargo parameter calculator.

Computes m², europallets, and volume from cargo dimensions.
NO LLM involved — pure math.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Standard europallet dimensions (mm)
_PALLET_LENGTH_MM = 1200
_PALLET_WIDTH_MM = 800
_MANEUVERING_MARGIN_MM = 50


@dataclass(frozen=True)
class CargoParams:
    """Calculated cargo parameters."""

    area_m2: float | None = None
    volume_m3: float | None = None
    europallets: int | None = None


def calc_cargo_area_m2(
    length_mm: float,
    width_mm: float,
) -> float:
    """Calculate cargo area in m² from length × width in mm."""
    return round((length_mm * width_mm) / 1_000_000, 2)


def calc_cargo_volume_m3(
    length_mm: float,
    width_mm: float,
    height_mm: float,
) -> float:
    """Calculate cargo volume in m³ from dimensions in mm."""
    return round((length_mm * width_mm * height_mm) / 1_000_000_000, 2)


def calc_europallets(
    length_mm: float,
    width_mm: float,
) -> int:
    """Calculate max europallets that fit in cargo area.

    Standard europallet: 1200×800mm.
    Adds maneuvering margin per pallet.
    Checks both orientations and uses the better one.
    """
    eff_pallet_l = _PALLET_LENGTH_MM + _MANEUVERING_MARGIN_MM
    eff_pallet_w = _PALLET_WIDTH_MM + _MANEUVERING_MARGIN_MM

    # Orientation A: pallets lengthwise
    along_a = int(length_mm // eff_pallet_l)
    across_a = int(width_mm // eff_pallet_w)
    count_a = along_a * across_a

    # Orientation B: pallets rotated
    along_b = int(length_mm // eff_pallet_w)
    across_b = int(width_mm // eff_pallet_l)
    count_b = along_b * across_b

    return max(count_a, count_b)


def calculate_cargo_params(
    cargo_length_mm: float | None = None,
    cargo_width_mm: float | None = None,
    cargo_height_mm: float | None = None,
) -> CargoParams:
    """Calculate all cargo parameters from available dimensions.

    Gracefully handles missing dimensions — returns None for
    params that can't be calculated.
    """
    area: float | None = None
    volume: float | None = None
    pallets: int | None = None

    if cargo_length_mm and cargo_width_mm:
        if cargo_length_mm > 0 and cargo_width_mm > 0:
            area = calc_cargo_area_m2(cargo_length_mm, cargo_width_mm)
            pallets = calc_europallets(cargo_length_mm, cargo_width_mm)

            if cargo_height_mm and cargo_height_mm > 0:
                volume = calc_cargo_volume_m3(
                    cargo_length_mm, cargo_width_mm, cargo_height_mm
                )

    return CargoParams(area_m2=area, volume_m3=volume, europallets=pallets)
