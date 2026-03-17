import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Box, Paper, Typography, Divider, CircularProgress, Button, Tooltip,
  Snackbar, Alert, LinearProgress,
} from '@mui/material';
import CalculateIcon from '@mui/icons-material/Calculate';
import { ScoringFilters } from './components/ScoringFilters';
import { ScoringResults } from './components/ScoringResults';
import type { SelectedFeature, SearchContext } from './types';

interface CacheProgress {
  total: number;
  done: number;
  current_vehicle: string | null;
  status: 'running' | 'done' | 'unknown';
}

export const ScoringSearchPage: React.FC = () => {
  const [searchContext, setSearchContext] = useState<SearchContext>({
    brands: [],
    models: [],
    samarClassIds: [],
    duration_months_range: [24, 48],
    annual_mileage_range: [15000, 30000],
    margin_pct: 10,
    monthly_budget: undefined,
  });
  
  const [selectedFeatures, setSelectedFeatures] = useState<SelectedFeature[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);

  // ── Progress tracking ──
  const [cacheProgress, setCacheProgress] = useState<CacheProgress | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Clean up on unmount
  useEffect(() => stopPolling, [stopPolling]);

  const startPolling = useCallback(async (jobId: string) => {
    stopPolling();
    const { apiFetch } = await import('../lib/api');

    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/scoring-search/cache/progress/${jobId}`);
        if (!res.ok) return;
        const data: CacheProgress = await res.json();
        setCacheProgress(data);

        if (data.status === 'done') {
          stopPolling();
          setIsRefreshing(false);
          setSnackbarMessage(`Przeliczono ${data.total} pojazdów. Wyszukaj ponownie, aby zobaczyć wyniki.`);
          // Clear progress bar after 3s
          setTimeout(() => setCacheProgress(null), 3000);
        }
      } catch {
        // Ignore polling errors (backend may be busy)
      }
    }, 2000);
  }, [stopPolling]);

  const handleRefreshMissing = async () => {
    setIsRefreshing(true);
    setCacheProgress(null);
    try {
      const { apiFetch } = await import('../lib/api');
      const res = await apiFetch('/api/scoring-search/cache/refresh-missing', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setSnackbarMessage(data.message);
        if (data.job_id) {
          startPolling(data.job_id);
        } else {
          // No missing vehicles → no polling needed
          setIsRefreshing(false);
        }
      } else {
        setSnackbarMessage("Wystąpił błąd podczas uruchamiania kalkulacji.");
        setIsRefreshing(false);
      }
    } catch {
      setSnackbarMessage("Wystąpił błąd sieci podczas uruchamiania kalkulacji.");
      setIsRefreshing(false);
    }
  };

  // Function to execute the search
  const handleSearch = async () => {
    setIsSearching(true);
    try {
      // Build requirements payload out of selectedFeatures and context
      const requirements = [...selectedFeatures];
      
      // Duration range (gte + lte pair)
      requirements.push({ feature_key: 'duration_months', operator: 'gte', value: searchContext.duration_months_range[0], requirement: 'MUST_HAVE', weight: 1 });
      requirements.push({ feature_key: 'duration_months', operator: 'lte', value: searchContext.duration_months_range[1], requirement: 'MUST_HAVE', weight: 1 });
      // Mileage range (gte + lte pair)
      requirements.push({ feature_key: 'annual_mileage', operator: 'gte', value: searchContext.annual_mileage_range[0], requirement: 'MUST_HAVE', weight: 1 });
      requirements.push({ feature_key: 'annual_mileage', operator: 'lte', value: searchContext.annual_mileage_range[1], requirement: 'MUST_HAVE', weight: 1 });
      if (searchContext.margin_pct !== undefined) {
        requirements.push({ feature_key: 'margin_pct', operator: 'gte', value: searchContext.margin_pct, requirement: 'MUST_HAVE', weight: 1 });
      }
      if (searchContext.monthly_budget) {
        requirements.push({ feature_key: 'monthly_price_net', operator: 'lte', value: searchContext.monthly_budget, requirement: 'MUST_HAVE', weight: 1 });
      }

      const payload = {
        brands: searchContext.brands.length > 0 ? searchContext.brands : null,
        models: searchContext.models.length > 0 ? searchContext.models : null,
        samar_class_ids: searchContext.samarClassIds.length > 0 ? searchContext.samarClassIds : null,
        requirements: requirements
      };

      const { apiFetch } = await import('../lib/api');
      const res = await apiFetch('/api/scoring-search/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      } else {
        console.error('Search error', await res.text());
        setSearchResults([]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const progressPct = cacheProgress && cacheProgress.total > 0
    ? Math.round((cacheProgress.done / cacheProgress.total) * 100)
    : 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3, height: { md: 'calc(100vh - 120px)' } }}>
      {/* Left Column - Filters */}
      <Box sx={{ width: { xs: '100%', md: 560 }, flexShrink: 0, height: { xs: 'auto', md: '100%' } }}>
        <Paper elevation={2} sx={{ p: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ p: 2, background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)', color: 'primary.contrastText', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h6">Wyszukiwarka Ofert</Typography>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Zbuduj profil Idealnego Auta</Typography>
            </Box>
          </Box>
          <Divider />
          <Box sx={{ p: 0, flexGrow: 1, overflowY: 'auto' }}>
            <ScoringFilters 
              searchContext={searchContext}
              onContextChange={setSearchContext}
              selectedFeatures={selectedFeatures}
              onFeaturesChange={setSelectedFeatures}
              onTriggerSearch={handleSearch}
              isSearching={isSearching}
            />
          </Box>
        </Paper>
      </Box>

      {/* Right Column - Results */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Paper elevation={2} sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6">Wyniki Dopasowania ({searchResults.length})</Typography>
              {isSearching && <CircularProgress size={24} />}
            </Box>
            <Tooltip title="Przelicz w tle pojazdy bez wygenerowanej macierzy cen">
              <span>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={isRefreshing ? <CircularProgress size={16} /> : <CalculateIcon />}
                  onClick={handleRefreshMissing}
                  disabled={isSearching || isRefreshing}
                >
                  {isRefreshing ? 'Przeliczanie…' : 'Przelicz braki (LTR)'}
                </Button>
              </span>
            </Tooltip>
          </Box>

          {/* ── Progress Bar ── */}
          {cacheProgress && cacheProgress.status === 'running' && (
            <Box sx={{ px: 2, py: 1, bgcolor: 'action.hover' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="textSecondary">
                  Przeliczanie pojazdów: {cacheProgress.done} / {cacheProgress.total}
                </Typography>
                <Typography variant="caption" fontWeight={600} color="primary">
                  {progressPct}%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={progressPct}
                sx={{ height: 6, borderRadius: 3 }}
              />
            </Box>
          )}
          {cacheProgress && cacheProgress.status === 'done' && (
            <Box sx={{ px: 2, py: 1, bgcolor: 'success.light' }}>
              <Typography variant="caption" color="success.contrastText" fontWeight={600}>
                ✓ Przeliczono {cacheProgress.total} pojazdów — wyszukaj ponownie
              </Typography>
            </Box>
          )}

          <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto', bgcolor: 'background.default' }}>
            <ScoringResults results={searchResults} loading={isSearching} />
          </Box>
        </Paper>
      </Box>

      <Snackbar open={!!snackbarMessage} autoHideDuration={6000} onClose={() => setSnackbarMessage(null)}>
        <Alert onClose={() => setSnackbarMessage(null)} severity="info" sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};
