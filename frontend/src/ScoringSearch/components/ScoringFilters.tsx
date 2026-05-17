import React, { useState, useRef } from 'react';
import { Box, Button, Divider } from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import type { SearchContext, SelectedFeature, ScoredVehicle } from '../types';

import { useFilterDictionaries } from '../hooks/useFilterDictionaries';
import { useScoringFilterActions } from '../hooks/useScoringFilterActions';
import { useLiveFacets } from '../hooks/useLiveFacets';
import { Level1Primary } from './Filters/Level1Primary';
import { Level2Detailed } from './Filters/Level2Detailed';

interface ScoringFiltersProps {
  searchContext: SearchContext;
  onContextChange: (ctx: SearchContext) => void;
  selectedFeatures: SelectedFeature[];
  onFeaturesChange: (features: SelectedFeature[]) => void;
  searchResults: ScoredVehicle[];
}

export const ScoringFilters: React.FC<ScoringFiltersProps> = ({
  searchContext,
  onContextChange,
  selectedFeatures,
  onFeaturesChange,
  searchResults,
}) => {
  const [onLevel2, setOnLevel2] = useState(false);
  const level2Ref = useRef<HTMLDivElement>(null);

  const [l2Tab, setL2Tab] = useState<'universal' | 'dedicated'>('universal');
  const [universalSearch, setUniversalSearch] = useState('');
  const [dedicatedSearch, setDedicatedSearch] = useState('');

  const {
    initialData, loadingInitial,
    data, loadingFilters,
    trimsAndOptions, loadingTrims,
    sortedBrands, primaryEnumFacets, sortedBooleanGroups
  } = useFilterDictionaries({ searchContext, onLevel2 });

  const actions = useScoringFilterActions(
    searchContext, onContextChange,
    selectedFeatures, onFeaturesChange
  );

  const liveFacets = useLiveFacets(searchResults, initialData?.samar_classes ?? []);

  const handleLevel2Toggle = () => {
    setOnLevel2(prev => {
      const isOpening = !prev;
      if (isOpening) {
        setTimeout(() => {
          level2Ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
      return isOpening;
    });
  };

  const handleReset = () => {
    onContextChange({
      ...searchContext,
      brands: [], models: [], bodyTypes: [], trims: [],
      fuelTypes: [], transmissions: [], driveTypes: [], samarClassIds: [],
      margin_pct: undefined, monthly_budget: undefined,
      exact_mode: false, exact_duration_months: 36, exact_total_mileage: 60000,
    });
    onFeaturesChange([]);
  };

  return (
    <Box sx={{
      width: '100%', flexShrink: 0, bgcolor: '#ffffff',
      display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden'
    }}>
      {/* ── Sticky Header ── */}
      <Box sx={{
        p: 2, borderBottom: '1px solid #e2e8f0', bgcolor: '#f8fafc',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 10
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FilterListIcon sx={{ color: '#3b82f6', fontSize: 20 }} />
          <Box sx={{ fontWeight: 800, color: '#0f172a', fontSize: '0.9rem', letterSpacing: 0.5 }}>FILTRY</Box>
        </Box>
        <Button size="small" variant="text" color="inherit" onClick={handleReset} startIcon={<RestartAltIcon />} sx={{ opacity: 0.6, fontSize: '0.7rem', '&:hover': { opacity: 1 } }}>
          Reset
        </Button>
      </Box>

      {/* ── Scrollable Content ── */}
      <Box sx={{ flex: 1, overflowY: 'auto' }}>

        {/* ══ LEVEL 1 ══ */}
        <Level1Primary
          searchContext={searchContext}
          onContextChange={onContextChange}
          selectedFeatures={selectedFeatures}
          loadingInitial={loadingInitial}
          initialData={initialData}
          sortedBrands={sortedBrands}
          loadingTrims={loadingTrims}
          trimsAndOptions={trimsAndOptions}
          loadingFilters={loadingFilters}
          primaryEnumFacets={primaryEnumFacets}
          liveFacets={liveFacets}
          {...actions}
        />

        {/* ══ Transition to LEVEL 2 ══ */}
        <Divider sx={{ my: 0 }} />
        <Button
          fullWidth
          onClick={handleLevel2Toggle}
          endIcon={onLevel2 ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          sx={{
            py: 1.5, borderRadius: 0, justifyContent: 'space-between', px: 2,
            color: onLevel2 ? '#7c3aed' : '#64748b', fontWeight: 700,
            bgcolor: onLevel2 ? '#fafafe' : '#ffffff', borderBottom: onLevel2 ? '2px solid #7c3aed' : 'none',
            '&:hover': { bgcolor: '#f1f5f9' }
          }}
        >
          Więcej filtrów
        </Button>

        {/* ══ LEVEL 2 ══ */}
        {onLevel2 && (
          <Level2Detailed
            level2Ref={level2Ref}
            l2Tab={l2Tab} setL2Tab={setL2Tab}
            universalSearch={universalSearch} setUniversalSearch={setUniversalSearch}
            dedicatedSearch={dedicatedSearch} setDedicatedSearch={setDedicatedSearch}
            loadingFilters={loadingFilters}
            loadingTrims={loadingTrims}
            sortedBooleanGroups={sortedBooleanGroups}
            data={data}
            trimsAndOptions={trimsAndOptions}
            selectedFeatures={selectedFeatures}
            {...actions}
          />
        )}
      </Box>
    </Box>
  );
};
