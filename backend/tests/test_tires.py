"""Testy jednostkowe LTRSubCalculatorOpony.

Pokrywają:
- kolumnę DB z dropdown (Fix 4)
- capex_initial_set (Fix 3)
- walidację srednica_felgi (Fix 1)
- sezonowe / wielosezonowe warianty
- progi przebiegowe
"""

import pytest
from unittest.mock import patch, MagicMock
from core.LTRSubCalculatorOpony import LTRSubCalculatorOpony


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_CC_TYRE_CONFIG = {
    "cost_tyre_swap": "120",
    "cost_tyre_storage": "216",
    "all_season_threshold_1": "60000",
    "all_season_threshold_2": "120000",
    "all_season_threshold_3": "180000",
    "all_season_threshold_4": "240000",
    "all_season_threshold_5": "300000",
    "season_threshold_1": "120000",
    "season_threshold_2": "180000",
    "season_threshold_3": "240000",
    "season_threshold_4": "300000",
}


def _mock_supabase() -> MagicMock:
    """Zwraca mock supabase dla _fetch_tire_cost (control_center idzie przez adapter)."""
    mock = MagicMock()
    # _fetch_global_param → pusty wynik → fallback
    mock.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value.data = []
    # _fetch_tire_cost → zwraca generyczny słownik by uniknąć ValueError (brak fallbacków)
    mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {
            "budget": 1000.0,
            "medium": 1000.0,
            "premium": 1000.0,
            "wzmocnione_budget": 1000.0,
            "wzmocnione_medium": 1000.0,
            "wzmocnione_premium": 1000.0,
            "wielosezon_budget": 1000.0,
            "wielosezon_medium": 1000.0,
            "wielosezon_premium": 1000.0,
            "wielosezon_wzmocnione_budget": 1000.0,
            "wielosezon_wzmocnione_medium": 1000.0,
            "wielosezon_wzmocnione_premium": 1000.0,
        }
    ]
    return mock


def _patched_fetch_cc_row(*args, **kwargs):
    """Zastępuje fetch_control_center_row w testach — zwraca stały dict z opon-config."""
    keys = kwargs.get("keys")
    if keys is None and len(args) >= 2:
        keys = args[1]
    if keys is None:
        return dict(_CC_TYRE_CONFIG)
    return {k: _CC_TYRE_CONFIG[k] for k in keys if k in _CC_TYRE_CONFIG}


def _make_calc(
    klasa: str = "Medium",
    srednica: int = 16,
    z_oponami: bool = True,
) -> LTRSubCalculatorOpony:
    """Tworzy kalkulator z zamockowanym Supabase."""
    with patch("core.LTRSubCalculatorOpony.get_fresh_client", return_value=_mock_supabase()), \
         patch("core.control_center.fetch_control_center_row", side_effect=_patched_fetch_cc_row):
        calc = LTRSubCalculatorOpony(
            z_oponami=z_oponami,
            klasa_opony_string=klasa,
            srednica_felgi=srednica,
            odkup_opon_enabled=False,
        )
    return calc


# ---------------------------------------------------------------------------
# Fix 4: Mapowanie klasy opon → kolumna DB
# ---------------------------------------------------------------------------


