import React from 'react';
import {
  Box, Typography, CircularProgress, FormGroup, FormControlLabel,
  Checkbox, TextField, Tabs, Tab, Slider
} from '@mui/material';
import { SectionLabel, OptionsChecklist } from './FilterUIComponents';
import type { SelectedFeature, AvailableFiltersResponse, TrimsAndOptionsResponse, BooleanFilter } from '../../types';

interface Level2DetailedProps {
  level2Ref: React.RefObject<HTMLDivElement | null>;
  l2Tab: 'universal' | 'dedicated';
  setL2Tab: (val: 'universal' | 'dedicated') => void;
  
  universalSearch: string;
  setUniversalSearch: (val: string) => void;
  stdOptionSearch: string;
  setStdOptionSearch: (val: string) => void;
  paidOptionSearch: string;
  setPaidOptionSearch: (val: string) => void;
  
  loadingFilters: boolean;
  sortedBooleanGroups: { groupName: string, filters: BooleanFilter[], totalCount: number }[];
  data: AvailableFiltersResponse | null;
  trimsAndOptions: TrimsAndOptionsResponse | null;
  
  selectedFeatures: SelectedFeature[];
  
  // Actions
  updateRangeFeature: (key: string, val: [number, number], minLimit: number, maxLimit: number) => void;
  toggleFeature: (key: string, value: string, weight?: number, isMustHave?: boolean) => void;
  isFeatureSelected: (key: string, value: string) => boolean;
  isOptionSelected: (prefix: string, name: string) => boolean;
  toggleOption: (prefix: string, name: string) => void;
}

