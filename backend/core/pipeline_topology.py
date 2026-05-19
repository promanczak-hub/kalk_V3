"""
Statyczny manifest topologii pipeline'u kalk_v3.

Zawiera elementy które są niewykrywalne przez introspection FastAPI/Celery:
- 12 sub-kalkulatorów LTR (z polskimi nazwami i kolejnością)
- Fazy ekstrakcji PDF (router → multi-vehicle → twins → mapping)
- Tabele DB jako węzły terminalne
- Edges (kto kogo woła) między stagami, fazami, endpointami i tabelami DB

Używany przez `backend/api/introspection_routes.py` do złożenia
pełnej topology JSON serwowanej do frontendu.
"""

from __future__ import annotations

from typing import Any, Dict, List


# ─── 12 stagów LTR (Source: PipelineDebugger.V1_SECTION_NAMES) ────────────
LTR_STAGES: List[Dict[str, Any]] = [
    {
        "id": "stage:ltr:1",
        "order": 1,
        "label": "Opony",
        "file": "backend/core/LTRSubCalculatorOpony.py",
        "db_tables": ["tire_costs"],
        "depends_on": [],
    },
    {
        "id": "stage:ltr:2",
        "order": 2,
        "label": "Koszty Dodatkowe",
        "file": "backend/core/LTRSubCalculatorKosztyDodatkowe.py",
        "db_tables": ["control_center"],
        "depends_on": [],
    },
    {
        "id": "stage:ltr:3",
        "order": 3,
        "label": "Samochód Zastępczy",
        "file": "backend/core/LTRSubCalculatorSamochodZastepczy.py",
        "db_tables": ["insurance_samochody_zastepcze_kategorie"],
        "depends_on": [],
    },
    {
        "id": "stage:ltr:4",
        "order": 4,
        "label": "Serwis",
        "file": "backend/core/LTRSubCalculatorSerwisNew.py",
        "db_tables": ["samar_class_serwis", "control_center"],
        "depends_on": [],
    },
    {
        "id": "stage:ltr:5",
        "order": 5,
        "label": "Cena Zakupu (CAPEX)",
        "file": "backend/core/LTRSubCalculatorCenaZakupu.py",
        "db_tables": [],
        "depends_on": ["stage:ltr:1"],
    },
    {
        "id": "stage:ltr:6",
        "order": 6,
        "label": "Utrata Wartości",
        "file": "backend/core/LTRSubCalculatorUtrataWartosciNew.py",
        "db_tables": ["body_types", "samar_rv"],
        "depends_on": ["stage:ltr:5"],
    },
    {
        "id": "stage:ltr:7",
        "order": 7,
        "label": "Amortyzacja",
        "file": "backend/core/LTRSubCalculatorAmortyzacja.py",
        "db_tables": [],
        "depends_on": ["stage:ltr:5", "stage:ltr:6"],
    },
    {
        "id": "stage:ltr:8",
        "order": 8,
        "label": "Ubezpieczenie",
        "file": "backend/core/LTRSubCalculatorUbezpieczenie.py",
        "db_tables": ["insurance_rates"],
        "depends_on": ["stage:ltr:5", "stage:ltr:7"],
    },
    {
        "id": "stage:ltr:9",
        "order": 9,
        "label": "Finanse",
        "file": "backend/core/LTRSubCalculatorFinanse.py",
        "db_tables": ["control_center"],
        "depends_on": ["stage:ltr:5", "stage:ltr:6"],
    },
    {
        "id": "stage:ltr:10",
        "order": 10,
        "label": "Koszt Dzienny",
        "file": "backend/core/LTRSubCalculatorKosztDzienny.py",
        "db_tables": [],
        "depends_on": [
            "stage:ltr:1", "stage:ltr:2", "stage:ltr:3", "stage:ltr:4",
            "stage:ltr:7", "stage:ltr:8", "stage:ltr:9",
        ],
    },
    {
        "id": "stage:ltr:11",
        "order": 11,
        "label": "Stawka (Marża)",
        "file": "backend/core/LTRSubCalculatorStawka.py",
        "db_tables": ["control_center"],
        "depends_on": ["stage:ltr:10"],
    },
    {
        "id": "stage:ltr:12",
        "order": 12,
        "label": "Budżet Marketingowy",
        "file": "backend/core/LTRSubCalculatorBudzetMarketingowy.py",
        "db_tables": ["control_center"],
        "depends_on": ["stage:ltr:6"],
    },
]


# ─── Fazy ekstrakcji PDF ───────────────────────────────────────────────────
EXTRACTION_PHASES: List[Dict[str, Any]] = [
    {
        "id": "phase:0:router",
        "label": "Phase 0 — Router (klasyfikacja PDF)",
        "file": "backend/core/extraction_pipeline/phase_0_router.py",
        "description": "Gemini Pro klasyfikuje typ dokumentu z pymupdf4llm markdown",
        "depends_on": [],
    },
    {
        "id": "phase:0:multi_vehicle",
        "label": "Phase 0 — Multi-Vehicle Detection",
        "file": "backend/core/pipeline_multi_vehicle.py",
        "description": "Wykrywa czy PDF zawiera 1 czy N pojazdów i splituje payload",
        "depends_on": ["phase:0:router"],
    },
    {
        "id": "phase:1:twins",
        "label": "Phase 1 — Digital Twins (extract + summary)",
        "file": "backend/core/extraction_pipeline/phase_1_twins.py",
        "description": "Gemini Pro extract → Gemini Flash card summary → V3 enrichment → price validator",
        "depends_on": ["phase:0:multi_vehicle"],
    },
    {
        "id": "phase:2:mapping",
        "label": "Phase 2 — Mapping & Finalize",
        "file": "backend/core/extraction_pipeline/phase_2_mapping.py",
        "description": "Composite body style, AI mapper, SAMAR/engine class, ranking, enrichment",
        "depends_on": ["phase:1:twins"],
    },
]


