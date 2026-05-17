"""Tests for the comparison-chart snapshot helpers in scoring_search_routes.

Exercises the pure builders that map vehicle_matrix_cache rows to
VehicleSnapshot — happy path, missing-row, snap-to-nearest, null decomposition
and the include_curve branch. Endpoint wiring is not tested here because it
hits Supabase; integration coverage belongs in an e2e suite.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make 'core' / 'api' imports resolvable when pytest is invoked from repo root.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from api.scoring_search_routes import (  # noqa: E402
    _build_snapshot_for_vehicle,
    _pick_latest_per_duration,
    _row_to_curve_point,
    _row_to_snapshot,
)


def _row(
    *,
    duration_months: int = 36,
    annual_mileage: int = 30000,
    base_price_net: float = 200000.0,
    monthly_price_net: float = 3500.0,
    utrata: float | None = 80000.0,
    serwis: float | None = 12000.0,
    opony: float | None = 6000.0,
    ubezp: float | None = 18000.0,
    wr_pct: float | None = 40.0,
    calculated_at: str = "2026-05-16T12:00:00+00:00",
) -> dict:
    return {
        "vehicle_id": "v1",
        "duration_months": duration_months,
        "annual_mileage": annual_mileage,
        "base_price_net": base_price_net,
        "monthly_price_net": monthly_price_net,
        "utrata_wartosci_pln": utrata,
        "koszty_serwisowe_pln": serwis,
        "koszt_opon_pln": opony,
        "ubezpieczenie_pln": ubezp,
        "wr_pct": wr_pct,
        "calculated_at": calculated_at,
    }


class TestRowToSnapshot:
    def test_happy_path_per_month_division(self):
        snap = _row_to_snapshot(_row(), vehicle_id="v1")
        assert snap.found is True
        assert snap.error is None
        assert snap.duration_months == 36
        assert snap.monthly_total == 3500.0
        assert snap.wr_pct == 40.0
        assert snap.wr_pln == 80000.0
        # 80000 / 36 = 2222.22
        assert snap.monthly_amortization == 2222.22
        assert snap.monthly_service == 333.33  # 12000/36
        assert snap.monthly_tires == 166.67  # 6000/36
        assert snap.monthly_insurance == 500.0  # 18000/36

    def test_null_decomposition_keeps_total(self):
        row = _row(utrata=None, serwis=None, opony=None, ubezp=None, wr_pct=None)
        snap = _row_to_snapshot(row, vehicle_id="v1")
        assert snap.found is True
        assert snap.error == "null_decomposition"
        assert snap.monthly_total == 3500.0
        assert snap.monthly_amortization is None
        assert snap.wr_pct is None

    def test_partial_decomposition_still_treated_as_present(self):
        row = _row(utrata=72000.0, serwis=None, opony=None, ubezp=None, wr_pct=36.0)
        snap = _row_to_snapshot(row, vehicle_id="v1")
        assert snap.error is None
        assert snap.monthly_amortization == 2000.0
        assert snap.monthly_service is None

    def test_explicit_error_overrides_null_decomposition(self):
        row = _row(utrata=None, serwis=None, opony=None, ubezp=None, wr_pct=None)
        snap = _row_to_snapshot(row, vehicle_id="v1", error="snap_to_nearest")
        assert snap.error == "snap_to_nearest"


class TestPickLatestPerDuration:
    def test_keeps_newest_calculated_at(self):
        old = _row(duration_months=36, calculated_at="2026-01-01T00:00:00+00:00", monthly_price_net=4000.0)
        new = _row(duration_months=36, calculated_at="2026-05-16T00:00:00+00:00", monthly_price_net=3500.0)
        picked = _pick_latest_per_duration([old, new])
        assert picked[36]["monthly_price_net"] == 3500.0

    def test_returns_one_row_per_duration(self):
        rows = [
            _row(duration_months=24),
            _row(duration_months=36),
            _row(duration_months=48),
            _row(duration_months=36, calculated_at="2025-01-01T00:00:00+00:00"),
        ]
        picked = _pick_latest_per_duration(rows)
        assert set(picked.keys()) == {24, 36, 48}


class TestBuildSnapshotForVehicle:
    def test_not_in_cache(self):
        snap = _build_snapshot_for_vehicle([], vehicle_id="v1", target_months=36, include_curve=False)
        assert snap.found is False
        assert snap.error == "not_in_cache"
        assert snap.monthly_total is None

    def test_exact_match(self):
        rows = [_row(duration_months=36)]
        snap = _build_snapshot_for_vehicle(rows, vehicle_id="v1", target_months=36, include_curve=False)
        assert snap.found is True
        assert snap.error is None
        assert snap.duration_months == 36

    def test_snap_to_nearest_when_target_missing(self):
        rows = [_row(duration_months=24, monthly_price_net=4200.0), _row(duration_months=48, monthly_price_net=2900.0)]
        snap = _build_snapshot_for_vehicle(rows, vehicle_id="v1", target_months=36, include_curve=False)
        assert snap.found is True
        assert snap.error == "snap_to_nearest"
        # 36 is equidistant from 24 and 48 → min() picks 24 (first in sorted)
        assert snap.duration_months in (24, 48)

    def test_include_curve_returns_sorted_points(self):
        rows = [
            _row(duration_months=48, wr_pct=55.0, monthly_price_net=2800.0),
            _row(duration_months=24, wr_pct=28.0, monthly_price_net=4500.0),
            _row(duration_months=36, wr_pct=40.0, monthly_price_net=3500.0),
            _row(duration_months=60, wr_pct=68.0, monthly_price_net=2400.0),
        ]
        snap = _build_snapshot_for_vehicle(rows, vehicle_id="v1", target_months=36, include_curve=True)
        assert snap.wr_curve is not None
        durations = [p.duration_months for p in snap.wr_curve]
        assert durations == sorted(durations) == [24, 36, 48, 60]
        wr_values = [p.wr_pct for p in snap.wr_curve]
        assert wr_values == [28.0, 40.0, 55.0, 68.0]


class TestRowToCurvePoint:
    def test_maps_all_fields(self):
        point = _row_to_curve_point(_row(duration_months=48, wr_pct=55.0, utrata=110000.0, monthly_price_net=2800.0))
        assert point.duration_months == 48
        assert point.wr_pct == 55.0
        assert point.wr_pln == 110000.0
        assert point.monthly_total == 2800.0

    def test_handles_null_breakdown(self):
        point = _row_to_curve_point(_row(duration_months=48, wr_pct=None, utrata=None, monthly_price_net=2800.0))
        assert point.duration_months == 48
        assert point.wr_pct is None
        assert point.wr_pln is None
        assert point.monthly_total == 2800.0
