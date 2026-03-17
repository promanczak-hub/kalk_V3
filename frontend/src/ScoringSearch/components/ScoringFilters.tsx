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

// ── Reusable styled chip ──────────────────────────────────────────────────────
const FilterChip: React.FC<{
  label: string;
  selected: boolean;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
}> = ({ label, selected, onClick, variant = 'primary' }) => {
  const selectedBg =
    variant === 'secondary'
      ? 'linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)'
      : 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)';

  return (
    <Chip
      label={label}
      size="small"
      onClick={onClick}
      sx={{
        cursor: 'pointer',
        fontWeight: selected ? 700 : 400,
        fontSize: '0.75rem',
        height: 26,
        transition: 'all 0.15s ease',
        background: selected ? selectedBg : '#f1f5f9',
        color: selected ? '#ffffff' : '#475569',
        border: selected ? 'none' : '1px solid #cbd5e1',
        boxShadow: selected ? '0 2px 6px rgba(59,130,246,0.35)' : 'none',
        '&:hover': {
          transform: 'scale(1.04)',
          background: selected ? selectedBg : '#e2e8f0',
          boxShadow: selected
            ? '0 4px 10px rgba(59,130,246,0.45)'
            : '0 1px 4px rgba(0,0,0,0.08)',
        },
      }}
    />
  );
};

// ── Section badge (count of selected items) ──────────────────────────────────
const SectionBadge: React.FC<{ count: number }> = ({ count }) =>
  count > 0 ? (
    <Box
      sx={{
        ml: 'auto',
        bgcolor: '#3b82f6',
        color: 'white',
        borderRadius: 10,
        px: 0.8,
        py: 0.1,
        fontSize: '0.65rem',
        fontWeight: 700,
        lineHeight: 1.6,
        minWidth: 18,
        textAlign: 'center',
      }}
    >
      {count}
    </Box>
  ) : null;

// ── Section header ────────────────────────────────────────────────────────────
const SectionLabel: React.FC<{ label: string; selectedCount?: number }> = ({
  label,
  selectedCount = 0,
}) => (
  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
    <Typography
      variant="subtitle2"
      sx={{
        fontWeight: 700,
        color: '#1e40af',
        fontSize: '0.7rem',
        textTransform: 'uppercase',
        letterSpacing: 1.5,
        borderLeft: '3px solid #3b82f6',
        pl: 1,
      }}
    >
      {label}
    </Typography>
    <SectionBadge count={selectedCount} />
  </Box>
);

// ── Section wrapper ───────────────────────────────────────────────────────────
const Section: React.FC<{ children: React.ReactNode; alt?: boolean }> = ({
  children,
  alt = false,
}) => (
  <Box
    sx={{
      p: 2,
      borderBottom: '1px solid #e2e8f0',
      bgcolor: alt ? '#f8fafc' : '#ffffff',
      transition: 'background 0.2s',
    }}
  >
    {children}
  </Box>
);

