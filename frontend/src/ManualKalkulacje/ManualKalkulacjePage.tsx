import { useCallback, useEffect, useState } from 'react';
import {
  Box, Typography, Button, CircularProgress, ToggleButtonGroup,
  ToggleButton, Dialog, DialogTitle, DialogContent, DialogActions,
  Stack, Fab, Tooltip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useNavigate } from 'react-router-dom';
import { KalkulacjaCard } from './KalkulacjaCard';
import { PricingPanel } from './PricingPanel';
import type { KalkulacjaListItem, PricingState } from './types';
import { DEFAULT_PRICING_COMPONENTS } from './types';
import { apiClient } from '../lib/apiClient';

type FilterSource = 'all' | 'manual' | 'clone' | 'pdf';

function extractSource(item: KalkulacjaListItem): 'pdf' | 'manual' | 'clone' {
  return (item.source as 'pdf' | 'manual' | 'clone') ?? 'pdf';
}

export function ManualKalkulacjePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<KalkulacjaListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<FilterSource>('all');

  // Pricing edit dialog state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingPricing, setEditingPricing] = useState<PricingState>({
    components: DEFAULT_PRICING_COMPONENTS.map((c) => ({ ...c })),
    discount_pct: 0,
  });

  // Delete confirm state
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadItems = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.fetch('/api/kalkulacje');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: KalkulacjaListItem[] = await resp.json();
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load kalkulacje:', err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);


  useEffect(() => { loadItems(); }, [loadItems]);

  const filtered = items.filter((item) => {
    if (filter === 'all') return true;
    return extractSource(item) === filter;
  });

  const handleClone = useCallback(async (id: string) => {
    try {
      await apiClient.fetch(`/api/kalkulacje/${id}/duplicate`, { method: 'POST' });
      await loadItems();
    } catch (err) {
      console.error('Clone failed', err);
    }
  }, [loadItems]);

  const handleDelete = useCallback(async () => {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await apiClient.fetch(`/api/kalkulacje/${deleteId}`, { method: 'DELETE' });
      setDeleteId(null);
      await loadItems();
    } finally {
      setDeleting(false);
    }
  }, [deleteId, loadItems]);

  const handleEditPricing = useCallback((id: string) => {
    const item = items.find((i) => i.id === id);
    const stan = (item as unknown as { stan_json?: Record<string, unknown> })?.stan_json;
    const storedPricing = stan?.['pricing'] as PricingState | undefined;
    setEditingPricing(
      storedPricing ?? {
        components: DEFAULT_PRICING_COMPONENTS.map((c) => ({ ...c })),
        discount_pct: 0,
      },
    );
    setEditingId(id);
  }, [items]);

  const handlePricingSaved = useCallback(async () => {
    setEditingId(null);
    await loadItems();
  }, [loadItems]);

  const counts: Record<FilterSource, number> = {
    all: items.length,
    manual: items.filter((i) => extractSource(i) === 'manual').length,
    clone: items.filter((i) => extractSource(i) === 'clone').length,
    pdf: items.filter((i) => extractSource(i) === 'pdf').length,
  };

  return (
    <Box sx={{ position: 'relative', minHeight: '60vh' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box>
          <Typography variant="h5">Kalkulacje Manualne</Typography>
          <Typography variant="body2" color="text.secondary">
            Twórz kalkulacje bez PDF-a lub klonuj istniejące w celu edycji.
          </Typography>
        </Box>
        <Button startIcon={<RefreshIcon />} onClick={loadItems} size="small" variant="outlined">
          Odśwież
        </Button>
      </Box>

      {/* Filtry */}
      <ToggleButtonGroup
        size="small"
        value={filter}
        exclusive
        onChange={(_, val) => val && setFilter(val)}
        sx={{ mb: 2 }}
      >
        <ToggleButton value="all">Wszystkie ({counts.all})</ToggleButton>
        <ToggleButton value="manual">Manualne ({counts.manual})</ToggleButton>
        <ToggleButton value="clone">Kopie ({counts.clone})</ToggleButton>
        <ToggleButton value="pdf">PDF ({counts.pdf})</ToggleButton>
      </ToggleButtonGroup>

      {/* Lista */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : filtered.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary">Brak kalkulacji</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Kliknij „+" aby stworzyć nową kalkulację manualną.
          </Typography>
        </Box>
      ) : (
        <Stack spacing={1.5}>
          {filtered.map((item) => (
            <KalkulacjaCard
              key={item.id}
              item={item}
              onClone={handleClone}
              onDelete={(id) => setDeleteId(id)}
              onEditPricing={handleEditPricing}
            />
          ))}
        </Stack>
      )}

      {/* FAB — redirects to VertexExtractor where the blank-CardSummary flow now lives.
          The old in-page CreateManualModal was replaced by /extract/blank + HITL wizard. */}
      <Tooltip title="Nowa kalkulacja manualna (otwórz extractor)" placement="left">
        <Fab
          color="primary"
          onClick={() => navigate('/')}
          sx={{ position: 'fixed', bottom: 32, right: 32 }}
        >
          <AddIcon />
        </Fab>
      </Tooltip>

      {/* Dialog edycji cen */}
      <Dialog open={editingId != null} onClose={() => setEditingId(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Edycja panelu cenowego</DialogTitle>
        <DialogContent dividers>
          {editingId && (
            <PricingPanel
              initialState={editingPricing}
              kalkulacjaId={editingId}
              onSave={handlePricingSaved}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditingId(null)}>Zamknij</Button>
        </DialogActions>
      </Dialog>

      {/* Dialog usunięcia */}
      <Dialog open={deleteId != null} onClose={() => setDeleteId(null)} maxWidth="xs">
        <DialogTitle>Usuń kalkulację?</DialogTitle>
        <DialogContent>
          <Typography>Tej operacji nie można cofnąć. Kalkulacja zostanie trwale usunięta z bazy.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteId(null)}>Anuluj</Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleDelete}
            disabled={deleting}
            startIcon={deleting ? <CircularProgress size={16} /> : null}
          >
            {deleting ? 'Usuwanie…' : 'Usuń'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
