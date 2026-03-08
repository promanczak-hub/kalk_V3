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
  Button,
  TextField,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Typography
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import { supabase } from '../VertexExtractor/lib/supabaseClient';
import ConfigTableToolbar from '../components/ConfigTableToolbar';

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
// Thresholds sub-component
// ---------------------------------------------------------------------------

function TyreThresholdsSection({ onError }: { onError: (msg: string) => void }) {
  const [thresholds, setThresholds] = useState<Record<string, number>>({});
  const [initialThresholds, setInitialThresholds] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
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
      setInitialThresholds({ ...map });
    } catch (e) {
      onError(String(e));
    } finally {
      setLoadingThresholds(false);
    }
  }, [onError]);

  useEffect(() => {
    fetchThresholds();
  }, [fetchThresholds]);

  const handleThresholdChange = (key: string, value: string) => {
    const num = parseFloat(value);
    setThresholds(prev => ({ ...prev, [key]: isNaN(num) ? 0 : num }));
    setSaved(false);
  };

  const hasChanges = Object.keys(thresholds).some(
    k => thresholds[k] !== initialThresholds[k]
  );

  const handleSaveThresholds = async () => {
    setSaving(true);
    try {
      const changedKeys = Object.keys(thresholds).filter(
        k => thresholds[k] !== initialThresholds[k]
      );
      for (const key of changedKeys) {
        const { error } = await supabase
          .from('tyre_configurations')
          .update({ config_value: String(thresholds[key]) })
          .eq('config_key', key);
        if (error) {
          onError(`Błąd zapisu ${key}: ${error.message}`);
          setSaving(false);
          return;
        }
      }
      setInitialThresholds({ ...thresholds });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      onError(String(e));
    } finally {
      setSaving(false);
    }
  };

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
          <TextField
            key={f.key}
            label={f.label}
            type="number"
            size="small"
            value={thresholds[f.key] ?? f.fallback}
            onChange={e => handleThresholdChange(f.key, e.target.value)}
            slotProps={{ input: { endAdornment: <Typography variant="caption" sx={{ color: 'text.disabled', ml: 0.5 }}>km</Typography> } }}
            inputProps={{ step: '1000' }}
            fullWidth
          />
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
        <Button
          variant="contained"
          size="small"
          disabled={saving || !hasChanges}
          onClick={handleSaveThresholds}
          sx={{
            bgcolor: saved ? 'success.main' : undefined,
            '&:hover': saved ? { bgcolor: 'success.dark' } : undefined,
            minWidth: 130,
          }}
        >
          {saving ? 'Zapisuję...' : saved ? '✓ Zapisano' : 'Zapisz progi'}
        </Button>
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
// Main panel
// ---------------------------------------------------------------------------

export default function TabelaOponCrudPanel() {
  const [rows, setRows] = useState<TireCostRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [openDialog, setOpenDialog] = useState(false);
  const [editRow, setEditRow] = useState<TireCostRow | null>(null);
  const [formData, setFormData] = useState<Partial<TireCostRow>>({});

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

  const handleOpenEdit = (row: TireCostRow) => {
    setEditRow(row);
    setFormData({ ...row });
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleSave = async () => {
    setLoading(true);
    if (editRow) {
      const { error } = await supabase
        .from('koszty_opon')
        .update(formData)
        .eq('srednica', editRow.srednica);
      if (error) {
        setError(error.message);
      } else {
        fetchData();
      }
    }
    setOpenDialog(false);
    setLoading(false);
  };

  return (
    <Box sx={{ mt: 2 }}>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {/* Thresholds section */}
      <TyreThresholdsSection onError={(msg) => setError(msg)} />

      {/* Existing tire costs table */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">Tabela Kosztów Opon (PLN Netto)</Typography>
        <ConfigTableToolbar tableName="koszty_opon" tableLabel="Koszty Opon" onDataChanged={fetchData} />
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: 650 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" p={5}><CircularProgress /></Box>
        ) : (
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold', whiteSpace: 'nowrap' }}>Akcje</TableCell>
                <TableCell sx={{ fontWeight: 'bold', whiteSpace: 'nowrap' }}>Średnica</TableCell>
                {columns.map(col => (
                  <TableCell key={col.name} sx={{ fontWeight: 'bold' }}>{col.label}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.srednica} hover>
                  <TableCell>
                    <IconButton size="small" color="primary" onClick={() => handleOpenEdit(row)}>
                      <EditIcon fontSize="small"/>
                    </IconButton>
                  </TableCell>
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

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>Edycja Kosztów dla średnicy {editRow?.srednica}"</DialogTitle>
        <DialogContent dividers>
          <Box display="grid" gridTemplateColumns="repeat(3, 1fr)" gap={2} pt={1}>
            {columns.map(col => (
              <TextField
                key={col.name}
                label={col.label}
                type="number"
                value={formData[col.name as keyof TireCostRow] ?? ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setFormData({
                    ...formData,
                    [col.name]: val === '' ? null : parseFloat(val)
                  });
                }}
                fullWidth
                variant="outlined"
                size="small"
                inputProps={{ step: "0.01" }}
              />
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave} disabled={loading}>
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
