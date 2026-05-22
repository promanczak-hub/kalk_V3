"""Regression: multi-vehicle child rows must get UNIQUE file_hash.

vehicle_synthesis.file_hash has a UNIQUE constraint. When a single document
splits into N vehicles, handle_multi_vehicles reuses the parent row for the
first twin (idx==0) and INSERTs new rows for the rest. If those inserts copy
the parent's hash verbatim, the 2nd insert violates the UNIQUE constraint
(`duplicate key value violates unique constraint
"vehicle_synthesis_file_hash_key"`), aborts the whole batch, and the
document ends up as a single error row instead of N vehicles.

This test pins that child inserts carry a unique, parent-derived hash.
"""

from __future__ import annotations


from core.extraction_pipeline import phase_1_twins


class _FakeQuery:
    """Records insert payloads; serves a canned parent row for select."""

    def __init__(self, store: dict):
        self._store = store
        self._op: str | None = None

    # select(...).eq(...).single().execute()
    def select(self, *a, **kw):
        self._op = "select"
        return self

    def eq(self, *a, **kw):
        return self

    def single(self):
        return self

    def insert(self, payload):
        self._store["inserts"].append(payload)
        self._op = "insert"
        return self

    def update(self, payload):
        self._op = "update"
        return self

    def execute(self):
        if self._op == "select":
            return type("R", (), {"data": {"file_hash": self._store["parent_hash"]}})()
        return type("R", (), {"data": None})()


class _FakeSupabase:
    def __init__(self, parent_hash: str):
        self.store = {"parent_hash": parent_hash, "inserts": []}

    def table(self, _name):
        return _FakeQuery(self.store)


def test_child_rows_get_unique_parent_derived_hash(monkeypatch) -> None:
    parent_hash = "abc123def456abc123def456abc123de"  # 32-char md5-like

    # Stub the heavy per-twin pipeline so we only exercise the row-creation loop
    monkeypatch.setattr(
        phase_1_twins, "process_single_twin", lambda *a, **kw: '{"brand": "Toyota"}'
    )
    monkeypatch.setattr(
        phase_1_twins, "finalize_vehicle_pipeline", lambda *a, **kw: None
    )
    monkeypatch.setattr(phase_1_twins, "update_progress", lambda *a, **kw: None)
    monkeypatch.setattr(phase_1_twins, "is_cancelled", lambda *a, **kw: False)

    fake = _FakeSupabase(parent_hash)
    multi_vehicles = [
        {"brand": "Toyota", "model": "Hilux MY24"},
        {"brand": "Toyota", "model": "Hilux NG26"},
        {"brand": "Toyota", "model": "Hilux Comfort"},
    ]

    phase_1_twins.handle_multi_vehicles(
        fake,  # type: ignore[arg-type]
        file_id="parent-id-0",
        file_name="fairwind.pdf",
        raw_pdf_url=None,
        router_data="markdown",
        multi_vehicles=multi_vehicles,
    )

    inserts = fake.store["inserts"]
    # idx==0 reuses parent row (no insert); idx 1,2 → 2 inserts
    assert len(inserts) == 2, f"Expected 2 child inserts, got {len(inserts)}"

    child_hashes = [ins["file_hash"] for ins in inserts]
    # All unique
    assert len(set(child_hashes)) == len(child_hashes), "Child hashes collide"
    # None equals the bare parent hash (that would re-trigger the UNIQUE clash)
    assert parent_hash not in child_hashes
    # Parent-derived + never a valid 32-char md5 (so dedup .eq(md5) never matches a child)
    for h in child_hashes:
        assert h.startswith(parent_hash + "#")
        assert len(h) != 32


def test_child_hash_null_when_parent_hash_missing(monkeypatch) -> None:
    """If the parent row has no hash, children get NULL (Postgres allows
    multiple NULLs under a UNIQUE constraint) — never a bogus string."""
    monkeypatch.setattr(
        phase_1_twins, "process_single_twin", lambda *a, **kw: '{"brand": "X"}'
    )
    monkeypatch.setattr(
        phase_1_twins, "finalize_vehicle_pipeline", lambda *a, **kw: None
    )
    monkeypatch.setattr(phase_1_twins, "update_progress", lambda *a, **kw: None)
    monkeypatch.setattr(phase_1_twins, "is_cancelled", lambda *a, **kw: False)

    fake = _FakeSupabase(None)  # type: ignore[arg-type]
    phase_1_twins.handle_multi_vehicles(
        fake,  # type: ignore[arg-type]
        file_id="p",
        file_name="f.pdf",
        raw_pdf_url=None,
        router_data=None,
        multi_vehicles=[{"brand": "A"}, {"brand": "B"}],
    )

    assert fake.store["inserts"][0]["file_hash"] is None
