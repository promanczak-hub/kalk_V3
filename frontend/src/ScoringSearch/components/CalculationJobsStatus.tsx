import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Chip, Tooltip, IconButton,
  Collapse, CircularProgress, Alert,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import RefreshIcon from '@mui/icons-material/Refresh';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

interface JobStatus {
  vehicle_id: string;
  status: string;
  error_code: string | null;
  error_detail: string | null;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  monthly_price_net: number | null;
}

interface JobsStatusResponse {
  total: number;
  done: number;
  failed: number;
  running: number;
  queued: number;
  failed_jobs: JobStatus[];
}

const ERROR_CODE_LABELS: Record<string, string> = {
  NO_BASE_PRICE: 'Brak ceny bazowej',
  NO_SAMAR_CLASS: 'Brak klasy SAMAR',
  BUILD_INPUT_ERROR: 'Błąd budowania inputu',
  INVALID_STAN_JSON: 'Nieprawidłowy stan JSON',
  NO_CC_SETTINGS: 'Brak ustawień CC',
  CALC_ERROR: 'Błąd kalkulacji',
  DB_UPSERT_ERROR: 'Błąd zapisu do bazy',
  NO_MATRIX_CELLS: 'Brak komórek matrycy',
};

const REFRESH_INTERVAL_MS = 30_000;

const CalculationJobsStatus: React.FC = () => {
  const [data, setData] = useState<JobsStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/kalkulacje/jobs-status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: JobsStatusResponse = await res.json();
      setData(json);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchStatus]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1 }}>
        <CircularProgress size={14} />
        <Typography variant="caption" color="textSecondary">Ładowanie statusu jobów...</Typography>
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Alert severity="warning" sx={{ py: 0.5, fontSize: '0.75rem' }}>
        Nie udało się załadować statusu kalkulacji
      </Alert>
    );
  }

  const hasFailed = data.failed > 0;
  const hasPending = data.running + data.queued > 0;

  return (
    <Box sx={{
      border: '1px solid',
      borderColor: hasFailed ? 'error.light' : 'divider',
      borderRadius: 1,
      overflow: 'hidden',
    }}>
      {/* Header row */}
      <Box
        sx={{
          display: 'flex', alignItems: 'center', gap: 1,
          px: 1.5, py: 0.75,
          bgcolor: hasFailed ? 'rgba(239,68,68,0.05)' : 'background.paper',
          cursor: hasFailed ? 'pointer' : 'default',
        }}
        onClick={() => hasFailed && setExpanded(e => !e)}
      >
        <Typography variant="caption" sx={{ fontWeight: 'bold', mr: 'auto', fontSize: '0.68rem', letterSpacing: '0.05em' }}>
          KALKULACJE
        </Typography>

        <Tooltip title={`Zakończone: ${data.done}`}>
          <Chip
            icon={<CheckCircleOutlineIcon sx={{ fontSize: '0.8rem !important' }} />}
            label={data.done}
            size="small"
            color="success"
            sx={{ height: 18, fontSize: '0.65rem', '.MuiChip-label': { px: 0.75 } }}
          />
        </Tooltip>

        {hasFailed && (
          <Tooltip title={`Błędy: ${data.failed}`}>
            <Chip
              icon={<ErrorOutlineIcon sx={{ fontSize: '0.8rem !important' }} />}
              label={data.failed}
              size="small"
              color="error"
              sx={{ height: 18, fontSize: '0.65rem', '.MuiChip-label': { px: 0.75 } }}
            />
          </Tooltip>
        )}

        {hasPending && (
          <Tooltip title={`W toku: ${data.running + data.queued}`}>
            <Chip
              icon={<AccessTimeIcon sx={{ fontSize: '0.8rem !important' }} />}
              label={data.running + data.queued}
              size="small"
              color="warning"
              sx={{ height: 18, fontSize: '0.65rem', '.MuiChip-label': { px: 0.75 } }}
            />
          </Tooltip>
        )}

        <Tooltip title="Odśwież">
          <IconButton
            size="small"
            onClick={e => { e.stopPropagation(); fetchStatus(); }}
            sx={{ p: 0.25 }}
          >
            <RefreshIcon sx={{ fontSize: '0.9rem' }} />
          </IconButton>
        </Tooltip>

        {hasFailed && (
          expanded
            ? <ExpandLessIcon sx={{ fontSize: '1rem', color: 'text.secondary' }} />
            : <ExpandMoreIcon sx={{ fontSize: '1rem', color: 'text.secondary' }} />
        )}
      </Box>

      {/* Failed jobs list */}
      <Collapse in={expanded && hasFailed}>
        <Box sx={{ maxHeight: 240, overflowY: 'auto', borderTop: '1px solid', borderColor: 'divider' }}>
          {data.failed_jobs.map((job: JobStatus) => (
            <Box
              key={job.vehicle_id}
              sx={{
                px: 1.5, py: 0.75,
                borderBottom: '1px solid', borderColor: 'divider',
                '&:last-child': { borderBottom: 0 },
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', opacity: 0.55, fontSize: '0.6rem' }}>
                  {job.vehicle_id.slice(0, 8)}…
                </Typography>
                <Chip
                  label={ERROR_CODE_LABELS[job.error_code ?? ''] ?? job.error_code ?? 'Nieznany błąd'}
                  size="small"
                  color="error"
                  variant="outlined"
                  sx={{ height: 16, fontSize: '0.6rem', '.MuiChip-label': { px: 0.5 } }}
                />
              </Box>
              {job.error_detail && (
                <Typography
                  variant="caption"
                  color="error.main"
                  sx={{ fontSize: '0.6rem', display: 'block', mt: 0.25, wordBreak: 'break-all' }}
                >
                  {job.error_detail.slice(0, 140)}
                </Typography>
              )}
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
};

export default CalculationJobsStatus;
