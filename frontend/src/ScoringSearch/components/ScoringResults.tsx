import React, { useMemo, useState } from 'react';
import { Box, Typography, FormControl, Select, MenuItem } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import type { SearchContext, SelectedFeature, ScoredVehicle } from '../types';
import { useBatchPrices, useBatchSimilarVehicles } from '../hooks/useBatchData';
import { VehicleResultCard } from './Results/VehicleResultCard';
import { computeSearchRanges } from '../utils/computeSearchRanges';

export type SortOption = 'budget_margin_desc' | 'score_desc' | 'price_asc' | 'price_desc' | 'brand_asc';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'budget_margin_desc', label: 'Marża dopasowana ↓ (najlepsze)' },
  { value: 'score_desc', label: 'Dopasowanie ↓' },
  { value: 'price_asc', label: 'Cena ↑ (najtańsze)' },
  { value: 'price_desc', label: 'Cena ↓ (najdroższe)' },
  { value: 'brand_asc', label: 'Marka A-Z' },
];

interface ScoringResultsProps {
  results: ScoredVehicle[];
  loading: boolean;
  searchContext: SearchContext;
  selectedFeatures: SelectedFeature[];
  requirements: SelectedFeature[];
}

export const ScoringResults: React.FC<ScoringResultsProps> = ({ results, loading, searchContext, requirements }) => {
  // Default sort = "Marża dopasowana" when matrix+budget is active (best business deal first),
  // otherwise = "Dopasowanie" (cech-based score).
  const matrixActive = searchContext.useMatrixFilters && !!searchContext.monthly_budget;
  const [sortBy, setSortBy] = useState<SortOption>(
    matrixActive ? 'budget_margin_desc' : 'score_desc',
  );
  const similarityMode = 'semantic';

  const {
    searchDurationMin,
    searchDurationMax,
    searchAnnualMin,
    searchAnnualMax,
    targetDuration,
    targetAnnualMileage
  } = computeSearchRanges(searchContext);


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
    similarityMode,
    requirements
  );

  const sortedResults = useMemo(() => {
    const sorted = [...results];
    switch (sortBy) {
      case 'budget_margin_desc':
        // Highest applied_margin_pct first (best business deal in budget).
        // Cars without applied_margin_pct fall to the end (treated as -Infinity).
        sorted.sort((a, b) => {
          const ma = (a.applied_margin_pct as number | undefined) ?? -Infinity;
          const mb = (b.applied_margin_pct as number | undefined) ?? -Infinity;
          return mb - ma;
        });
        break;
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
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>

      {/* Sort Toolbar */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 2 }}>
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

      {/* Results mapped to isolated Card Component.
          When a vehicle has pinned calculations (multi-select on Ekstrakcja),
          we render one card per pinned calc — each fetches its own price.
          No pins → one default card backed by the batch-prices result. */}
      {sortedResults.flatMap((car) => {
        const vehicleId = car.vehicle_id as string;
        const pinned = car.selected_kalkulacja_ids ?? [];

        if (pinned.length === 0) {
          return [
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
          ];
        }

        return pinned.map((kid) => (
          <VehicleResultCard
            key={`${vehicleId}_${kid}`}
            car={car}
            searchContext={searchContext}
            targetDuration={targetDuration}
            targetAnnualMileage={targetAnnualMileage}
            priceData={batchPrices[vehicleId]}
            pricesLoading={batchPricesLoading}
            similarData={batchSimilar[vehicleId]}
            pinnedKalkulacjaId={kid}
          />
        ));
      })}
    </Box>
  );
};
