"""
Endpoint introspekcji: zwraca topologię systemu kalk_v3 jako pojedynczy JSON.

Łączy:
- Auto-discover endpointów FastAPI z `app.routes`
- Auto-discover Celery tasków z `celery_app.tasks`
- Statyczny manifest z `core/pipeline_topology` dla 12 stagów LTR,
  faz ekstrakcji i tabel DB.

Używany przez frontend `PipelineMap/PipelineMapPage.tsx` do renderingu
interaktywnego grafu (reactflow + dagre).
"""

from __future__ import annotations

import inspect
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.routing import APIRoute

from core.celery_app import celery_app
from core.pipeline_topology import (
    STATIC_EDGES,
    build_db_nodes,
    build_phase_edges,
    build_phase_nodes,
    build_stage_edges,
    build_stage_nodes,
)


router = APIRouter(tags=["Introspection"])


# ─── Helpers ────────────────────────────────────────────────────────────────

def _repo_relative_file(endpoint: Any) -> str:
    """
    Zwraca ścieżkę pliku endpointu relatywną do repo (backend/...).
    Fallback: __module__ jeśli inspect.getfile zawiedzie.
    """
    try:
        abs_path = inspect.getfile(endpoint)
        norm = abs_path.replace("\\", "/")
        if "/backend/" in norm:
            return "backend/" + norm.split("/backend/", 1)[1]
        return os.path.basename(norm)
    except (TypeError, OSError):
        module = getattr(endpoint, "__module__", "unknown")
        return module.replace(".", "/") + ".py"


def _route_doc(endpoint: Any) -> str:
    """Pierwsza linia docstringa endpointa jako description."""
    doc = inspect.getdoc(endpoint) or ""
    return doc.splitlines()[0].strip() if doc else ""


def _route_tag(route: APIRoute) -> str:
    """Pierwszy tag routera (lub 'untagged')."""
    if route.tags:
        return str(route.tags[0])
    return "untagged"


def _route_node_id(method: str, path: str) -> str:
    return f"route:{method}:{path}"


def _task_node_id(name: str) -> str:
    return f"task:{name}"


# ─── Route discovery ────────────────────────────────────────────────────────

def discover_route_nodes(request: Request) -> List[Dict[str, Any]]:
    """
    Iteruje `app.routes` i buduje listę node'ów typu 'route'.
    Pomija health/system endpointy bez tagów.
    """
    app = request.app
    nodes: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            node_id = _route_node_id(method, route.path)
            if node_id in seen:
                continue
            seen.add(node_id)
            nodes.append({
                "id": node_id,
                "kind": "route",
                "method": method,
                "path": route.path,
                "tag": _route_tag(route),
                "file": _repo_relative_file(route.endpoint),
                "description": _route_doc(route.endpoint),
                "label": f"{method} {route.path}",
            })
    return nodes


# ─── Task discovery ─────────────────────────────────────────────────────────

def discover_task_nodes() -> List[Dict[str, Any]]:
    """
    Iteruje `celery_app.tasks` i buduje listę node'ów typu 'task'.
    Pomija wewnętrzne taski Celery (`celery.*`).
    """
    nodes: List[Dict[str, Any]] = []
    routes_cfg: Dict[str, Dict[str, str]] = celery_app.conf.task_routes or {}

    for name, task in sorted(celery_app.tasks.items()):
        if name.startswith("celery."):
            continue
        queue = routes_cfg.get(name, {}).get("queue", "default")
        # Spróbuj odczytać file z task.run; fallback do task.__module__
        try:
            file_path = _repo_relative_file(task.run)
        except Exception:
            module = getattr(task, "__module__", "unknown")
            file_path = module.replace(".", "/") + ".py"
        nodes.append({
            "id": _task_node_id(name),
            "kind": "task",
            "label": name,
            "queue": queue,
            "file": file_path,
            "description": _route_doc(task.run) if hasattr(task, "run") else "",
        })
    return nodes


# ─── Endpoint ───────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _cached_static_payload() -> Dict[str, Any]:
    """Cache statycznych części topology — odświeżane raz na proces."""
    return {
        "stages": build_stage_nodes(),
        "phases": build_phase_nodes(),
        "db": build_db_nodes(),
        "stage_edges": build_stage_edges(),
        "phase_edges": build_phase_edges(),
    }


@router.get("/_introspect/topology")
async def get_topology(request: Request) -> Dict[str, Any]:
    """
    Zwraca pełną topologię systemu:
    - nodes: routes + tasks + stages + phases + db
    - edges: stage sequences + phase sequences + cross-layer (calls, writes_db, celery)
    """
    static = _cached_static_payload()
    route_nodes = discover_route_nodes(request)
    task_nodes = discover_task_nodes()

    all_nodes: List[Dict[str, Any]] = (
        route_nodes
        + task_nodes
        + static["stages"]
        + static["phases"]
        + static["db"]
    )
    all_edges: List[Dict[str, str]] = (
        static["stage_edges"]
        + static["phase_edges"]
        + list(STATIC_EDGES)
    )

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": all_nodes,
        "edges": all_edges,
        "counts": {
            "routes": len(route_nodes),
            "tasks": len(task_nodes),
            "stages": len(static["stages"]),
            "phases": len(static["phases"]),
            "db": len(static["db"]),
            "edges": len(all_edges),
        },
    }