class TestTireColumnMapping:
    """Klasa opon z dropdown → kolumna w tabeli koszty_opon."""

    @pytest.mark.parametrize(
        "dropdown_value,expected_column",
        [
            ("Budget", "budget"),
            ("Medium", "medium"),
            ("Premium", "premium"),
            ("Wzmocnione Budget", "wzmocnione_budget"),
            ("Wzmocnione Medium", "wzmocnione_medium"),
            ("Wzmocnione Premium", "wzmocnione_premium"),
            ("Wielosezon Budget", "wielosezon_budget"),
            ("Wielosezon Medium", "wielosezon_medium"),
            ("Wielosezon Premium", "wielosezon_premium"),
            ("Wielosezon Wzmocnione Budget", "wielosezon_wzmocnione_budget"),
            ("Wielosezon Wzmocnione Medium", "wielosezon_wzmocnione_medium"),
            ("Wielosezon Wzmocnione Premium", "wielosezon_wzmocnione_premium"),
        ],
    )
    def test_column_mapping(self, dropdown_value: str, expected_column: str) -> None:
        calc = _make_calc(klasa=dropdown_value)
        assert calc._get_tire_column_name() == expected_column

    def test_all_season_flag_from_wielosezon(self) -> None:
        calc = _make_calc(klasa="Wielosezon Medium")
        assert calc.all_season is True

    def test_no_all_season_for_regular(self) -> None:
        calc = _make_calc(klasa="Premium")
        assert calc.all_season is False

    def test_empty_string_defaults_to_medium(self) -> None:
        calc = _make_calc(klasa="")
        assert calc._get_tire_column_name() == "medium"

    def test_whitespace_stripped(self) -> None:
        calc = _make_calc(klasa="  Budget  ")
        assert calc._get_tire_column_name() == "budget"


# ---------------------------------------------------------------------------
# Fix 3: capex_initial_set
# ---------------------------------------------------------------------------


class TestCapexInitialSet:
    """Pierwszy komplet opon → CAPEX, reszta → OponyNetto."""

    def test_capex_returned_in_result(self) -> None:
        calc = _make_calc(klasa="Medium", srednica=16)
        calc.swap_cost = 120.0
        calc.storage_cost_per_year = 216.0

        result = calc.calculate_cost(months=36, total_km=90000)

        assert "capex_initial_set" in result
        assert result["capex_initial_set"] == 1000.0

    def test_opony_netto_excludes_first_set(self) -> None:
        calc = _make_calc(klasa="Medium", srednica=16)
        calc.tire_set_price = 1000.0
        calc.swap_cost = 120.0
        calc.storage_cost_per_year = 216.0

        result = calc.calculate_cost(months=36, total_km=90000)

        # total_km=90_000 < 120_000 → 1 set → hw_cost = tire_set_price
        # base hw = 1000
        # remaining_hw_cost = 1000
        # swaps = 120 * 3 * 2 = 720
        # storage = 216 * 3 * 2 = 1296
        # OponyNetto = 1000 + 720 + 1296 = 3016
        assert result["OponyNetto"] == 3016.0
        assert result["capex_initial_set"] == 1000.0

    def test_capex_zero_when_z_oponami_false(self) -> None:
        calc = _make_calc(klasa="Medium", srednica=16, z_oponami=False)
        result = calc.calculate_cost(months=36, total_km=90000)

        assert result["capex_initial_set"] == 0.0
        assert result["OponyNetto"] == 0.0


# ---------------------------------------------------------------------------
# Fix 1: Walidacja srednica_felgi
# ---------------------------------------------------------------------------


class TestSrednicaValidation:
    """srednica_felgi jest wymagana gdy z_oponami=True."""

    def test_raises_when_srednica_zero_and_z_oponami(self) -> None:
        with pytest.raises(ValueError, match="srednica_felgi"):
            with patch("core.LTRSubCalculatorOpony.get_fresh_client", return_value=_mock_supabase()), \
         patch("core.control_center.fetch_control_center_row", side_effect=_patched_fetch_cc_row):
                LTRSubCalculatorOpony(
                    z_oponami=True,
                    klasa_opony_string="Medium",
                    srednica_felgi=0,
                )

    def test_no_error_when_z_oponami_false(self) -> None:
        with patch("core.LTRSubCalculatorOpony.get_fresh_client", return_value=_mock_supabase()), \
         patch("core.control_center.fetch_control_center_row", side_effect=_patched_fetch_cc_row):
            calc = LTRSubCalculatorOpony(
                z_oponami=False,
                klasa_opony_string="Medium",
                srednica_felgi=0,
            )
        result = calc.calculate_cost(months=36, total_km=90000)
        assert result["OponyNetto"] == 0.0


