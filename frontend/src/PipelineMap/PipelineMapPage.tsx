/**
 * Strona "Mapa Pipeline" — interaktywny graf endpointów i etapów kalkulacji.
 *
 * URL params:
 *   ?kalk=<vehicle_id> — pobiera FleetVehicleView z Supabase i podświetla ścieżkę
 *
 * Bez query → przegląd read-only, wszystkie nody w pełnym kolorze.
 */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Box, Typography, Alert, CircularProgress, Stack, Chip } from "@mui/material";

import { apiClient } from "../lib/apiClient";
import { supabase } from "../lib/supabaseClient";
import type { FleetVehicleView } from "../VertexExtractor/types";

import { PipelineCanvas } from "./components/PipelineCanvas";
import { NodeDetailDrawer } from "./components/NodeDetailDrawer";
import { inferHighlight } from "./lib/pathInference";
import type { TopologyNode, TopologyResponse } from "./types";
import { KIND_COLORS, KIND_LABELS_PL } from "./types";

function Legend() {
  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        position: "absolute",
        top: 16, right: 16,
        zIndex: 5,
        bgcolor: "background.paper",
        borderRadius: 1,
        boxShadow: 1,
        px: 1.5, py: 1,
        flexWrap: "wrap",
        gap: 0.5,
      }}
    >
      {(Object.keys(KIND_COLORS) as Array<keyof typeof KIND_COLORS>).map((kind) => (
        <Chip
          key={kind}
          size="small"
          label={KIND_LABELS_PL[kind]}
          sx={{
            "& .MuiChip-label": { fontSize: 11 },
            borderLeft: `4px solid ${KIND_COLORS[kind]}`,
            borderRadius: 1,
            bgcolor: "transparent",
          }}
          variant="outlined"
        />
      ))}
    </Stack>
  );
}

export default function PipelineMapPage() {
  const [searchParams] = useSearchParams();
  const kalkId = searchParams.get("kalk");

  const [topology, setTopology] = useState<TopologyResponse | null>(null);
  const [vehicle, setVehicle] = useState<FleetVehicleView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);

  // Fetch topology raz na mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.fetch("/api/_introspect/topology");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as TopologyResponse;
        if (!cancelled) setTopology(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch konkretnej kalkulacji (jeśli ?kalk=...)
  useEffect(() => {
    if (!kalkId) {
      setVehicle(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const { data, error: supErr } = await supabase
          .from("vehicle_synthesis")
          .select("*")
          .eq("id", kalkId)
          .maybeSingle();
        if (supErr) throw supErr;
        if (!cancelled) {
          setVehicle((data as FleetVehicleView | null) ?? null);
        }
      } catch (e) {
        console.warn("Nie udało się pobrać kalkulacji:", e);
        if (!cancelled) setVehicle(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [kalkId]);

  const highlight = useMemo(() => {
    if (!topology) return new Map<string, ReturnType<typeof inferHighlight> extends Map<string, infer V> ? V : never>();
    return inferHighlight(vehicle, topology);
  }, [vehicle, topology]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 10 }}>
        <CircularProgress size={32} />
        <Typography variant="body2" sx={{ ml: 2, color: "text.secondary" }}>
          Ładowanie topologii pipeline'u…
        </Typography>
      </Box>
    );
  }

  if (error || !topology) {
    return (
      <Box sx={{ maxWidth: 720, mx: "auto", mt: 6 }}>
        <Alert severity="error">
          Nie udało się załadować topologii: {error ?? "brak danych"}.
        </Alert>
      </Box>
    );
  }

  const stats = topology.counts;

  return (
    <Box
      sx={{
        height: "calc(100vh - 96px)",
        display: "flex",
        flexDirection: "column",
        px: { xs: 1, md: 2 },
        pb: 1,
      }}
    >
      {/* Nagłówek */}
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 2, py: 2, flexWrap: "wrap" }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Mapa Pipeline
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          {stats.routes} endpointów · {stats.tasks} zadań Celery · {stats.stages} etapów LTR · {stats.phases} faz ekstrakcji · {stats.db} tabel DB
        </Typography>
        {vehicle && (
          <Chip
            size="small"
            color="primary"
            label={`Podświetlono ścieżkę dla: ${vehicle.brand ?? "?"} ${vehicle.model ?? ""}`.trim()}
            sx={{ ml: "auto" }}
          />
        )}
        {kalkId && !vehicle && (
          <Chip
            size="small"
            color="warning"
            label={`Nie znaleziono kalkulacji ${kalkId.slice(0, 8)}… — pokazuję pełny graf`}
            sx={{ ml: "auto" }}
          />
        )}
      </Box>

      {/* Canvas */}
      <Box sx={{ flex: 1, position: "relative", border: 1, borderColor: "divider", borderRadius: 1, overflow: "hidden" }}>
        <Legend />
        <PipelineCanvas
          topology={topology}
          highlight={highlight}
          onNodeClick={setSelectedNode}
        />
      </Box>

      <NodeDetailDrawer node={selectedNode} onClose={() => setSelectedNode(null)} />
    </Box>
  );
}
