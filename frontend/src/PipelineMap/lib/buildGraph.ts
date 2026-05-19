/**
 * Transformuje TopologyResponse → ReactFlow nodes/edges z dagre auto-layout.
 *
 * Layout: hierarchiczny top-down (`rankdir=TB`).
 * Grupowanie: route'y zgrupowane po `tag` w jednym poziomie.
 * Kolejność grup: route → task → phase → stage → db.
 */

import dagre from "dagre";
import { Position, type Edge, type Node } from "@xyflow/react";
import type {
  HighlightMap,
  TopologyEdge,
  TopologyNode,
  TopologyResponse,
} from "../types";
import { KIND_COLORS } from "../types";

const NODE_WIDTH = 240;
const NODE_HEIGHT = 56;

const EDGE_STYLES: Record<TopologyEdge["kind"], { stroke: string; dasharray?: string }> = {
  sequence: { stroke: "#8b5cf6" },
  calls: { stroke: "#10b981" },
  celery: { stroke: "#f59e0b", dasharray: "6 4" },
  reads_db: { stroke: "#64748b", dasharray: "3 3" },
  writes_db: { stroke: "#64748b" },
};

function getNodeLabel(node: TopologyNode): string {
  if (node.kind === "route") return `${node.method} ${node.path}`;
  return node.label;
}

function getNodeSubLabel(node: TopologyNode): string | undefined {
  if (node.kind === "route") return node.tag;
  if (node.kind === "task") return `queue: ${node.queue}`;
  if (node.kind === "stage") return `Etap ${node.order}`;
  if (node.kind === "phase") return "Ekstrakcja";
  return undefined;
}

export interface BuiltGraph {
  nodes: BuiltNode[];
  edges: Edge[];
}

export type BuiltNodeData = {
  label: string;
  subLabel?: string;
  kind: TopologyNode["kind"];
  color: string;
  highlight: import("../types").HighlightMode;
  raw: TopologyNode;
} & Record<string, unknown>;

export type BuiltNode = Node<BuiltNodeData, "pipelineNode">;

export function buildGraph(
  topology: TopologyResponse,
  highlight: HighlightMap,
): BuiltGraph {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: "TB",
    nodesep: 50,
    ranksep: 90,
    marginx: 40,
    marginy: 40,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const node of topology.nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of topology.edges) {
    if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) continue;
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const rfNodes: BuiltNode[] = topology.nodes.map((node) => {
    const layout = g.node(node.id);
    const mode = highlight.get(node.id) ?? (highlight.size > 0 ? "dim" : "normal");
    return {
      id: node.id,
      type: "pipelineNode",
      position: {
        x: layout ? layout.x - NODE_WIDTH / 2 : 0,
        y: layout ? layout.y - NODE_HEIGHT / 2 : 0,
      },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      data: {
        label: getNodeLabel(node),
        subLabel: getNodeSubLabel(node),
        kind: node.kind,
        color: KIND_COLORS[node.kind],
        highlight: mode,
        raw: node,
      },
    };
  });

  const rfEdges: Edge[] = topology.edges
    .filter((e) => g.hasNode(e.source) && g.hasNode(e.target))
    .map((edge, idx) => {
      const style = EDGE_STYLES[edge.kind];
      const sourceMode = highlight.get(edge.source);
      const targetMode = highlight.get(edge.target);
      const bothHighlighted =
        (sourceMode === "highlighted" || sourceMode === "variant-nonASO") &&
        (targetMode === "highlighted" || targetMode === "variant-nonASO");
      const dim = highlight.size > 0 && !bothHighlighted;
      return {
        id: `${edge.source}->${edge.target}-${idx}`,
        source: edge.source,
        target: edge.target,
        animated: edge.kind === "celery" && !dim,
        style: {
          stroke: style.stroke,
          strokeWidth: bothHighlighted ? 2.5 : 1.5,
          strokeDasharray: style.dasharray,
          opacity: dim ? 0.15 : 1,
        },
        data: { kind: edge.kind },
      };
    });

  return { nodes: rfNodes, edges: rfEdges };
}
