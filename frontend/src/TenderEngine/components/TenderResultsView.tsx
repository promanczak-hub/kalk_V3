import React, { useState } from 'react';
import {
  Box, Paper, Typography, Chip, LinearProgress, Collapse,
  IconButton, Tooltip, Divider,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';
import type {
  TenderEvaluateResponse,
  VehicleTenderResult,
  ComplianceStatus,
} from '../hooks/useTenderEngine';

const STATUS_CHIP: Record<string, { icon: React.ReactElement; color: 'success' | 'error' | 'warning'; label: string }> = {
  MATCH: { icon: <CheckCircleIcon sx={{ fontSize: 16 }} />, color: 'success', label: 'Zgodny' },
  NOT_COMPLIANT: { icon: <CancelIcon sx={{ fontSize: 16 }} />, color: 'error', label: 'Niezgodny' },
  MISSING_DATA: { icon: <HelpOutlineIcon sx={{ fontSize: 16 }} />, color: 'warning', label: 'Brak danych' },
};

const CRITERION_STATUS: Record<ComplianceStatus, { color: string; icon: string }> = {
  PASS: { color: '#16a34a', icon: '✓' },
  FAIL: { color: '#dc2626', icon: '✗' },
  MISSING: { color: '#d97706', icon: '?' },
};

function ScoreBar({ score }: { score: number }) {
  const percent = Math.round(score * 100);
  const color = percent >= 80 ? '#16a34a' : percent >= 50 ? '#d97706' : '#dc2626';
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: 140 }}>
      <LinearProgress
        variant="determinate"
        value={percent}
        sx={{
          flexGrow: 1,
          height: 6,
          borderRadius: 3,
          bgcolor: '#f1f5f9',
          '& .MuiLinearProgress-bar': { bgcolor: color, borderRadius: 3 },
        }}
      />
      <Typography variant="caption" sx={{ fontWeight: 700, color, minWidth: 32, textAlign: 'right' }}>
        {percent}%
      </Typography>
    </Box>
  );
}

function VehicleResultRow({ result, rank }: { result: VehicleTenderResult; rank: number }) {
  const [expanded, setExpanded] = useState(false);
  const statusConfig = STATUS_CHIP[result.compliance_status] || STATUS_CHIP.MISSING_DATA;

  return (
    <Paper
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: expanded ? 'primary.main' : 'divider',
        borderRadius: 2,
        overflow: 'hidden',
        transition: 'all 0.15s ease',
        '&:hover': { borderColor: 'primary.light', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
      }}
    >
      {/* Header row */}
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 2,
          py: 1.5,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'action.hover' },
        }}
      >
        {/* Rank badge */}
        <Box sx={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '0.75rem',
          fontWeight: 700,
          bgcolor: rank <= 3 ? '#fef3c7' : '#f8fafc',
          color: rank <= 3 ? '#92400e' : '#64748b',
          border: '1px solid',
          borderColor: rank <= 3 ? '#fbbf24' : '#e2e8f0',
          flexShrink: 0,
        }}>
          {rank <= 3 ? <EmojiEventsIcon sx={{ fontSize: 14, color: rank === 1 ? '#f59e0b' : '#94a3b8' }} /> : rank}
        </Box>

        {/* Vehicle name */}
        <Typography variant="body2" sx={{ fontWeight: 600, flexGrow: 1 }}>
          {result.vehicle_label || result.vehicle_id}
        </Typography>

        {/* Score bar */}
        <ScoreBar score={result.compliance_score} />

        {/* Status chip */}
        <Chip
          icon={statusConfig.icon}
          label={statusConfig.label}
          color={statusConfig.color}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 600, fontSize: '0.7rem' }}
        />

        {/* Stats */}
        <Box sx={{ display: 'flex', gap: 0.5, flexShrink: 0 }}>
          <Tooltip title="MUST spełnione">
            <Chip
              label={`${result.must_pass_count}/${result.must_pass_count + result.must_fail_count}`}
              size="small"
              sx={{ fontSize: '0.65rem', height: 20, bgcolor: result.must_fail_count === 0 ? '#dcfce7' : '#fee2e2', fontWeight: 600 }}
            />
          </Tooltip>
        </Box>

        {/* Expand toggle */}
        <IconButton size="small">
          <ExpandMoreIcon
            sx={{
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s',
            }}
          />
        </IconButton>
      </Box>

      {/* Detailed criteria results */}
      <Collapse in={expanded}>
        <Divider />
        <Box sx={{ px: 2, py: 1.5, bgcolor: '#fafafa' }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 1 }}>
            {result.criteria_results.map((cr, idx) => {
              const statusCfg = CRITERION_STATUS[cr.status];
              return (
                <Box
                  key={idx}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    p: 1,
                    borderRadius: 1,
                    border: '1px solid #e2e8f0',
                    bgcolor: 'white',
                    fontSize: '0.78rem',
                  }}
                >
                  <Box sx={{
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.7rem',
                    fontWeight: 800,
                    color: 'white',
                    bgcolor: statusCfg.color,
                    flexShrink: 0,
                  }}>
                    {statusCfg.icon}
                  </Box>
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', lineHeight: 1.2 }}>
                      {cr.feature_name || cr.feature_key}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                      Wymóg: {cr.required_operator} {cr.required_value}
                      {cr.actual_value !== null && cr.actual_value !== undefined
                        ? ` → Wartość: ${cr.actual_value}`
                        : ' → Brak danych'}
                    </Typography>
                  </Box>
                  {cr.confidence !== null && cr.confidence !== undefined && (
                    <Tooltip title={`Pewność: ${Math.round(cr.confidence * 100)}%`}>
                      <Typography variant="caption" sx={{ color: '#94a3b8', fontSize: '0.6rem' }}>
                        {Math.round(cr.confidence * 100)}%
                      </Typography>
                    </Tooltip>
                  )}
                </Box>
              );
            })}
          </Box>
        </Box>
      </Collapse>
    </Paper>
  );
}