# ---------------------------------------------------------------------------
# Kalkulacje: sezonowe vs wielosezonowe
# ---------------------------------------------------------------------------


class TestSeasonalCalculation:
    """Opony sezonowe (nie wielosezon)."""

    def test_basic_seasonal_36m_90k(self) -> None:
        calc = _make_calc(klasa="Budget", srednica=16)
        calc.swap_cost = 120.0
        calc.storage_cost_per_year = 216.0
        calc.tire_set_price = 1000.0

        result = calc.calculate_cost(months=36, total_km=90000)

        # HW: 1 set (90k < 120k) = 1000
        # capex_initial = 1000 → remaining HW = 1000
        # swaps: 120 * 3 * 2 = 720
        # storage: 216 * 3 * 2 = 1296
        # Total OponyNetto = 1000 + 720 + 1296 = 3016
        assert result["capex_initial_set"] == 1000.0
        assert result["OponyNetto"] == 3016.0
        assert result["IloscOpon"] == 1.0


class TestAllSeasonCalculation:
    """Opony wielosezonowe."""

    def test_basic_allseason_48m_100k(self) -> None:
        calc = _make_calc(klasa="Wielosezon Premium", srednica=17)
        calc.swap_cost = 120.0
        calc.storage_cost_per_year = 216.0
        calc.tire_set_price_base = 2000.0

        result = calc.calculate_cost(months=48, total_km=100000)

        # HW proportional: 2000 + ((100k-60k)/60k)*2000 = 2000 + 1333.33 = 3333.33
        # capex_initial_set = 2000
        # remaining_hw_cost = 3333.33
        # swaps: ceil(100k/60k)=2 → 2*120 = 240
        # storage: 0 (wielosezon)
        # OponyNetto = 3333.33 + 240 = 3573.33
        assert result["capex_initial_set"] == 1000.0
        assert round(result["OponyNetto"], 2) == 3573.33
        assert result["IloscOpon"] == 2.0

    def test_allseason_storage_is_zero(self) -> None:
        calc = _make_calc(klasa="Wielosezon Medium", srednica=16)
        calc.tire_set_price_base = 1000.0
        calc.swap_cost = 100.0
        calc.storage_cost_per_year = 999.0  # should be ignored

        result = calc.calculate_cost(months=24, total_km=50000)

        assert result["monthly_storage"] == 0.0


# ---------------------------------------------------------------------------
# Progi przebiegowe
# ---------------------------------------------------------------------------


class TestMileageThresholds:
    """Progi przebiegowe dla liczby kompletów."""

    def test_exactly_60k_allseason(self) -> None:
        calc = _make_calc(klasa="Wielosezon Budget", srednica=16)
        calc.tire_set_price = 1000.0
        calc.swap_cost = 100.0
        calc.storage_cost_per_year = 0.0

        result = calc.calculate_cost(months=24, total_km=60000)

        # 60k <= threshold_1 → 1 set
        # HW = 1000 (base, no extra)
        # capex_initial = 1000
        # remaining HW = 1000
        # swaps: ceil(60k/60k)=1 → 100
        # Netto = 1000 + 100 = 1100
        assert result["IloscOpon"] == 1.0
        assert result["capex_initial_set"] == 1000.0
        assert result["OponyNetto"] == 1100.0

    def test_exactly_120k_allseason(self) -> None:
        calc = _make_calc(klasa="Wielosezon Budget", srednica=16)
        calc.tire_set_price = 1000.0
        calc.swap_cost = 100.0
        calc.storage_cost_per_year = 0.0

        result = calc.calculate_cost(months=48, total_km=120000)

        # 120k <= threshold_2 → 2 sets
        # HW = 1000 + ((120k-60k)/60k)*1000 = 2000
        # capex = 1000
        # remaining_hw_cost = 2000
        # swaps: ceil(120k/60k)=2 → 200
        # OponyNetto = 2000 + 200 = 2200
        assert result["IloscOpon"] == 2.0
        assert result["capex_initial_set"] == 1000.0
        assert result["OponyNetto"] == 2200.0
