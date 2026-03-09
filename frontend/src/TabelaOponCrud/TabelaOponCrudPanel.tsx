import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Typography,
  Chip
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import { supabase } from '../VertexExtractor/lib/supabaseClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TireCostRow {
  srednica: number;
  budget: number;
  medium: number;
  premium: number;
  wzmocnione_budget: number;
  wzmocnione_medium: number;
  wzmocnione_premium: number;
  wielosezon_budget: number;
  wielosezon_medium: number;
  wielosezon_premium: number;
  wielosezon_wzmocnione_budget: number;
  wielosezon_wzmocnione_medium: number;
  wielosezon_wzmocnione_premium: number;
}

interface ThresholdField {
  key: string;
  label: string;
  fallback: number;
}

// ---------------------------------------------------------------------------
// Threshold field definitions (driven by data, not hardcoded logic)
// ---------------------------------------------------------------------------

const ALL_SEASON_FIELDS: ThresholdField[] = [
  { key: 'all_season_threshold_1', label: 'Próg 1', fallback: 60000 },
  { key: 'all_season_threshold_2', label: 'Próg 2', fallback: 120000 },
  { key: 'all_season_threshold_3', label: 'Próg 3', fallback: 180000 },
  { key: 'all_season_threshold_4', label: 'Próg 4', fallback: 240000 },
  { key: 'all_season_threshold_5', label: 'Próg 5', fallback: 300000 },
];

const SEASONAL_FIELDS: ThresholdField[] = [
  { key: 'season_threshold_1', label: 'Próg 1', fallback: 120000 },
  { key: 'season_threshold_2', label: 'Próg 2', fallback: 180000 },
  { key: 'season_threshold_3', label: 'Próg 3', fallback: 240000 },
  { key: 'season_threshold_4', label: 'Próg 4', fallback: 300000 },
];

// ---------------------------------------------------------------------------
// Thresholds sub-component (READ-ONLY)
// ---------------------------------------------------------------------------

function TyreThresholdsSection({ onError }: { onError: (msg: string) => void }) {
  const [thresholds, setThresholds] = useState<Record<string, number>>({});
  const [loadingThresholds, setLoadingThresholds] = useState(true);

  const fetchThresholds = useCallback(async () => {
    setLoadingThresholds(true);
    try {
      const { data, error } = await supabase
        .from('tyre_configurations')
        .select('config_key, config_value');
      if (error) {
        onError(error.message);
        return;
      }
      const map: Record<string, number> = {};
      for (const row of data ?? []) {
        map[row.config_key] = parseFloat(row.config_value);
      }
      // Apply fallbacks for any missing keys
      for (const f of [...ALL_SEASON_FIELDS, ...SEASONAL_FIELDS]) {
        if (!(f.key in map)) map[f.key] = f.fallback;
      }
      setThresholds({ ...map });
    } catch (e) {
      onError(String(e));
    } finally {
      setLoadingThresholds(false);
    }
  }, [onError]);

  useEffect(() => {
    fetchThresholds();
  }, [fetchThresholds]);

  if (loadingThresholds) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  const renderGroup = (title: string, fields: ThresholdField[]) => (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.05em' }}>
        {title}
      </Typography>
      <Box display="grid" gridTemplateColumns={`repeat(${fields.length}, 1fr)`} gap={2}>
        {fields.map(f => (
          <Box key={f.key} sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 1.5, py: 0.75, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>{f.label}:</Typography>
            <Typography variant="body2" sx={{ color: 'primary.main', fontWeight: 600 }}>{(thresholds[f.key] ?? f.fallback).toLocaleString('pl-PL')} km</Typography>
          </Box>
        ))}
      </Box>
    </Paper>
  );

  return (
    <Paper sx={{ p: 2.5, mb: 3, bgcolor: 'grey.50', border: '1px solid', borderColor: 'divider' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6" sx={{ fontSize: '1rem' }}>
          📏 Progi przebiegowe opon
        </Typography>
        <Chip icon={<LockIcon />} label="ZAMROŻONE" size="small" color="default" variant="outlined" />
      </Box>
      <Box display="flex" flexDirection="column" gap={2}>
        {renderGroup('🛞 Opony wielosezonowe', ALL_SEASON_FIELDS)}
        {renderGroup('❄️ Opony sezonowe (letnie/zimowe)', SEASONAL_FIELDS)}
      </Box>
      <Typography variant="caption" sx={{ display: 'block', mt: 1.5, color: 'text.disabled', textAlign: 'center' }}>
        Progi km decydują o doliczaniu ułamkowych kompletów opon proporcjonalnie do przebiegu (V1 parity)
      </Typography>
    </Paper>
  );
}

// ---------------------------------------------------------------------------
// Main panel (READ-ONLY — frozen 2026-03-09)
// ---------------------------------------------------------------------------

export default function TabelaOponCrudPanel() {
  const [rows, setRows] = useState<TireCostRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const columns = [
    { name: 'budget', label: 'Budget' },
    { name: 'medium', label: 'Medium' },
    { name: 'premium', label: 'Premium' },
    { name: 'wzmocnione_budget', label: 'Wzmocnione Budget' },
    { name: 'wzmocnione_medium', label: 'Wzmocnione Medium' },
    { name: 'wzmocnione_premium', label: 'Wzmocnione Premium' },
    { name: 'wielosezon_budget', label: 'Wielosezonowe Budget' },
    { name: 'wielosezon_medium', label: 'Wielosezonowe Medium' },
    { name: 'wielosezon_premium', label: 'Wielosezonowe Premium' },
    { name: 'wielosezon_wzmocnione_budget', label: 'Wielosez.+Wzmocnione Budget' },
    { name: 'wielosezon_wzmocnione_medium', label: 'Wielosez.+Wzmocnione Medium' },
    { name: 'wielosezon_wzmocnione_premium', label: 'Wielosez.+Wzmocnione Premium' }
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    const { data, error } = await supabase.from('koszty_opon').select('*').order('srednica', { ascending: true });
    if (error) {
      setError(error.message);
    } else {
      setRows(data || []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <Box sx={{ mt: 2 }}>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {/* Thresholds section (read-only) */}
      <TyreThresholdsSection onError={(msg) => setError(msg)} />

      {/* Frozen tire costs table */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">Tabela Kosztów Opon (PLN Netto)</Typography>
        <Chip icon={<LockIcon />} label="ZAMROŻONE — Read Only" size="small" color="warning" variant="outlined" />
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: 650 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" p={5}><CircularProgress /></Box>
        ) : (
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold', whiteSpace: 'nowrap' }}>Średnica</TableCell>
                {columns.map(col => (
                  <TableCell key={col.name} sx={{ fontWeight: 'bold' }}>{col.label}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.srednica} hover>
                  <TableCell sx={{ fontSize: '1.1em', fontWeight: 500 }}>{row.srednica}"</TableCell>
                  {columns.map(col => (
                    <TableCell key={col.name}>{Number(row[col.name as keyof TireCostRow] ?? 0).toFixed(2)} zł</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>
    </Box>
  );
}