// ─────────────────────────────────────────────────────────────────────────────

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

  const toggleBodyType = (name: string) => {
    const current = searchContext.bodyTypes || [];
    const next = current.includes(name)
      ? current.filter(b => b !== name)
      : [...current, name];
    onContextChange({ ...searchContext, bodyTypes: next });
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

  const isFeatureSelected = (key: string, value: string) =>
    selectedFeatures.some(f => f.feature_key === key && f.value === value);

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

  // ── Section counts for badges ──
  const selectedBrandsCount = searchContext.brands.length;
  const selectedBodyCount = (searchContext.bodyTypes || []).length;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* ── Section 1: Brands ── */}
      <Section>
        <SectionLabel label="Marka" selectedCount={selectedBrandsCount} />
        {loadingInitial ? (
          <CircularProgress size={20} />
        ) : (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {sortedBrands.map(brand => {
              const count = initialData?.brand_counts?.[brand] || 0;
              const selected = searchContext.brands.includes(brand);
              return (
                <FilterChip
                  key={brand}
                  label={`${brand} (${count})`}
                  selected={selected}
                  onClick={() => toggleBrand(brand)}
                  variant="primary"
                />
              );
            })}
          </Box>
        )}
      </Section>

      {/* ── Section 2: Body Types ── */}
      {!loadingInitial && initialData?.body_types && initialData.body_types.length > 0 && (
        <Section alt>
          <SectionLabel label="Typ nadwozia" selectedCount={selectedBodyCount} />
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {initialData.body_types.map(bt => {
              const selected = (searchContext.bodyTypes || []).includes(bt.name);
              return (
                <FilterChip
                  key={bt.name}
                  label={`${bt.name} (${bt.count})`}
                  selected={selected}
                  onClick={() => toggleBodyType(bt.name)}
                  variant="primary"
                />
              );
            })}
          </Box>
        </Section>
      )}

      {/* ── Section 3: Models (conditional) ── */}
      {searchContext.brands.length > 0 && (
        <Section>
          <SectionLabel label="Model" selectedCount={searchContext.models.length} />
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
        </Section>
      )}

      {/* ── Section 4: Primary Enum Facets (Napęd, Paliwo, Skrzynia…) ── */}
      {!loadingFilters && primaryEnumFacets.length > 0 && (
        <Section alt>
          {primaryEnumFacets.map(facet => {
            const facetSelected = facet.items.filter(i => isFeatureSelected(facet.key, i.value)).length;
            return (
              <Box key={facet.key} sx={{ mb: 1.5, '&:last-child': { mb: 0 } }}>
                <SectionLabel label={facet.name} selectedCount={facetSelected} />
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                  {facet.items.map(item => {
                    const selected = isFeatureSelected(facet.key, item.value);
                    return (
                      <FilterChip
                        key={item.value}
                        label={`${item.value} (${item.count})`}
                        selected={selected}
                        onClick={() => toggleFeature(facet.key, item.value, 1, false)}
                        variant="secondary"
                      />
                    );
                  })}
                </Box>
              </Box>
            );
          })}
        </Section>
      )}

      {/* ── Section 5: Samar Classes ── */}
      {!loadingInitial && (
        <Section>
          <SectionLabel label="Klasa Samar" selectedCount={searchContext.samarClassIds.length} />
          <Autocomplete
            multiple
            size="small"
            options={initialData?.samar_classes || []}
            getOptionLabel={(opt) => opt.name}
            value={initialData?.samar_classes.filter(c => searchContext.samarClassIds.includes(c.id)) || []}
            onChange={(_, newVal) => onContextChange({ ...searchContext, samarClassIds: newVal.map(v => v.id) })}
            renderInput={(params) => <TextField {...params} placeholder="Wybierz klasy..." />}
          />
        </Section>
      )}

      {/* ── Section 6: Numeric params ── */}
      <Section alt>
        <SectionLabel label="Parametry" />

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
      </Section>

      {/* ── Search Button ── */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #e2e8f0', bgcolor: '#ffffff' }}>
        <Button
          variant="contained"
          fullWidth
          onClick={onTriggerSearch}
          disabled={isSearching}
          sx={{
            fontWeight: 700,
            py: 1.2,
            fontSize: '0.9rem',
            letterSpacing: 0.5,
            borderRadius: 2,
            background: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)',
            boxShadow: '0 4px 12px rgba(59,130,246,0.4)',
            transition: 'all 0.2s ease',
            '&:hover': {
              background: 'linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)',
              boxShadow: '0 6px 16px rgba(59,130,246,0.5)',
              transform: 'translateY(-1px)',
            },
            '&:active': {
              transform: 'translateY(0)',
            },
            '&.Mui-disabled': {
              background: '#cbd5e1',
              boxShadow: 'none',
            },
          }}
        >
          {isSearching ? 'Wyszukiwanie…' : '🔍 Szukaj Ofert'}
        </Button>
      </Box>

      {/* ── Section 7: Feature Tree (Nice to have) ── */}
      <Box sx={{ p: 2 }}>
        <SectionLabel label="Wymagania" selectedCount={selectedFeatures.filter(f => f.requirement === 'NICE_TO_HAVE' || f.requirement === 'MUST_HAVE').length} />
        {loadingFilters ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
        ) : !data || (!data.facet_groups?.length && !data.boolean_filters?.length) ? (
          <Typography variant="body2" color="textSecondary">Wybierz pojazdy, aby załadować cechy.</Typography>
        ) : (
          <Box>
            {data.boolean_filters && Array.from(new Set(data.boolean_filters.map(f => f.group_name))).map((groupName) => {
              const groupFilters = data.boolean_filters!.filter(f => f.group_name === groupName);
              if (groupFilters.length === 0) return null;

              return (
                <Accordion key={`bool-${groupName}`} disableGutters
                  sx={{
                    boxShadow: 'none',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px !important',
                    mb: 0.5,
                    '&:before': { display: 'none' },
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon sx={{ color: '#64748b', fontSize: '1.1rem' }} />}
                    sx={{
                      minHeight: 36,
                      bgcolor: '#f1f5f9',
                      color: '#334155',
                      '&:hover': { bgcolor: '#e9eef5' },
                      '& .MuiAccordionSummary-content': { my: 0.5 },
                    }}
                  >
                    <Typography sx={{ textTransform: 'capitalize', fontSize: '0.82rem', fontWeight: 600, color: '#334155' }}>
                      {groupName.replace(/_/g, ' ')}
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails sx={{ p: '8px 16px', bgcolor: '#f8fafc' }}>
                    <FormGroup sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
                      {groupFilters.map((filter) => (
                        <FormControlLabel
                          key={filter.feature_key}
                          control={
                            <Checkbox
                              size="small"
                              checked={isFeatureSelected(filter.feature_key, 'true')}
                              onChange={() => toggleFeature(filter.feature_key, 'true', 1, false)}
                              sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#3b82f6' } }}
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
