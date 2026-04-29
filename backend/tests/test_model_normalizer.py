"""Tests for model_normalizer using real cases from production DB (vehicle_synthesis)."""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model_normalizer import (
    BODY_ALIASES,
    SOT_BODY_TYPES,
    normalize_model_trim_body,
    normalize_trim,
)


# (raw_model, brand, raw_trim, raw_body) → (model, trim, body)
REAL_CASES = [
    # Skoda: trim baked into model
    ("Octavia RS", "SKODA", "RS", "Liftback",
     "Octavia", "RS", "Liftback"),
    ("Kodiaq Drive", "SKODA", "Drive", "SUV",
     "Kodiaq", "Drive", "SUV"),
    ("Superb Drive", "SKODA", "Drive", "Liftback",
     "Superb", "Drive", "Liftback"),
    ("Fabia Selection", "SKODA", "Selection", "Hatchback",
     "Fabia", "Selection", "Hatchback"),
    ("Elroq RS", "SKODA", "RS", "SUV",
     "Elroq", "RS", "SUV"),
    # Body type in model + trim
    ("Octavia Combi Drive Essence", "SKODA", "Drive Essence", "Kombi",
     "Octavia", "Drive Essence", "Kombi"),
    ("Octavia Combi Drive Selection", "SKODA", "Drive Selection", "Kombi",
     "Octavia", "Drive Selection", "Kombi"),
    ("Superb Combi", "SKODA", "Selection", "Kombi",
     "Superb", "Selection", "Kombi"),
    ("Octavia Combi", "SKODA", "Drive Essence", "Kombi",
     "Octavia", "Drive Essence", "Kombi"),
    # Brand prefix
    ("Škoda Superb Combi Sportline", "SKODA", "Sportline", "Kombi",
     "Superb", "Sportline", "Kombi"),
    ("Škoda Superb Edition 130", "SKODA", "Edition 130", "Kombi",
     "Superb", "Edition 130", "Kombi"),
    # Year code + ALL CAPS
    ("SUPERB RM2022 AMBITION", "SKODA", "Ambition", "Liftback",
     "Superb", "Ambition", "Liftback"),
    # Already clean (no-op expected)
    ("Octavia", "SKODA", "Essence", "Liftback",
     "Octavia", "Essence", "Liftback"),
    ("Octavia", "SKODA", "Sportline", "Liftback",
     "Octavia", "Sportline", "Liftback"),
    ("Kodiaq", "SKODA", "Sportline", "SUV",
     "Kodiaq", "Sportline", "SUV"),
    ("Superb", "SKODA", "L&K", "Liftback",
     "Superb", "L&K", "Liftback"),
    # VW: trim suffix and extension
    ("Tayron Elegance", "VOLKSWAGEN", "Elegance", "SUV",
     "Tayron", "Elegance", "SUV"),
    ("Tayron. Elegance", "VOLKSWAGEN", "Elegance", "SUV",
     "Tayron", "Elegance", "SUV"),
    # Trim extension: 'Business' → 'Business Plus' (rest of model after trim)
    ("Passat Business Plus", "VOLKSWAGEN", "Business", "Kombi",
     "Passat", "Business Plus", "Kombi"),
    # VW commercials with body in model name
    ("Crafter Furgon", "VOLKSWAGEN", "Pro", "Furgon",
     "Crafter", "Pro", "Furgon"),
    ("Crafter Furgon. Furgon z wysokim dachem", "VOLKSWAGEN", "Furgon z wysokim dachem", "Furgon",
     "Crafter", None, "Furgon"),  # trim is body descriptor → null
    ("Transporter Kombi", "VOLKSWAGEN", "Kombi N1", "Kombi",
     "Transporter", None, "Kombi"),  # trim is body descriptor
    ("Golf Variant. Life Plus", "VOLKSWAGEN", "Life Plus", "Kombi",
     "Golf", "Life Plus", "Kombi"),  # Variant→Kombi alias
    # Audi: engine spec + body alias
    ("Audi A6 Sedan 45 TFSI quattro 195 kW (265 KM) S tronic", "AUDI", "45 TFSI quattro", "Sedan",
     "A6", None, "Sedan"),  # trim was engine → null
    ("A5 Avant TFSI quattro 150 kW S tronic", "AUDI", "S line", "Avant",
     "A5", "S line", "Kombi"),  # body Avant → Kombi
    ("A5 Avant", "AUDI", "S line", "Kombi",
     "A5", "S line", "Kombi"),
    # BMW: engine spec — keep 320i as model
    ("320i xDrive Limuzyna", "BMW", "Brak", "Limuzyna",
     "320i", None, "Sedan"),  # Brak→null, Limuzyna→Sedan
    ("X3", "BMW", "20 xDrive", "SUV",
     "X3", None, "SUV"),  # engine-only trim → null
    # CUPRA / FORD / others
    ("LEON SPORTSTOURER", "CUPRA", "Brak", "Sportstourer",
     "Leon", None, "Kombi"),  # ALL CAPS → title, body alias
    ("DUSTER", "DACIA", "Expression", "SUV",
     "Duster", "Expression", "SUV"),
    ("Kuga", "FORD", "ST-LINE", "SUV",
     "Kuga", "ST-LINE", "SUV"),
    ("Ranger", "FORD", "WILDTRAK PHEV", "Pickup",
     "Ranger", "WILDTRAK PHEV", "Pickup"),
    ("TRANSIT CUSTOM", "FORD", "Trend", "Van",
     "Transit Custom", "Trend", "Van"),
    ("SANTA FE", "HYUNDAI", "Executive", "SUV",
     "Santa Fe", "Executive", "SUV"),
    ("RANGE ROVER SPORT S", "LAND ROVER", "S", "SUV",
     "Range Rover Sport", "S", "SUV"),  # Strip 'S' trim from end
    # Edge case: trim already in model but not redundantly
    ("V60", "VOLVO", "Core", "Kombi",
     "V60", "Core", "Kombi"),
    ("XC60", "VOLVO", "Core", "SUV",
     "XC60", "Core", "SUV"),
]


