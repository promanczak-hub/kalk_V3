import React, { useEffect, useState, useMemo, useRef } from 'react';
import {
  Box, Typography, CircularProgress,
  FormGroup, FormControlLabel, Checkbox, Button, TextField, Autocomplete, Chip, Slider,
  IconButton, Tooltip, Tabs, Tab
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { apiFetch } from '../../lib/api';
import type {
  AvailableFiltersResponse, SearchContext, SelectedFeature, EnumFilter, InitialDataResponse,
  TrimsAndOptionsResponse, OptionItem,
} from '../types';

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
  const [trimsAndOptions, setTrimsAndOptions] = useState<TrimsAndOptionsResponse | null>(null);
  const [loadingTrims, setLoadingTrims] = useState(false);
  const [stdOptionSearch, setStdOptionSearch] = useState('');
  const [paidOptionSearch, setPaidOptionSearch] = useState('');
  const [universalSearch, setUniversalSearch] = useState('');

  // ── Level-2 panel ref for scroll ──
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const level2Ref = useRef<HTMLDivElement>(null);
  const [onLevel2, setOnLevel2] = useState(false);
  const [l2Tab, setL2Tab] = useState<'universal' | 'dedicated'>('universal');

  const scrollToLevel2 = () => {
    level2Ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setOnLevel2(true);
  };

  const scrollToTop = () => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
    setOnLevel2(false);
  };

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
    const hasBrandOrModelOrBody = searchContext.brands.length > 0 || searchContext.models.length > 0 || searchContext.bodyTypes.length > 0;
    if (hasBrandOrModelOrBody || onLevel2) {
      fetchFilters();
      fetchTrimsAndOptions();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchContext.brands.length, searchContext.models.length, searchContext.bodyTypes.length, onLevel2]);

  const fetchFilters = async () => {
    setLoadingFilters(true);
    try {
      const payload = {
        brands: searchContext.brands.length > 0 ? searchContext.brands : null,
        models: searchContext.models.length > 0 ? searchContext.models : null,
        body_types: searchContext.bodyTypes.length > 0 ? searchContext.bodyTypes : null,
        samar_class_ids: null,
      };
      const res = await apiFetch('/api/scoring-search/available-filters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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

  const fetchTrimsAndOptions = async () => {
    if (searchContext.brands.length === 0 && searchContext.models.length === 0) {
      setTrimsAndOptions(null);
      return;
    }
    setLoadingTrims(true);
    try {
      const payload = {
        brands: searchContext.brands.length > 0 ? searchContext.brands : null,
        models: searchContext.models.length > 0 ? searchContext.models : null,
      };
      const res = await apiFetch('/api/scoring-search/trims-and-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const json: TrimsAndOptionsResponse = await res.json();
        setTrimsAndOptions(json);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingTrims(false);
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
    // Reset models, trims when brand changes
    onContextChange({ ...searchContext, brands: next, models: [], trims: [] });
  };

  const toggleTrim = (trim: string) => {
    const current = searchContext.trims || [];
    const next = current.includes(trim)
      ? current.filter(t => t !== trim)
      : [...current, trim];
    onContextChange({ ...searchContext, trims: next });
  };

  const toggleBodyType = (name: string) => {
    const current = searchContext.bodyTypes || [];
    const next = current.includes(name)
      ? current.filter(b => b !== name)
      : [...current, name];
    onContextChange({ ...searchContext, bodyTypes: next });
  };

  // ── Primary enum facets ──
  const primaryEnumFacets = useMemo(() => {
    if (!data?.facet_groups) return [];
    const facets: EnumFilter[] = [];
    for (const group of data.facet_groups) {
      for (const filter of group.filters) {
        if (filter.items && filter.items.length > 0) facets.push(filter);
      }
    }
    return facets;
  }, [data]);

  // ── Boolean filter groups — sorted by total count desc ──
  const sortedBooleanGroups = useMemo(() => {
    if (!data?.boolean_filters) return [];
    const groups = Array.from(new Set(data.boolean_filters.map(f => f.group_name)));
    return groups
      .map(groupName => ({
        groupName,
        filters: data.boolean_filters!
          .filter(f => f.group_name === groupName)
          .sort((a, b) => (b.cnt ?? 0) - (a.cnt ?? 0)),
        totalCount: data.boolean_filters!
          .filter(f => f.group_name === groupName)
          .reduce((sum, f) => sum + (f.cnt ?? 0), 0),
      }))
      .sort((a, b) => b.totalCount - a.totalCount);
  }, [data]);

  const isFeatureSelected = (key: string, value: string) =>
    selectedFeatures.some(f => f.feature_key === key && f.value === value);

  const toggleFeature = (key: string, value: string, weight = 1, isMustHave = false) => {
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
        weight,
      }]);
    }
  };

  const isOptionSelected = (prefix: string, name: string) =>
    selectedFeatures.some(f => f.feature_key === `${prefix}${name}`);

  const toggleOption = (prefix: string, name: string) => {
    const key = `${prefix}${name}`;
    const existing = selectedFeatures.findIndex(f => f.feature_key === key);
    if (existing >= 0) {
      const clone = [...selectedFeatures];
      clone.splice(existing, 1);
      onFeaturesChange(clone);
    } else {
      onFeaturesChange([...selectedFeatures, {
        feature_key: key,
        operator: 'eq',
        value: 'true',
        requirement: 'MUST_HAVE',
        weight: 1,
      }]);
    }
  };

  const l2SelectedCount = selectedFeatures.filter(
    f => !['duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net', 'body_style'].includes(f.feature_key)
      && data?.boolean_filters?.some(bf => bf.feature_key === f.feature_key)
  ).length;

  return (
    <Box ref={scrollContainerRef} sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>

      {/* ══ LEVEL 1 — Primary filters ══ */}

      {/* Section: Brands */}
      <Section>
        <SectionLabel label="Marka" selectedCount={searchContext.brands.length} />
        {loadingInitial ? (
          <CircularProgress size={20} />
        ) : (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {sortedBrands.map(brand => (
              <FilterChip
                key={brand}
                label={`${brand} (${initialData?.brand_counts?.[brand] || 0})`}
                selected={searchContext.brands.includes(brand)}
                onClick={() => toggleBrand(brand)}
                variant="primary"
              />
            ))}
          </Box>
        )}
      </Section>

      {/* Section: Body Types */}
      {!loadingInitial && initialData?.body_types && initialData.body_types.length > 0 && (
        <Section alt>
          <SectionLabel label="Typ nadwozia" selectedCount={(searchContext.bodyTypes || []).length} />
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {initialData.body_types.map(bt => (
              <FilterChip
                key={bt.name}
                label={`${bt.name} (${bt.count})`}
                selected={(searchContext.bodyTypes || []).includes(bt.name)}
                onClick={() => toggleBodyType(bt.name)}
                variant="primary"
              />
            ))}
          </Box>
        </Section>
      )}

      {/* Section: Models (conditional) */}
      {searchContext.brands.length > 0 && (
        <Section>
          <SectionLabel label="Model" selectedCount={searchContext.models.length} />
          <Autocomplete
            multiple
            size="small"
            options={
              Array.from(new Set(
                searchContext.brands.flatMap(b => initialData?.brand_model_map?.[b] || [])
              )).sort()
            }
            value={searchContext.models}
            onChange={(_, newVal) => onContextChange({ ...searchContext, models: newVal, trims: [] })}
            renderInput={(params) => <TextField {...params} placeholder="Wybierz modele..." />}
          />
        </Section>
      )}

      {/* Section: Trim selector (conditional — after model selected) */}
      {searchContext.models.length > 0 && (
        <Section alt>
          <SectionLabel label="Wersja (trim)" selectedCount={(searchContext.trims || []).length} />
          {loadingTrims ? (
            <CircularProgress size={16} />
          ) : (trimsAndOptions?.trim_levels || []).length === 0 ? (
            <Typography variant="caption" color="textSecondary">Brak danych o wersjach</Typography>
          ) : (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {(trimsAndOptions?.trim_levels || []).map(t => (
                <FilterChip
                  key={t.name}
                  label={`${t.name} (${t.count})`}
                  selected={(searchContext.trims || []).includes(t.name)}
                  onClick={() => toggleTrim(t.name)}
                  variant="secondary"
                />
              ))}
            </Box>
          )}
        </Section>
      )}

      {/* Section: Primary Enum Facets */}
      {!loadingFilters && primaryEnumFacets.length > 0 && (
        <Section alt>
          {primaryEnumFacets.map(facet => {
            const facetSelected = facet.items.filter(i => isFeatureSelected(facet.key, i.value)).length;
            return (
              <Box key={facet.key} sx={{ mb: 1.5, '&:last-child': { mb: 0 } }}>
                <SectionLabel label={facet.name} selectedCount={facetSelected} />
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                  {facet.items.map(item => (
                    <FilterChip
                      key={item.value}
                      label={`${item.value} (${item.count})`}
                      selected={isFeatureSelected(facet.key, item.value)}
                      onClick={() => toggleFeature(facet.key, item.value, 1, false)}
                      variant="secondary"
                    />
                  ))}
                </Box>
              </Box>
            );
          })}
        </Section>
      )}

      {/* Section: Numeric params */}
      <Section>
        <Box sx={{ mb: 2 }}>
          <SectionLabel label="Kalkulacje (Matrix)" />
          <Tabs
            value={!searchContext.useMatrixFilters ? 'off' : searchContext.exact_mode ? 'exact' : 'ranges'}
            onChange={(_, val) => {
              if (val === 'off') {
                onContextChange({ ...searchContext, useMatrixFilters: false });
              } else if (val === 'ranges') {
                onContextChange({ ...searchContext, useMatrixFilters: true, exact_mode: false });
              } else if (val === 'exact') {
                onContextChange({ ...searchContext, useMatrixFilters: true, exact_mode: true });
              }
            }}
            variant="fullWidth"
            sx={{ 
               minHeight: 36, 
               bgcolor: '#f1f5f9', 
               borderRadius: 2, 
               p: 0.5,
               '& .MuiTab-root': { minHeight: 32, py: 0.5, fontSize: '0.7rem', fontWeight: 600, textTransform: 'none', borderRadius: 1.5, color: '#64748b' },
               '& .Mui-selected': { bgcolor: '#ffffff', color: '#1e40af', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
               '& .MuiTabs-indicator': { display: 'none' }
            }}
          >
            <Tab label="Wyłączone" value="off" disableRipple />
            <Tab label="Zakresy" value="ranges" disableRipple />
            <Tab label={
              <Tooltip title="Oblicz dokładną ratę 'w locie' dla każdego auta (Live LTR)" placement="top">
                <span>Live LTR</span>
              </Tooltip>
            } value="exact" disableRipple />
          </Tabs>
        </Box>

        <Box sx={{ opacity: searchContext.useMatrixFilters ? 1 : 0.4, pointerEvents: searchContext.useMatrixFilters ? 'auto' : 'none', transition: 'opacity 0.2s' }}>

          {searchContext.exact_mode ? (
            <Box sx={{ display: 'flex', gap: 2, mb: 2, p: 2, bgcolor: '#f8fafc', borderRadius: 2, border: '1px solid #e2e8f0' }}>
              <TextField
                label="Dokładny okres (m-ce)"
                type="number"
                size="small"
                fullWidth
                value={searchContext.exact_duration_months || ''}
                onChange={(e) => onContextChange({ ...searchContext, exact_duration_months: parseInt(e.target.value) || 0 })}
                InputProps={{ inputProps: { min: 1, max: 120 } }}
              />
              <TextField
                label="Dokładny łączny przebieg (km)"
                type="number"
                size="small"
                fullWidth
                value={searchContext.exact_total_mileage || ''}
                onChange={(e) => onContextChange({ ...searchContext, exact_total_mileage: parseInt(e.target.value) || 0 })}
                InputProps={{ inputProps: { min: 1000, step: 1000 } }}
              />
            </Box>
          ) : (
            <>
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: -0.5 }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>Okres (m-ce)</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
                    {searchContext.duration_months_range[0]}–{searchContext.duration_months_range[1]} mc
                  </Typography>
                </Box>
                <Slider
                  value={searchContext.duration_months_range}
                  onChange={(_, val) => onContextChange({ ...searchContext, duration_months_range: val as [number, number] })}
                  min={24} max={60} step={12}
                  marks={[24, 36, 48, 60].map(v => ({ value: v, label: String(v) }))}
                  valueLabelDisplay="auto" disableSwap
                  sx={{ mt: 1, '& .MuiSlider-markLabel': { fontSize: '0.65rem' } }}
                />
              </Box>

              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: -0.5 }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>Łączny przebieg na kontrakt (km)</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
                    {(searchContext.total_mileage_range[0] / 1000).toFixed(0)}k–{(searchContext.total_mileage_range[1] / 1000).toFixed(0)}k km
                  </Typography>
                </Box>
                <Slider
                  value={searchContext.total_mileage_range}
                  onChange={(_, val) => onContextChange({ ...searchContext, total_mileage_range: val as [number, number] })}
                  min={20000} max={200000} step={5000}
                  marks={[20000, 60000, 100000, 140000, 200000].map(v => ({ value: v, label: `${(v / 1000).toFixed(0)}k` }))}
                  valueLabelDisplay="auto" valueLabelFormat={(v) => `${(v / 1000).toFixed(0)}k`}
                  disableSwap
                  sx={{ mt: 1, '& .MuiSlider-markLabel': { fontSize: '0.65rem' } }}
                />
              </Box>
            </>
          )}

          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
            <TextField
              label="Marża min (%)" type="number" size="small"
              value={searchContext.margin_pct}
              onChange={(e) => onContextChange({ ...searchContext, margin_pct: parseFloat(e.target.value) || 0 })}
            />
            <TextField
              label="Max Rata (Netto)" type="number" size="small"
              value={searchContext.monthly_budget || ''}
              onChange={(e) => onContextChange({ ...searchContext, monthly_budget: parseInt(e.target.value) || undefined })}
            />
          </Box>
        </Box>
      </Section>

      {/* Search Button */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #e2e8f0', bgcolor: '#ffffff' }}>
        <Button
          variant="contained"
          fullWidth
          onClick={onTriggerSearch}
          disabled={isSearching}
          sx={{
            fontWeight: 700, py: 1.2, fontSize: '0.9rem', letterSpacing: 0.5, borderRadius: 2,
            background: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)',
            boxShadow: '0 4px 12px rgba(59,130,246,0.4)',
            transition: 'all 0.2s ease',
            '&:hover': {
              background: 'linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)',
              boxShadow: '0 6px 16px rgba(59,130,246,0.5)',
              transform: 'translateY(-1px)',
            },
            '&:active': { transform: 'translateY(0)' },
            '&.Mui-disabled': { background: '#cbd5e1', boxShadow: 'none' },
          }}
        >
          {isSearching ? 'Wyszukiwanie…' : '🔍 Szukaj Ofert'}
        </Button>
      </Box>

      {/* ── Separator / scroll-to-L2 ── */}
      <Tooltip title={onLevel2 ? 'Wróć do filtrów głównych' : `Filtry szczegółowe${l2SelectedCount > 0 ? ` (${l2SelectedCount} aktywnych)` : ''}`}>
        <Box
          onClick={onLevel2 ? scrollToTop : scrollToLevel2}
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 1,
            py: 1.2,
            cursor: 'pointer',
            bgcolor: '#f1f5f9',
            borderBottom: '1px solid #e2e8f0',
            color: '#64748b',
            transition: 'all 0.2s ease',
            '&:hover': { bgcolor: '#e2e8f0', color: '#1e40af' },
          }}
        >
          <Typography sx={{ fontSize: '0.72rem', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
            Filtry szczegółowe
          </Typography>
          {l2SelectedCount > 0 && (
            <Box sx={{ bgcolor: '#3b82f6', color: 'white', borderRadius: 10, px: 0.8, fontSize: '0.65rem', fontWeight: 700 }}>
              {l2SelectedCount}
            </Box>
          )}
          <IconButton size="small" disableRipple sx={{ p: 0, color: 'inherit' }}>
            {onLevel2 ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
          </IconButton>
        </Box>
      </Tooltip>

      {/* ══ LEVEL 2 — Boolean feature filters ══ */}
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
            ) : sortedBooleanGroups.length === 0 ? (
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
                
                {sortedBooleanGroups.map(({ groupName, filters }) => {
                  const filteredFilters = filters.filter(f => 
                    (f.feature_name || f.feature_key.replace(/_/g, ' ')).toLowerCase().includes(universalSearch.toLowerCase())
                  );
                  if (filteredFilters.length === 0) return null;

                  const groupSelected = filteredFilters.filter(f => isFeatureSelected(f.feature_key, 'true')).length;

                  return (
                    <Box key={`bool-${groupName}`} sx={{ mb: 3 }}>
                      <SectionLabel
                        label={groupName.replace(/_/g, ' ')}
                        selectedCount={groupSelected}
                      />
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
    </Box>
  );
};

// ── Options checklist sub-component ──────────────────────────────────────────
const OptionsChecklist: React.FC<{
  items: OptionItem[];
  prefix: string;
  selectedFeatures: SelectedFeature[];
  isSelected: (prefix: string, name: string) => boolean;
  onToggle: (prefix: string, name: string) => void;
}> = ({ items, prefix, isSelected, onToggle }) => {
  if (items.length === 0) {
    return (
      <Typography variant="caption" color="textSecondary" sx={{ display: 'block', py: 1 }}>
        Brak pasujących opcji
      </Typography>
    );
  }
  return (
    <FormGroup>
      {items.slice(0, 50).map(item => (
        <FormControlLabel
          key={item.name}
          control={
            <Checkbox
              size="small"
              checked={isSelected(prefix, item.name)}
              onChange={() => onToggle(prefix, item.name)}
              sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#7c3aed' }, py: 0.3 }}
            />
          }
          label={
            <Typography variant="body2" sx={{ fontSize: '0.78rem', color: '#475569' }}>
              {item.name}
              <Box component="span" sx={{ color: '#94a3b8', ml: 0.5, fontSize: '0.72rem' }}>({item.count})</Box>
            </Typography>
          }
          sx={{ m: 0, alignItems: 'flex-start' }}
        />
      ))}
      {items.length > 50 && (
        <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5 }}>
          Pokazano 50 z {items.length} — zawęź wyszukiwanie
        </Typography>
      )}
    </FormGroup>
  );
};