export const Level2Detailed: React.FC<Level2DetailedProps> = ({
  level2Ref, l2Tab, setL2Tab,
  universalSearch, setUniversalSearch,
  stdOptionSearch, setStdOptionSearch,
  paidOptionSearch, setPaidOptionSearch,
  loadingFilters, sortedBooleanGroups, data, trimsAndOptions,
  selectedFeatures,
  updateRangeFeature, toggleFeature, isFeatureSelected, isOptionSelected, toggleOption
}) => {
  return (
    <Box ref={level2Ref} sx={{ p: 2, bgcolor: '#fafafe' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs 
          value={l2Tab} 
          onChange={(_, newValue) => setL2Tab(newValue)} 
          variant="fullWidth"
          sx={{
            minHeight: 40,
            '& .MuiTab-root': {
              py: 1,
              minHeight: 40,
              fontSize: '0.8rem',
              fontWeight: 600,
              textTransform: 'none'
            }
          }}
        >
          <Tab label="Cechy uniwersalne" value="universal" />
          <Tab label="Cechy dedykowane" value="dedicated" />
        </Tabs>
      </Box>

      {l2Tab === 'universal' && (
        <Box>
          {loadingFilters ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
          ) : sortedBooleanGroups.length === 0 && (data?.range_filters?.length ?? 0) === 0 ? (
            <Typography variant="body2" color="textSecondary" sx={{ textAlign: 'center', py: 3, color: '#94a3b8' }}>
              Wybierz markę, model lub typ nadwozia, aby załadować cechy uniwersalne.
            </Typography>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <TextField
                size="small"
                fullWidth
                placeholder="Szukaj w cechach uniwersalnych..."
                value={universalSearch}
                onChange={e => setUniversalSearch(e.target.value)}
                sx={{ mb: 2, bgcolor: '#ffffff' }}
              />

              {/* ── Range Filters ── */}
              {data?.range_filters && data.range_filters.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  {data.range_filters.map(filter => {
                    if (universalSearch && !filter.feature_name.toLowerCase().includes(universalSearch.toLowerCase()) && !filter.feature_key.toLowerCase().includes(universalSearch.toLowerCase())) return null;

                    const currentMin = selectedFeatures.find(f => f.feature_key === filter.feature_key && f.operator === 'gte')?.value as number ?? filter.min_val;
                    const currentMax = selectedFeatures.find(f => f.feature_key === filter.feature_key && f.operator === 'lte')?.value as number ?? filter.max_val;

                    const spread = filter.max_val - filter.min_val;
                    const rangeStep = spread > 1000 ? 10 : (spread > 100 ? 5 : 1);

                    return (
                      <Box key={filter.feature_key} sx={{ mb: 2, pl: 0.5, pr: 1.5 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: -0.5 }}>
                          <Typography variant="body2" sx={{ fontSize: '0.78rem', color: '#475569', fontWeight: 600 }}>
                            {filter.feature_name || filter.feature_key.replace(/_/g, ' ')}
                          </Typography>
                          <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
                            {currentMin} – {currentMax}
                          </Typography>
                        </Box>
                        <Slider
                          value={[currentMin, currentMax]}
                          onChange={(_, val) => updateRangeFeature(filter.feature_key, val as [number, number], filter.min_val, filter.max_val)}
                          min={filter.min_val}
                          max={filter.max_val}
                          step={rangeStep}
                          disableSwap
                          sx={{ mt: 1, '& .MuiSlider-thumb': { width: 16, height: 16 } }}
                        />
                      </Box>
                    );
                  })}
                </Box>
              )}
              
              {sortedBooleanGroups.map(({ groupName, filters }) => {
                const filteredFilters = filters.filter(f => 
                  (f.feature_name || f.feature_key.replace(/_/g, ' ')).toLowerCase().includes(universalSearch.toLowerCase())
                );
                if (filteredFilters.length === 0) return null;

                const groupSelected = filteredFilters.filter(f => isFeatureSelected(f.feature_key, 'true')).length;

                return (
                  <Box key={`bool-${groupName}`} sx={{ mb: 3 }}>
                    <SectionLabel label={groupName.replace(/_/g, ' ')} selectedCount={groupSelected} />
                    <FormGroup>
                      {filteredFilters.map((filter) => {
                        const isSel = isFeatureSelected(filter.feature_key, 'true');
                        return (
                          <FormControlLabel
                            key={filter.feature_key}
                            control={
                              <Checkbox
                                size="small"
                                checked={isSel}
                                onChange={() => toggleFeature(filter.feature_key, 'true', 1, false)}
                                sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#3b82f6' }, py: 0.3 }}
                              />
                            }
                            label={
                              <Typography variant="body2" sx={{ fontSize: '0.78rem', color: isSel ? '#1e40af' : '#475569', fontWeight: isSel ? 600 : 400 }}>
                                {filter.feature_name || filter.feature_key.replace(/_/g, ' ')}
                                <Box component="span" sx={{ color: '#94a3b8', ml: 0.5, fontSize: '0.72rem', fontWeight: 400 }}>({filter.cnt})</Box>
                              </Typography>
                            }
                            sx={{ m: 0, alignItems: 'flex-start' }}
                          />
                        );
                      })}
                    </FormGroup>
                  </Box>
                );
              })}
            </Box>
          )}
        </Box>
      )}

      {l2Tab === 'dedicated' && (
        <Box>
          {/* ── Standard equipment options ── */}
          {(!trimsAndOptions || ((trimsAndOptions.standard_options || []).length === 0 && (trimsAndOptions.paid_options || []).length === 0)) ? (
            <Typography variant="body2" color="textSecondary" sx={{ textAlign: 'center', py: 3, color: '#94a3b8' }}>
              Wybierz model, aby załadować cechy dedykowane (wyposażenie).
            </Typography>
          ) : (
            <>
              {(trimsAndOptions?.standard_options || []).length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <SectionLabel
                    label="Wyposażenie standardowe"
                    selectedCount={selectedFeatures.filter(f => f.feature_key.startsWith('opt_std:')).length}
                  />
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="Szukaj wyposażenia standardowego..."
                    value={stdOptionSearch}
                    onChange={e => setStdOptionSearch(e.target.value)}
                    sx={{ mb: 1, bgcolor: '#ffffff' }}
                  />
                  <OptionsChecklist
                    items={(trimsAndOptions?.standard_options || []).filter(
                      o => o.name.toLowerCase().includes(stdOptionSearch.toLowerCase())
                    )}
                    prefix="opt_std:"
                    selectedFeatures={selectedFeatures}
                    isSelected={isOptionSelected}
                    onToggle={toggleOption}
                  />
                </Box>
              )}

              {/* ── Paid options ── */}
              {(trimsAndOptions?.paid_options || []).length > 0 && (
                <Box>
                  <SectionLabel
                    label="Opcje dodatkowe (płatne)"
                    selectedCount={selectedFeatures.filter(f => f.feature_key.startsWith('opt_paid:')).length}
                  />
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="Szukaj opcji dodatkowych..."
                    value={paidOptionSearch}
                    onChange={e => setPaidOptionSearch(e.target.value)}
                    sx={{ mb: 1, bgcolor: '#ffffff' }}
                  />
                  <OptionsChecklist
                    items={(trimsAndOptions?.paid_options || []).filter(
                      o => o.name.toLowerCase().includes(paidOptionSearch.toLowerCase())
                    )}
                    prefix="opt_paid:"
                    selectedFeatures={selectedFeatures}
                    isSelected={isOptionSelected}
                    onToggle={toggleOption}
                  />
                </Box>
              )}
            </>
          )}
        </Box>
      )}
    </Box>
  );
};