# ─── Tabele DB jako węzły terminalne ──────────────────────────────────────
DB_TABLES: List[Dict[str, Any]] = [
    {"id": "db:vehicle_synthesis", "label": "vehicle_synthesis"},
    {"id": "db:ltr_kalkulacje", "label": "ltr_kalkulacje"},
    {"id": "db:vehicle_matrix_cache", "label": "vehicle_matrix_cache"},
    {"id": "db:body_types", "label": "body_types"},
    {"id": "db:samar_rv", "label": "samar_rv"},
    {"id": "db:samar_class_serwis", "label": "samar_class_serwis"},
    {"id": "db:insurance_rates", "label": "insurance_rates"},
    {"id": "db:insurance_samochody_zastepcze_kategorie", "label": "insurance_samochody_zastepcze_kategorie"},
    {"id": "db:tire_costs", "label": "tire_costs"},
    {"id": "db:control_center", "label": "control_center"},
    {"id": "db:extraction_corrections", "label": "extraction_corrections"},
]


# ─── Edges ręcznie zdefiniowane (cross-layer) ─────────────────────────────
# Większość edges (route→task, stage→stage) generujemy programatycznie
# z LTR_STAGES.depends_on i z manifestów. Tutaj trzymamy tylko edges
# pomiędzy fazami ekstrakcji i route'ami które je wywołują,
# oraz koncową WRITE do DB.
STATIC_EDGES: List[Dict[str, str]] = [
    # PDF upload → Celery task → Phase 0
    {"source": "route:POST:/api/extract/async", "target": "task:process_document_task_from_storage", "kind": "celery"},
    {"source": "task:process_document_task_from_storage", "target": "phase:0:router", "kind": "calls"},
    # Phase 2 → DB write
    {"source": "phase:2:mapping", "target": "db:vehicle_synthesis", "kind": "writes_db"},
    # 12 stagów → DB writes
    {"source": "stage:ltr:11", "target": "db:ltr_kalkulacje", "kind": "writes_db"},
    # Matrix cache job → DB
    {"source": "task:matrix_watchdog_task", "target": "db:vehicle_matrix_cache", "kind": "writes_db"},
    # Endpoint debug-pipeline odpala wszystkie 12 stagów
    {"source": "route:POST:/api/kalkulacje/debug-pipeline/{vehicle_id}", "target": "stage:ltr:1", "kind": "calls"},
    # Endpoint kalkulacje (calculate-matrix) odpala stage 1 (wszystkie po depends_on)
    {"source": "route:POST:/api/kalkulacje", "target": "stage:ltr:1", "kind": "calls"},
    {"source": "route:POST:/api/calculate-matrix", "target": "stage:ltr:1", "kind": "calls"},
]


def build_stage_nodes() -> List[Dict[str, Any]]:
    """Zwraca 12 stagów LTR jako node'y dla topology JSON."""
    return [
        {
            "id": s["id"],
            "kind": "stage",
            "category": "ltr",
            "order": s["order"],
            "label": s["label"],
            "file": s["file"],
            "db_tables": s["db_tables"],
            "depends_on": s["depends_on"],
        }
        for s in LTR_STAGES
    ]


def build_phase_nodes() -> List[Dict[str, Any]]:
    """Zwraca fazy ekstrakcji jako node'y."""
    return [
        {
            "id": p["id"],
            "kind": "phase",
            "category": "extraction",
            "label": p["label"],
            "file": p["file"],
            "description": p["description"],
            "depends_on": p["depends_on"],
        }
        for p in EXTRACTION_PHASES
    ]


def build_db_nodes() -> List[Dict[str, Any]]:
    """Zwraca tabele DB jako node'y terminalne."""
    return [
        {
            "id": t["id"],
            "kind": "db",
            "category": "db",
            "label": t["label"],
        }
        for t in DB_TABLES
    ]


def build_stage_edges() -> List[Dict[str, str]]:
    """Generuje edges między stagami z LTR_STAGES.depends_on + writes_db."""
    edges: List[Dict[str, str]] = []
    for stage in LTR_STAGES:
        for parent_id in stage["depends_on"]:
            edges.append({"source": parent_id, "target": stage["id"], "kind": "sequence"})
        for table in stage["db_tables"]:
            edges.append({"source": f"db:{table}", "target": stage["id"], "kind": "reads_db"})
    return edges


def build_phase_edges() -> List[Dict[str, str]]:
    """Generuje edges między fazami ekstrakcji z depends_on."""
    edges: List[Dict[str, str]] = []
    for phase in EXTRACTION_PHASES:
        for parent_id in phase["depends_on"]:
            edges.append({"source": parent_id, "target": phase["id"], "kind": "sequence"})
    return edges
