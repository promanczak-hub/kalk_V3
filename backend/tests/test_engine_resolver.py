import pytest

from core.ltr_vehicle_resolvers import _resolve_engine_type_id, resolve_engine_type_id


@pytest.mark.parametrize(
    "engine_str,expected",
    [
        # Regression 2026-05-21: "ON" w "kONwencjonalne" NIE może dać Diesla.
        ("Benzyna (PB) (Konwencjonalne (ICE))", 1),
        ("Diesel (ON)", 2),
        ("Diesel mHEV (ON-mHEV)", 4),
        ("Benzyna mHEV (PB-mHEV)", 3),
        ("Hybryda (HEV)", 5),
        ("Plug-in Hybrid (PHEV)", 6),
        ("Elektryczny (BEV)", 7),
        # Obecność LPG wygrywa (auto z instalacją LPG = wycena jako LPG).
        ("Autogaz (LPG)", 9),
        ("Benzyna + LPG", 9),
        ("Benzyna (PB) (Konwencjonalne (ICE)) Benzyna + LPG", 9),
    ],
)
def test_resolve_engine_type_id(monkeypatch, engine_str, expected):
    """Mapowanie silnik→engine_type_id przez engines SOT + heurystyki (granica słowa)."""
    monkeypatch.setattr("core.redis_cache._get_client", lambda: None)
    assert _resolve_engine_type_id(engine_str) == expected


@pytest.mark.parametrize(
    "candidates,expected",
    [
        # LPG w dowolnym kandydacie wygrywa (Sandero Benzyna + LPG).
        (("Autogaz (LPG)", "Benzyna + LPG", "Benzyna (PB) (Konwencjonalne (ICE))"), 9),
        ((None, "Benzyna + LPG", "Benzyna (PB) (Konwencjonalne (ICE))"), 9),
        # Brak LPG → priorytet pierwszego sensownego kandydata (wynik mappera).
        (("Benzyna (PB)", None, "Benzyna (PB) (Konwencjonalne (ICE))"), 1),
        ((None, None, "Benzyna (PB) (Konwencjonalne (ICE))"), 1),
        (("Diesel (ON)", None, None), 2),
        (("Hybryda (HEV)", None, None), 5),
    ],
)
def test_resolve_engine_type_id_with_candidates(monkeypatch, candidates, expected):
    """resolve_engine_type_id: reguła LPG-wins + priorytet kandydatów (mapper → card)."""
    monkeypatch.setattr("core.redis_cache._get_client", lambda: None)
    assert resolve_engine_type_id(*candidates) == expected


def test_resolve_engine_type_id_empty_raises(monkeypatch):
    monkeypatch.setattr("core.redis_cache._get_client", lambda: None)
    with pytest.raises(ValueError):
        resolve_engine_type_id(None, "", None)