interface TenderResultsViewProps {
  results: TenderEvaluateResponse | null;
  isLoading: boolean;
}

export const TenderResultsView: React.FC<TenderResultsViewProps> = ({ results, isLoading }) => {
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 6, gap: 2 }}>
        <Box sx={{
          width: 48, height: 48, borderRadius: '50%',
          background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          animation: 'pulse 1.5s ease-in-out infinite',
          '@keyframes pulse': {
            '0%, 100%': { opacity: 1, transform: 'scale(1)' },
            '50%': { opacity: 0.7, transform: 'scale(0.95)' },
          },
        }}>
          <EmojiEventsIcon sx={{ color: 'white', fontSize: 24 }} />
        </Box>
        <Typography variant="body2" color="text.secondary">
          Oceniam flotę pod kątem kryteriów przetargowych...
        </Typography>
      </Box>
    );
  }

  if (!results) {
    return (
      <Box sx={{ py: 6, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Zdefiniuj kryteria przetargowe i kliknij "Oceń flotę"
        </Typography>
        <Typography variant="caption" color="text.disabled">
          System oceni zgodność pojazdów z wymaganiami i wyświetli ranking
        </Typography>
      </Box>
    );
  }

  // Sort results: MATCH first, then by score descending
  const sortedResults = [...results.results].sort((a, b) => {
    if (a.compliance_status === 'MATCH' && b.compliance_status !== 'MATCH') return -1;
    if (b.compliance_status === 'MATCH' && a.compliance_status !== 'MATCH') return 1;
    return b.compliance_score - a.compliance_score;
  });

  return (
    <Box>
      {/* Summary stats */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <StatCard
          label="Ocenionych"
          value={results.total_vehicles}
          color="#64748b"
        />
        <StatCard
          label="Zgodnych"
          value={results.match_count}
          color="#16a34a"
          highlight
        />
        <StatCard
          label="Niezgodnych"
          value={results.not_compliant_count}
          color="#dc2626"
        />
        <StatCard
          label="Brak danych"
          value={results.missing_data_count}
          color="#d97706"
        />
      </Box>

      {/* Vehicle result cards */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {sortedResults.map((result, idx) => (
          <VehicleResultRow key={result.vehicle_id} result={result} rank={idx + 1} />
        ))}
      </Box>
    </Box>
  );
};

function StatCard({ label, value, color, highlight }: { label: string; value: number; color: string; highlight?: boolean }) {
  return (
    <Paper
      elevation={0}
      sx={{
        px: 2,
        py: 1,
        border: '1px solid',
        borderColor: highlight ? color : 'divider',
        borderRadius: 2,
        bgcolor: highlight ? `${color}08` : 'transparent',
        minWidth: 90,
        textAlign: 'center',
      }}
    >
      <Typography variant="h6" sx={{ fontWeight: 800, color, lineHeight: 1 }}>
        {value}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
        {label}
      </Typography>
    </Paper>
  );
}
