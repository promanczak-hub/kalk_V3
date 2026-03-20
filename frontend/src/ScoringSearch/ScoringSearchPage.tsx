import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  Box, Paper, Typography, Divider, CircularProgress,
  Snackbar, Alert
} from '@mui/material';
import { ScoringFilters } from './components/ScoringFilters';
import { ScoringResults } from './components/ScoringResults';
import type { SelectedFeature, SearchContext, ScoredVehicle } from './types';



export const ScoringSearchPage: React.FC = () => {
  const [searchContext, setSearchContext] = useState<SearchContext>({
    brands: [],
    models: [],
    trims: [],
    samarClassIds: [],
    bodyTypes: [],
    useMatrixFilters: false,
    duration_months_range: [24, 48],
    total_mileage_range: [60000, 140000],
    exact_mode: true,
    exact_duration_months: 48,
    exact_total_mileage: 80000,
    margin_pct: 10,
    monthly_budget: undefined,
  });
  
  const [selectedFeatures, setSelectedFeatures] = useState<SelectedFeature[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<ScoredVehicle[]>([]);
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up on unmount
  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
  }, []);

  // ── Auto-search with debounce on every filter change ──
  // Stringify only the fields that affect results to avoid reference churn
  const searchKey = useMemo(
    () => JSON.stringify({ searchContext, selectedFeatures }),
    [searchContext, selectedFeatures]
  );

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      handleSearch();
    }, 600);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchKey]);



  // Function to execute the search
  const handleSearch = async () => {
    setIsSearching(true);
    try {
      // Build requirements payload out of selectedFeatures and context
      const requirements = [...selectedFeatures];
      
      // Apply matrix filters only if the toggle is enabled
      if (searchContext.useMatrixFilters) {
        let searchDurationMin = searchContext.duration_months_range[0];
        let searchDurationMax = searchContext.duration_months_range[1];
        const targetDurationForAnnualMin = searchDurationMax; // To get minimum annual, divide by max duration
        const targetDurationForAnnualMax = searchDurationMin; // To get maximum annual, divide by min duration
        let searchAnnualMin = Math.max(10000, Math.round((searchContext.total_mileage_range[0] * 12) / targetDurationForAnnualMin));
        let searchAnnualMax = Math.min(80000, Math.round((searchContext.total_mileage_range[1] * 12) / targetDurationForAnnualMax));

        if (searchContext.exact_mode) {
           const d = searchContext.exact_duration_months;
           if (d <= 24) { searchDurationMin = 24; searchDurationMax = 24; }
           else if (d <= 36) { searchDurationMin = 24; searchDurationMax = 36; }
           else if (d <= 48) { searchDurationMin = 36; searchDurationMax = 48; }
           else { searchDurationMin = 48; searchDurationMax = 60; }
           
           const annual = Math.round((searchContext.exact_total_mileage * 12) / d);
           const bucket = Math.round(annual / 5000) * 5000;
           searchAnnualMin = Math.max(10000, bucket - 5000);
           searchAnnualMax = Math.min(80000, bucket + 5000);
        }

        // Duration range (gte + lte pair)
        requirements.push({ feature_key: 'duration_months', operator: 'gte', value: searchDurationMin, requirement: 'MUST_HAVE', weight: 1 });
        requirements.push({ feature_key: 'duration_months', operator: 'lte', value: searchDurationMax, requirement: 'MUST_HAVE', weight: 1 });
        // Mileage range (gte + lte pair)
        requirements.push({ feature_key: 'annual_mileage', operator: 'gte', value: searchAnnualMin, requirement: 'MUST_HAVE', weight: 1 });
        requirements.push({ feature_key: 'annual_mileage', operator: 'lte', value: searchAnnualMax, requirement: 'MUST_HAVE', weight: 1 });
        
        if (searchContext.margin_pct !== undefined) {
          requirements.push({ feature_key: 'margin_pct', operator: 'gte', value: searchContext.margin_pct, requirement: 'MUST_HAVE', weight: 1 });
        }
        if (searchContext.monthly_budget) {
          requirements.push({ feature_key: 'monthly_price_net', operator: 'lte', value: searchContext.monthly_budget, requirement: 'MUST_HAVE', weight: 1 });
        }
      }

      // Body type filter — każdy wybrany typ jako osobna cecha MUST_HAVE
      if (searchContext.bodyTypes.length > 0) {
        for (const bt of searchContext.bodyTypes) {
          requirements.push({
            feature_key: 'body_style',
            operator: 'eq',
            value: bt,
            requirement: 'MUST_HAVE',
            weight: 1
          });
        }
      }

      const payload = {
        brands: searchContext.brands.length > 0 ? searchContext.brands : null,
        models: searchContext.models.length > 0 ? searchContext.models : null,
        trims: searchContext.trims.length > 0 ? searchContext.trims : null,
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
          </Box>

          <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto', bgcolor: 'background.default' }}>
            <ScoringResults results={searchResults} loading={isSearching} searchContext={searchContext} />
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
