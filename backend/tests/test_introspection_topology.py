"""
Testy topologii pipeline'u — manifest stagów LTR, faz ekstrakcji, endpoint /api/_introspect/topology.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient


# ─── Manifest unit tests (bez FastAPI) ──────────────────────────────────────


class TestPipelineTopologyManifest:
    def test_twelve_ltr_stages_with_consecutive_orders(self) -> None:
        from core.pipeline_topology import build_stage_nodes

        nodes = build_stage_nodes()
        assert len(nodes) == 12
        orders = sorted(n["order"] for n in nodes)
        assert orders == list(range(1, 13))

    def test_each_stage_has_label_and_file(self) -> None:
        from core.pipeline_topology import build_stage_nodes

        for node in build_stage_nodes():
            assert node["label"], f"stage {node['id']} missing label"
            assert node["file"].startswith("backend/core/LTRSubCalculator"), (
                f"stage {node['id']} file path nie wskazuje na LTRSubCalculator: {node['file']}"
            )

    def test_polish_labels_match_v1_section_names(self) -> None:
        """Sanity check: labels po polsku zgodne z PipelineDebugger.V1_SECTION_NAMES."""
        from core.pipeline_topology import LTR_STAGES

        labels = {s["order"]: s["label"] for s in LTR_STAGES}
        assert labels[1] == "Opony"
        assert labels[2] == "Koszty Dodatkowe"
        assert labels[6] == "Utrata Wartości"
        assert labels[11] == "Stawka (Marża)"
        assert labels[12] == "Budżet Marketingowy"

    def test_extraction_phases_present(self) -> None:
        from core.pipeline_topology import build_phase_nodes

        phases = build_phase_nodes()
        assert len(phases) >= 3
        ids = {p["id"] for p in phases}
        assert "phase:0:router" in ids
        assert "phase:1:twins" in ids
        assert "phase:2:mapping" in ids

    def test_stage_edges_respect_depends_on(self) -> None:
        from core.pipeline_topology import build_stage_edges

        edges = build_stage_edges()
        sequence_edges = [e for e in edges if e["kind"] == "sequence"]
        # stage:ltr:6 depends_on stage:ltr:5
        assert {"source": "stage:ltr:5", "target": "stage:ltr:6", "kind": "sequence"} in sequence_edges
        # stage:ltr:7 depends_on stage:ltr:5 i stage:ltr:6
        assert {"source": "stage:ltr:6", "target": "stage:ltr:7", "kind": "sequence"} in sequence_edges


# ─── Integration tests (TestClient) ─────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Buduje FastAPI app z głównego main.py i zwraca TestClient."""
    # Import wewnątrz fixture, bo import main.py jest ciężki (inicjalizuje Sentry, supabase, etc.)
    from main import app

    return TestClient(app)


@pytest.fixture(scope="module")
def topology(client: TestClient) -> Dict[str, Any]:
    """Pobiera topologię raz na module."""
    response = client.get("/api/_introspect/topology")
    assert response.status_code == 200, response.text
    return response.json()


class TestIntrospectionEndpoint:
    def test_returns_version_and_counts(self, topology: Dict[str, Any]) -> None:
        assert topology["version"] == "1.0"
        assert "generated_at" in topology
        assert "counts" in topology

    def test_includes_minimum_routes(self, topology: Dict[str, Any]) -> None:
        route_nodes = [n for n in topology["nodes"] if n["kind"] == "route"]
        # 18 routerów × średnio ~4 endpointy = ~70+. Próg minimum 50 daje bufor.
        assert len(route_nodes) >= 50, f"Got only {len(route_nodes)} routes"

    def test_includes_all_12_ltr_stages(self, topology: Dict[str, Any]) -> None:
        stage_nodes = [n for n in topology["nodes"] if n["kind"] == "stage"]
        assert len(stage_nodes) == 12
        orders = sorted(n["order"] for n in stage_nodes)
        assert orders == list(range(1, 13))

    def test_includes_known_celery_tasks(self, topology: Dict[str, Any]) -> None:
        task_ids = {n["id"] for n in topology["nodes"] if n["kind"] == "task"}
        # Te dwa są krytyczne dla pipeline'u ekstrakcji PDF
        assert "task:process_document_task_from_storage" in task_ids
        assert "task:process_document_task" in task_ids

    def test_includes_kalkulacje_debug_pipeline_route(self, topology: Dict[str, Any]) -> None:
        paths = {
            n["path"] for n in topology["nodes"]
            if n["kind"] == "route" and n["method"] == "POST"
        }
        assert "/api/kalkulacje/debug-pipeline/{vehicle_id}" in paths

    def test_no_duplicate_node_ids(self, topology: Dict[str, Any]) -> None:
        ids = [n["id"] for n in topology["nodes"]]
        assert len(ids) == len(set(ids)), "Duplicate node ids in topology"

    def test_all_edges_have_valid_endpoints(self, topology: Dict[str, Any]) -> None:
        node_ids = {n["id"] for n in topology["nodes"]}
        invalid: List[Dict[str, str]] = []
        for edge in topology["edges"]:
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                invalid.append(edge)
        # Niektóre edges static mogą wskazywać na endpoint który nie istnieje w app.routes
        # (np. jeśli ktoś przemianował path). Akceptujemy do 5% rozjazdu jako warning,
        # ale powyżej tego fail — manifest się rozjechał z kodem.
        max_allowed = max(2, len(topology["edges"]) // 20)
        assert len(invalid) <= max_allowed, (
            f"Edges referencing missing nodes ({len(invalid)}/{len(topology['edges'])}): "
            f"{invalid[:5]}"
        )

    def test_routes_have_tag_and_file(self, topology: Dict[str, Any]) -> None:
        for node in topology["nodes"]:
            if node["kind"] != "route":
                continue
            assert "tag" in node and node["tag"], f"Route {node['id']} missing tag"
            assert "file" in node and node["file"], f"Route {node['id']} missing file"
