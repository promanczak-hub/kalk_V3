import React, { useEffect, useState, useMemo } from 'react';
import {
  Box, Typography, CircularProgress, Accordion, AccordionSummary, AccordionDetails,
  FormGroup, FormControlLabel, Checkbox, Button, TextField, Autocomplete, Chip, Slider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { apiFetch } from '../../lib/api';
import type { AvailableFiltersResponse, SearchContext, SelectedFeature, EnumFilter, InitialDataResponse } from '../types';

interface ScoringFiltersProps {
  searchContext: SearchContext;
  onContextChange: (ctx: SearchContext) => void;
  selectedFeatures: SelectedFeature[];
  onFeaturesChange: (features: SelectedFeature[]) => void;
  onTriggerSearch: () => void;
  isSearching: boolean;
}

export const ScoringFilters: React.FC<ScoringFiltersProps> = ({
  searchContext, onContextChange, selectedFeatures, onFeaturesChange, onTriggerSearch, isSearching
}) => {
  const [loadingInitial, setLoadingInitial] = useState(false);
  const [initialData, setInitialData] = useState<InitialDataResponse | null>(null);

  const [loadingFilters, setLoadingFilters] = useState(false);
  const [data, setData] = useState<AvailableFiltersResponse | null>(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoadingInitial(true);
      try {
        const res = await apiFetch('/api/scoring-search/initial-data', { method: 'GET' });
        if (res.ok) {
          const json = await res.json();
          setInitialData(json.data || json);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingInitial(false);
      }
    };
    fetchInitialData();
  }, []);

  useEffect(() => {
    fetchFilters();
  }, [
    searchContext.brands.length,
    searchContext.models.length,
    searchContext.samarClassIds.length
  ]);

  const fetchFilters = async () => {
    setLoadingFilters(true);
    try {
      const payload = {
        brands: searchContext.brands.length > 0 ? searchContext.brands : null,
        models: searchContext.models.length > 0 ? searchContext.models : null,
        samar_class_ids: searchContext.samarClassIds.length > 0 ? searchContext.samarClassIds : null,
      };
      const res = await apiFetch('/api/scoring-search/available-filters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const json = await res.json();
        setData(json.data || json);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingFilters(false);
    }
  };

  // ── Brands sorted by count descending ──
  const sortedBrands = useMemo(() => {
    if (!initialData?.brands) return [];
    const counts = initialData.brand_counts || {};
    return [...initialData.brands].sort((a, b) => (counts[b] || 0) - (counts[a] || 0));
  }, [initialData]);

  const toggleBrand = (brand: string) => {
    const current = searchContext.brands;
    const next = current.includes(brand)
      ? current.filter(b => b !== brand)
      : [...current, brand];
    onContextChange({ ...searchContext, brands: next, models: [] });
  };

  // ── Extract primary enum facets (napęd, etc.) from facet_groups ──
  const primaryEnumFacets = useMemo(() => {
    if (!data?.facet_groups) return [];
    const facets: EnumFilter[] = [];
    for (const group of data.facet_groups) {
      for (const filter of group.filters) {
        if (filter.items && filter.items.length > 0) {
          facets.push(filter);
        }
      }
    }
    return facets;
  }, [data]);

  const isFeatureSelected = (key: string, value: string) => {
    return selectedFeatures.some(f => f.feature_key === key && f.value === value);
  };

  const toggleFeature = (key: string, value: string, weight: number = 1, isMustHave: boolean = false) => {
    const existing = selectedFeatures.findIndex(f => f.feature_key === key && f.value === value);
    if (existing >= 0) {
      const clone = [...selectedFeatures];
      clone.splice(existing, 1);
      onFeaturesChange(clone);
    } else {
      onFeaturesChange([...selectedFeatures, {
        feature_key: key,
        operator: 'eq',
        value,
        requirement: isMustHave ? 'MUST_HAVE' : 'NICE_TO_HAVE',
        weight
      }]);
    }
  };

  // Chip styling — handled globally via MuiChip theme override

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* ── Section 1: Brands ── */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', bgcolor: '#f9fafb' }}>
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold', color: 'text.secondary', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Marka
        </Typography>
        {loadingInitial ? (
          <CircularProgress size={20} />
        ) : (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {sortedBrands.map(brand => {
              const count = initialData?.brand_counts?.[brand] || 0;
              const selected = searchContext.brands.includes(brand);
              return (
                <Chip
                  key={brand}
                  label={`${brand} (${count})`}
                  size="small"
                  color={selected ? 'primary' : 'default'}
                  variant={selected ? 'filled' : 'outlined'}
                  onClick={() => toggleBrand(brand)}
                  sx={{ cursor: 'pointer' }}
                />
              );
            })}
          </Box>
        )}
      </Box>

      {/* ── Section 2: Models (conditional) ── */}
      {searchContext.brands.length > 0 && (
        <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #e0e0e0', bgcolor: '#fafbfc' }}>
          <Typography variant="subtitle2" sx={{ mb: 0.75, fontWeight: 'bold', color: 'text.secondary', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Model
          </Typography>
          <Autocomplete
            multiple
            size="small"
            options={
              Array.from(new Set(searchContext.brands.flatMap(b => initialData?.brand_model_map?.[b] || []))).sort()
            }
            value={searchContext.models}
            onChange={(_, newVal) => onContextChange({ ...searchContext, models: newVal })}
            renderInput={(params) => <TextField {...params} placeholder="Wybierz modele..." />}
          />
        </Box>
      )}

      {/* ── Section 3: Primary Enum Facets (Napęd, etc.) ── */}
      {!loadingFilters && primaryEnumFacets.length > 0 && (
        <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #e0e0e0', bgcolor: '#f9fafb' }}>
          {primaryEnumFacets.map(facet => (
            <Box key={facet.key} sx={{ mb: 1 }}>
              <Typography variant="subtitle2" sx={{ mb: 0.75, fontWeight: 'bold', color: 'text.secondary', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                {facet.name}
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                {facet.items.map(item => {
                  const selected = isFeatureSelected(facet.key, item.value);
                  return (
                    <Chip
                      key={item.value}
                      label={`${item.value} (${item.count})`}
                      size="small"
                      color={selected ? 'secondary' : 'default'}
                      variant={selected ? 'filled' : 'outlined'}
                      onClick={() => toggleFeature(facet.key, item.value, 1, false)}
                      sx={{ cursor: 'pointer' }}
                    />
                  );
                })}
              </Box>
            </Box>
          ))}
        </Box>
      )}

      {/* ── Section 4: Samar Classes ── */}
      {!loadingInitial && (
        <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #e0e0e0', bgcolor: '#fafbfc' }}>
          <Typography variant="subtitle2" sx={{ mb: 0.75, fontWeight: 'bold', color: 'text.secondary', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Klasa Samar
          </Typography>
          <Autocomplete
            multiple
            size="small"
            options={initialData?.samar_classes || []}
            getOptionLabel={(opt) => opt.name}
            value={initialData?.samar_classes.filter(c => searchContext.samarClassIds.includes(c.id)) || []}
            onChange={(_, newVal) => onContextChange({ ...searchContext, samarClassIds: newVal.map(v => v.id) })}
            renderInput={(params) => <TextField {...params} placeholder="Wybierz klasy..." />}
          />
        </Box>
      )}

      {/* ── Section 5: Numeric params ── */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #e0e0e0', bgcolor: '#f9fafb' }}>
        <Typography variant="subtitle2" sx={{ mb: 0.75, fontWeight: 'bold', color: 'text.secondary', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Parametry
        </Typography>

        {/* ── Duration range slider ── */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: -0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
              Okres (m-ce)
            </Typography>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
              {searchContext.duration_months_range[0]}–{searchContext.duration_months_range[1]} mc
            </Typography>
          </Box>
          <Slider
            value={searchContext.duration_months_range}
            onChange={(_, val) => {
              const v = val as [number, number];
              onContextChange({ ...searchContext, duration_months_range: v });
            }}
            min={12}
            max={60}
            step={6}
            marks={[12, 18, 24, 30, 36, 42, 48, 54, 60].map(v => ({ value: v, label: String(v) }))}
            valueLabelDisplay="auto"
            disableSwap
            sx={{ mt: 1, '& .MuiSlider-markLabel': { fontSize: '0.65rem' } }}
          />
        </Box>

        {/* ── Mileage range slider ── */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: -0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
              Przebieg roczny (km)
            </Typography>
            <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
              {(searchContext.annual_mileage_range[0] / 1000).toFixed(0)}k–{(searchContext.annual_mileage_range[1] / 1000).toFixed(0)}k km
            </Typography>
          </Box>
          <Slider
            value={searchContext.annual_mileage_range}
            onChange={(_, val) => {
              const v = val as [number, number];
              onContextChange({ ...searchContext, annual_mileage_range: v });
            }}
            min={10000}
            max={40000}
            step={5000}
            marks={[10000, 15000, 20000, 25000, 30000, 35000, 40000].map(v => ({ value: v, label: `${v / 1000}k` }))}
            valueLabelDisplay="auto"
            valueLabelFormat={(v) => `${(v / 1000).toFixed(0)}k`}
            disableSwap
            sx={{ mt: 1, '& .MuiSlider-markLabel': { fontSize: '0.65rem' } }}
          />
        </Box>

        {/* ── Remaining numeric fields ── */}
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
          <TextField
            label="Marża min (%)"
            type="number"
            size="small"
            value={searchContext.margin_pct}
            onChange={(e) => onContextChange({ ...searchContext, margin_pct: parseFloat(e.target.value) || 0 })}
          />
          <TextField
            label="Max Rata (Netto)"
            type="number"
            size="small"
            value={searchContext.monthly_budget || ''}
            onChange={(e) => onContextChange({ ...searchContext, monthly_budget: parseInt(e.target.value) || undefined })}
          />
        </Box>
      </Box>

      {/* ── Search Button ── */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #e0e0e0' }}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={onTriggerSearch}
          disabled={isSearching}
          sx={{ fontWeight: 'bold', py: 1.2 }}
        >
          {isSearching ? 'Wyszukiwanie...' : 'Szukaj Ofert'}
        </Button>
      </Box>

      {/* ── Section 6: Feature Tree (Nice to have) ── */}
      <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
        <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 'bold', color: 'text.secondary', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Wymagania (Nice to have)
        </Typography>
        {loadingFilters ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : !data || (!data.facet_groups?.length && !data.boolean_filters?.length) ? (
          <Typography variant="body2" color="textSecondary">Wybierz pojazdy, aby załadować cechy.</Typography>
        ) : (
          <Box>
            {/* Render Boolean Facets (Ontology Features) */}
            {data.boolean_filters && Array.from(new Set(data.boolean_filters.map(f => f.group_name))).map((groupName) => {
              const groupFilters = data.boolean_filters!.filter(f => f.group_name === groupName);
              if (groupFilters.length === 0) return null;

              return (
                <Accordion key={`bool-${groupName}`} disableGutters>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography sx={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>{groupName.replace(/_/g, ' ')}</Typography>
                  </AccordionSummary>
                  <AccordionDetails sx={{ p: '8px 16px' }}>
                    <FormGroup sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
                      {groupFilters.map((filter) => (
                        <FormControlLabel
                          key={filter.feature_key}
                          control={
                            <Checkbox
                              size="small"
                              checked={isFeatureSelected(filter.feature_key, 'true')}
                              onChange={() => toggleFeature(filter.feature_key, 'true', 1, false)}
                            />
                          }
                          label={<Typography variant="body2" noWrap>{filter.feature_name || filter.feature_key.replace(/_/g, ' ')} ({filter.cnt})</Typography>}
                          sx={{ '& .MuiFormControlLabel-label': { fontSize: '0.8rem' }, m: 0 }}
                        />
                      ))}
                    </FormGroup>
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </Box>
        )}
      </Box>
    </Box>
  );
};
