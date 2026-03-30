import React, { useMemo, useState } from 'react';
import { Box, Typography, FormControl, Select, MenuItem } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import type { SearchContext } from '../types';
import { useBatchPrices, useBatchSimilarVehicles } from '../hooks/useBatchData';
import { VehicleResultCard } from './Results/VehicleResultCard';
import { MATRIX_LIMITS } from '../../config/matrixLimits';

export type SortOption = 'score_desc' | 'price_asc' | 'price_desc' | 'brand_asc';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'score_desc', label: 'Dopasowanie ↓' },
  { value: 'price_asc', label: 'Cena ↑ (najtańsze)' },
  { value: 'price_desc', label: 'Cena ↓ (najdroższe)' },
  { value: 'brand_asc', label: 'Marka A-Z' },
];

interface ScoringResultsProps {
  results: Record<string, unknown>[];
  loading: boolean;
  searchContext: SearchContext;
}

export const ScoringResults: React.FC<ScoringResultsProps> = ({ results, loading, searchContext }) => {
  console.log("SCORING_RESULTS_RENDERED", { resultsCount: results.length, loading, useMatrix: searchContext.useMatrixFilters });
  const [sortBy, setSortBy] = useState<SortOption>('score_desc');
  const [similarityMode, setSimilarityMode] = useState<'rule-based' | 'semantic'>('rule-based');

  let searchDurationMin = searchContext.duration_months_range[0];
  let searchDurationMax = searchContext.duration_months_range[1];
  const targetDurationForAnnualMin = searchDurationMax;
  const targetDurationForAnnualMax = searchDurationMin;
  let searchAnnualMin = Math.max(10000, Math.round((searchContext.total_mileage_range[0] * 12) / targetDurationForAnnualMin));
  let searchAnnualMax = Math.min(MATRIX_LIMITS.KM_MAX_ANNUAL, Math.round((searchContext.total_mileage_range[1] * 12) / targetDurationForAnnualMax));

  if (searchContext.exact_mode) {
    const d = searchContext.exact_duration_months;
    searchDurationMin = d;
    searchDurationMax = d;
    
    const annual = Math.round((searchContext.exact_total_mileage * 12) / d);
    const bucket = Math.round(annual / 2500) * 2500;
    searchAnnualMin = Math.max(MATRIX_LIMITS.KM_MIN_ANNUAL, Math.min(MATRIX_LIMITS.KM_MAX_ANNUAL, bucket));
    searchAnnualMax = searchAnnualMin;
  }

  // Calculate generic targets for similar vehicles and fallback scenarios
  const targetDuration = Math.round((searchDurationMin + searchDurationMax) / 2);
  const selectedMileage = searchContext.exact_mode ? searchContext.exact_total_mileage : Math.round((searchContext.total_mileage_range[0] + searchContext.total_mileage_range[1]) / 2);
  const targetAnnualMileage = Math.round((selectedMileage * 12) / targetDuration);

  // Zoptymalizowane zbieranie cen w locie używając 1 wsadowego żądania HTTP 
  const vehicleIdsToFetchPrices = useMemo(() => {
    return results.map(r => r.vehicle_id as string).filter(Boolean);
  }, [results]);

  // Pobieramy ceny TYLKO gdy filtry Matrix są aktywne — efekt celowy,
  // by nie pokazywać losowej ceny dla arbitralnych parametrów
  const matrixFiltersActive = searchContext.useMatrixFilters;

  const { prices: batchPrices, loading: batchPricesLoading } = useBatchPrices(
    vehicleIdsToFetchPrices, searchDurationMin, searchDurationMax, searchAnnualMin, searchAnnualMax,
    results.length > 0 && matrixFiltersActive,
  );
  
  const { similarVehicles: batchSimilar } = useBatchSimilarVehicles(
    vehicleIdsToFetchPrices,
    targetDuration,
    targetAnnualMileage,
    results.length > 0, // ZAWSZE POZWÓL NA ŁADOWANIE PODOBNYCH (nie wymagaj matrixFiltersActive)
    similarityMode
  );

  const sortedResults = useMemo(() => {
    const sorted = [...results];
    switch (sortBy) {
      case 'score_desc':
        sorted.sort((a, b) => ((b.match_score_pct as number) || 0) - ((a.match_score_pct as number) || 0));
        break;
      case 'price_asc':
        sorted.sort((a, b) => {
          const pa = (a.best_monthly_price as number) || Infinity;
          const pb = (b.best_monthly_price as number) || Infinity;
          return pa - pb;
        });
        break;
      case 'price_desc':
        sorted.sort((a, b) => {
          const pa = (a.best_monthly_price as number) || 0;
          const pb = (b.best_monthly_price as number) || 0;
          return pb - pa;
        });
        break;
      case 'brand_asc':
        sorted.sort((a, b) => ((a.brand as string) || '').localeCompare((b.brand as string) || '', 'pl'));
        break;
    }
    return sorted;
  }, [results, sortBy]);

  if (loading) {
    return <Typography sx={{ p: 2 }}>Wyszukiwanie najlepszych ofert...</Typography>;
  }

  if (results.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="textSecondary">Brak wyników</Typography>
        <Typography variant="body2" color="textSecondary">Zmień filtry lub budżet, aby znaleźć pasujące pojazdy.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* DEBUG MARKER - IF YOU SEE THIS, THE NEW AI CODE IS ACTIVE */}
      <Box sx={{ bgcolor: 'red', color: 'white', p: 1, textAlign: 'center', fontWeight: 'bold', mb: 2, borderRadius: 1 }}>
        AI SIMILARITY FEATURE ACTIVE (DEBUG)
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Wyniki Dopasowania ({results.length})
        </Typography>
      </Box>

      {/* Sort Toolbar */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="caption" color="textSecondary">Podobne (Alternatywy):</Typography>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <Select
              value={similarityMode}
              onChange={(e: SelectChangeEvent) => setSimilarityMode(e.target.value as 'rule-based' | 'semantic')}
              sx={{ fontSize: '0.8rem' }}
            >
              <MenuItem value="rule-based">W tej klasie (⚙️)</MenuItem>
              <MenuItem value="semantic">Inteligentne (AI ✨)</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="caption" color="textSecondary">Sortuj:</Typography>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <Select
              value={sortBy}
              onChange={(e: SelectChangeEvent) => setSortBy(e.target.value as SortOption)}
              sx={{ fontSize: '0.85rem' }}
            >
              {SORT_OPTIONS.map(opt => (
                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Box>

      {/* Results mapped to isolated Card Component */}
      {sortedResults.map((car) => {
        const vehicleId = car.vehicle_id as string;
        
        return (
          <VehicleResultCard 
            key={vehicleId}
            car={car}
            searchContext={searchContext}
            targetDuration={targetDuration}
            targetAnnualMileage={targetAnnualMileage}
            priceData={batchPrices[vehicleId]}
            pricesLoading={batchPricesLoading}
            similarData={batchSimilar[vehicleId]}
          />
        );
      })}
    </Box>
  );
};
