/**
 * Renderuje graf pipeline'u w ReactFlow z custom node'em + dagre auto-layout.
 *
 * Props:
 *   topology — pełna odpowiedź /_introspect/topology
 *   highlight — mapa node_id → tryb podświetlenia (z pathInference)
 *   onNodeClick — handler dla kliknięcia (otwiera NodeDetailDrawer)
 */

import { useMemo, useCallback, memo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { buildGraph, type BuiltNode, type BuiltNodeData } from "../lib/buildGraph";
import type { HighlightMap, TopologyNode, TopologyResponse } from "../types";

interface PipelineCanvasProps {
  topology: TopologyResponse;
  highlight: HighlightMap;
  onNodeClick: (node: TopologyNode) => void;
}

// ─── Custom node renderer ───────────────────────────────────────────────────

const PipelineNodeComponent = memo(function PipelineNodeComponent({
  data,
}: NodeProps<BuiltNode>) {
  const { label, subLabel, kind, color, highlight } = data;

  const isHighlighted = highlight === "highlighted" || highlight === "variant-nonASO";
  const isDimmed = highlight === "dim";
  const isDisabled = highlight === "disabled";
  const isVariant = highlight === "variant-nonASO";

  const opacity = isDimmed ? 0.25 : isDisabled ? 0.5 : 1;
  const ringColor = isVariant ? "#f97316" : color;
  const ringWidth = isHighlighted ? 3 : 1;

  return (
    <div
      style={{
        opacity,
        borderColor: ringColor,
        borderWidth: ringWidth,
        background: isDisabled ? "#f1f5f9" : "white",
      }}
      className="rounded-lg border px-3 py-2 shadow-sm hover:shadow-md transition-shadow cursor-pointer min-w-[200px]"
    >
      <Handle type="target" position={Position.Top} style={{ background: color }} />
      <div className="flex items-center gap-2">
        <span
          style={{ backgroundColor: color }}
          className="inline-block w-2 h-2 rounded-full flex-shrink-0"
          aria-hidden="true"
        />
        <span className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold">
          {kindLabelShort(kind)}
        </span>
        {isVariant && (
          <span className="ml-auto text-[10px] font-semibold text-orange-600">
            nonASO
          </span>
        )}
        {isDisabled && (
          <span className="ml-auto text-[10px] font-semibold text-slate-400">
            off
          </span>
        )}
      </div>
      <div
        className="text-sm font-medium text-slate-800 leading-tight mt-1 break-words"
        style={{ wordBreak: "break-word" }}
      >
        {label}
      </div>
      {subLabel && (
        <div className="text-[11px] text-slate-500 mt-0.5">{subLabel}</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </div>
  );
});

function kindLabelShort(kind: TopologyNode["kind"]): string {
  switch (kind) {
    case "route":
      return "API";
    case "task":
      return "Celery";
    case "stage":
      return "Etap LTR";
    case "phase":
      return "Faza";
    case "db":
      return "DB";
  }
}

// ─── Main canvas component ──────────────────────────────────────────────────

export function PipelineCanvas({ topology, highlight, onNodeClick }: PipelineCanvasProps) {
  const nodeTypes = useMemo(() => ({ pipelineNode: PipelineNodeComponent }), []);

  const { nodes, edges } = useMemo(
    () => buildGraph(topology, highlight),
    [topology, highlight],
  );

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: BuiltNode) => {
      onNodeClick(node.data.raw);
    },
    [onNodeClick],
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.1}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={20} size={1} color="#e2e8f0" />
      <Controls showInteractive={false} />
      <MiniMap
        nodeColor={(node) => {
          const data = node.data as BuiltNodeData | undefined;
          return data?.color ?? "#94a3b8";
        }}
        nodeStrokeWidth={3}
        pannable
        zoomable
      />
    </ReactFlow>
  );
}
