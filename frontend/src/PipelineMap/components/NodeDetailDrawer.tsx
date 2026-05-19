/**
 * MUI Drawer pokazujący szczegóły wybranego node'a: file path, tag/queue, opis,
 * lista DB tables, depends_on.
 *
 * Po polsku, otwiera się od prawej.
 */

import { Drawer, Box, Typography, Chip, Divider, IconButton, Stack } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import type { TopologyNode } from "../types";
import { KIND_LABELS_PL, KIND_COLORS } from "../types";

interface NodeDetailDrawerProps {
  node: TopologyNode | null;
  onClose: () => void;
}

export function NodeDetailDrawer({ node, onClose }: NodeDetailDrawerProps) {
  return (
    <Drawer anchor="right" open={node !== null} onClose={onClose} keepMounted={false}>
      <Box sx={{ width: { xs: 320, sm: 420 }, p: 3 }} role="presentation">
        {node && <NodeDetailContent node={node} onClose={onClose} />}
      </Box>
    </Drawer>
  );
}

function NodeDetailContent({ node, onClose }: { node: TopologyNode; onClose: () => void }) {
  const color = KIND_COLORS[node.kind];
  return (
    <>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Box
            sx={{
              width: 12, height: 12, borderRadius: "50%",
              backgroundColor: color,
            }}
          />
          <Typography variant="overline" sx={{ color: "text.secondary", lineHeight: 1 }}>
            {KIND_LABELS_PL[node.kind]}
          </Typography>
        </Stack>
        <IconButton onClick={onClose} size="small" aria-label="Zamknij">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <Typography variant="h6" sx={{ mb: 0.5, wordBreak: "break-word" }}>
        {node.kind === "route" ? `${node.method} ${node.path}` : node.label}
      </Typography>

      {node.description && (
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
          {node.description}
        </Typography>
      )}

      <Divider sx={{ my: 2 }} />

      {/* Pola zależne od typu */}
      {node.kind === "route" && (
        <Section title="Tag (router)">
          <Chip label={node.tag} size="small" />
        </Section>
      )}

      {node.kind === "task" && (
        <Section title="Kolejka">
          <Chip label={node.queue} size="small" color="warning" variant="outlined" />
        </Section>
      )}

      {node.kind === "stage" && (
        <>
          <Section title="Numer etapu">
            <Chip label={`#${node.order} z 12`} size="small" color="secondary" />
          </Section>
          {node.depends_on.length > 0 && (
            <Section title="Zależy od">
              <Stack direction="row" flexWrap="wrap" gap={0.5}>
                {node.depends_on.map((id) => (
                  <Chip key={id} label={id.replace("stage:ltr:", "Etap ")} size="small" variant="outlined" />
                ))}
              </Stack>
            </Section>
          )}
          {node.db_tables.length > 0 && (
            <Section title="Tabele DB">
              <Stack direction="row" flexWrap="wrap" gap={0.5}>
                {node.db_tables.map((t) => (
                  <Chip key={t} label={t} size="small" variant="outlined" sx={{ fontFamily: "monospace" }} />
                ))}
              </Stack>
            </Section>
          )}
        </>
      )}

      {node.kind === "phase" && node.depends_on.length > 0 && (
        <Section title="Zależy od">
          <Stack direction="row" flexWrap="wrap" gap={0.5}>
            {node.depends_on.map((id) => (
              <Chip key={id} label={id} size="small" variant="outlined" />
            ))}
          </Stack>
        </Section>
      )}

      {node.file && (
        <Section title="Plik źródłowy">
          <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 12, color: "text.secondary", wordBreak: "break-all" }}>
            {node.file}
          </Typography>
        </Section>
      )}

      <Section title="ID węzła">
        <Typography variant="caption" sx={{ fontFamily: "monospace", color: "text.disabled", wordBreak: "break-all" }}>
          {node.id}
        </Typography>
      </Section>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, display: "block", mb: 0.5 }}>
        {title}
      </Typography>
      {children}
    </Box>
  );
}
