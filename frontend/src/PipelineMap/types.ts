/**
 * Typy dla mapy pipeline'u — zgodne ze schematem zwracanym przez
 * backend endpoint GET /api/_introspect/topology.
 */

export type NodeKind = "route" | "task" | "stage" | "phase" | "db";

export type EdgeKind =
  | "sequence" // stage→stage, phase→phase
  | "calls" // route→stage, route→phase, task→phase
  | "celery" // route→task
  | "reads_db" // db→stage
  | "writes_db"; // stage/phase→db

export interface BaseNode {
  id: string;
  kind: NodeKind;
  label: string;
  file?: string;
  description?: string;
}

export interface RouteNode extends BaseNode {
  kind: "route";
  method: string;
  path: string;
  tag: string;
}

export interface TaskNode extends BaseNode {
  kind: "task";
  queue: string;
}

export interface StageNode extends BaseNode {
  kind: "stage";
  category: "ltr";
  order: number;
  db_tables: string[];
  depends_on: string[];
}

export interface PhaseNode extends BaseNode {
  kind: "phase";
  category: "extraction";
  depends_on: string[];
}

export interface DbNode extends BaseNode {
  kind: "db";
  category: "db";
}

export type TopologyNode = RouteNode | TaskNode | StageNode | PhaseNode | DbNode;

export interface TopologyEdge {
  source: string;
  target: string;
  kind: EdgeKind;
}

export interface TopologyResponse {
  version: string;
  generated_at: string;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  counts: {
    routes: number;
    tasks: number;
    stages: number;
    phases: number;
    db: number;
    edges: number;
  };
}

/**
 * Tryb podświetlenia węzła:
 * - "highlighted" — aktywny w danej kalkulacji
 * - "disabled" — wyłączony przez toggle (np. include_servicing=false)
 * - "variant-nonASO" — alternatywny tryb (np. serwis nonASO)
 * - "dim" — poza ścieżką (domyślny stan gdy mamy aktywną kalkulację)
 * - "normal" — brak kalkulacji, pełny kolor (read-only przegląd)
 */
export type HighlightMode =
  | "highlighted"
  | "disabled"
  | "variant-nonASO"
  | "dim"
  | "normal";

export type HighlightMap = Map<string, HighlightMode>;

/** Polskie nazwy grup do legendy + sidebar. */
export const KIND_LABELS_PL: Record<NodeKind, string> = {
  route: "Endpointy API",
  task: "Zadania Celery",
  stage: "Etapy kalkulacji LTR",
  phase: "Fazy ekstrakcji PDF",
  db: "Tabele bazy danych",
};

/** Kolory grup (zgodne z planem). */
export const KIND_COLORS: Record<NodeKind, string> = {
  route: "#10b981",
  task: "#f59e0b",
  stage: "#8b5cf6",
  phase: "#0ea5e9",
  db: "#64748b",
};