@pytest.mark.parametrize(
    "raw_model,brand,raw_trim,raw_body,exp_model,exp_trim,exp_body",
    REAL_CASES,
    ids=[c[0] for c in REAL_CASES],
)
def test_real_cases(raw_model, brand, raw_trim, raw_body, exp_model, exp_trim, exp_body):
    model, trim, body = normalize_model_trim_body(raw_model, brand, raw_trim, raw_body)
    assert model == exp_model, f"model: got {model!r}, expected {exp_model!r}"
    assert trim == exp_trim, f"trim: got {trim!r}, expected {exp_trim!r}"
    assert body == exp_body, f"body: got {body!r}, expected {exp_body!r}"


def test_normalize_trim_strips_brak():
    assert normalize_trim("Brak") is None
    assert normalize_trim("brak") is None
    assert normalize_trim("-") is None
    assert normalize_trim("") is None
    assert normalize_trim(None) is None
    assert normalize_trim("  ") is None


def test_normalize_trim_strips_engine_only():
    assert normalize_trim("45 TFSI quattro") is None
    assert normalize_trim("20 xDrive") is None
    assert normalize_trim("2.0 TDI") is None


def test_normalize_trim_passes_real_trims():
    assert normalize_trim("Sportline") == "Sportline"
    assert normalize_trim("L&K") == "L&K"
    assert normalize_trim("R-Line") == "R-Line"
    assert normalize_trim("S line") == "S line"
    assert normalize_trim("  Drive  ") == "Drive"


def test_null_inputs():
    model, trim, body = normalize_model_trim_body(None, None, None, None)
    assert model is None
    assert trim is None
    assert body is None


def test_sot_completeness():
    """Sanity check that SOT_BODY_TYPES has 32 rows and all common ones are present."""
    assert len(SOT_BODY_TYPES) == 32
    for body in ("Hatchback", "Kombi", "Sedan", "SUV", "Liftback", "Furgon", "Pickup", "Van"):
        assert body in SOT_BODY_TYPES


def test_body_aliases_map_to_sot():
    """Every alias must map to a real SOT body type."""
    for alias, sot in BODY_ALIASES.items():
        assert sot in SOT_BODY_TYPES, f"alias {alias!r} maps to non-SOT {sot!r}"
