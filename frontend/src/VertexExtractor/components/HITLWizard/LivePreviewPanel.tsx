import { Alert, Box, CircularProgress, Paper, Stack, Typography } from "@mui/material";
import { CheckCircle2, XCircle } from "lucide-react";
import type { PreviewResponse } from "./types";

interface LivePreviewPanelProps {
  loading: boolean;
  data: PreviewResponse | null;
  validationError: string | null;
}

function fmt(n: number): string {
  return n.toLocaleString("pl-PL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function LivePreviewPanel({
  loading,
  data,
  validationError,
}: LivePreviewPanelProps) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        borderRadius: 2,
        bgcolor: "info.50",
        borderColor: "info.light",
      }}
      data-testid="hitl-live-preview"
    >
      <Stack direction="row" alignItems="center" spacing={1} mb={1.5}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          📊 Podgląd kalkulacji
        </Typography>
        {loading && <CircularProgress size={14} />}
      </Stack>

      {!data && !loading && (
        <Typography variant="body2" color="text.secondary">
          Wybierz typ zabudowy lub przesuń pozycje by zobaczyć podgląd.
        </Typography>
      )}

      {data && (
        <Stack spacing={1}>
          <Typography variant="body2">
            <strong>Composite body_style:</strong>{" "}
            <span data-testid="composite-body-style">
              {data.composite_body_style ?? "—"}
            </span>
          </Typography>
          {data.body_type ? (
            <>
              <Typography variant="body2">
                <strong>body_types match:</strong>{" "}
                {data.body_type.matched_name}{" "}
                <Typography component="span" variant="caption" color="text.secondary">
                  ({data.body_type.match_method}, score {data.body_type.score})
                </Typography>
              </Typography>
              <Typography variant="body2">
                <strong>WR korekta (utrata_wartości):</strong>{" "}
                <span style={{ fontFamily: "monospace" }}>
                  {data.body_type.utrata_wartosci.toFixed(2)}%
                </span>
              </Typography>
            </>
          ) : (
            <Typography variant="body2" color="warning.main">
              Brak dopasowanego body_type w SOT — kalkulacja LTR użyje defaultu (WR 0%).
            </Typography>
          )}

          <Box mt={1} p={1.25} bgcolor="background.paper" borderRadius={1}>
            <Stack spacing={0.25}>
              <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 13 }}>
                Cena bazowa: {fmt(data.capex.base)} zł
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 13 }}>
                + Opcje fabryczne: {fmt(data.capex.factory)} zł
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 13 }}>
                + Zabudowa: {fmt(data.capex.zabudowa)} zł
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 13 }}>
                + Agregat / wyposażenie: {fmt(data.capex.agregat)} zł
              </Typography>
              <Box mt={0.5} pt={0.5} borderTop="1px solid" borderColor="divider">
                <Typography
                  variant="body2"
                  sx={{ fontFamily: "monospace", fontSize: 14, fontWeight: 700 }}
                  data-testid="capex-total"
                >
                  CAPEX suma: {fmt(data.capex.total_capex)} zł brutto
                </Typography>
              </Box>
            </Stack>
          </Box>
        </Stack>
      )}

      {validationError && (
        <Alert
          severity="error"
          icon={<XCircle size={18} />}
          sx={{ mt: 1.5 }}
        >
          {validationError}
        </Alert>
      )}
      {data && !validationError && (
        <Alert severity="success" icon={<CheckCircle2 size={18} />} sx={{ mt: 1.5 }}>
          Walidacja OK — można zapisać.
        </Alert>
      )}
    </Paper>
  );
}
