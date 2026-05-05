import React, { useState } from 'react';
import {
  Box, CircularProgress, Autocomplete, TextField, Typography,
  FormControlLabel, Switch, Collapse, Slider, Button
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { FilterChip, SectionLabel, Section } from './FilterUIComponents';
import { AdaptiveSliderField } from '../AdaptiveSliderField';
import type { SearchContext, SelectedFeature, InitialDataResponse, TrimsAndOptionsResponse, EnumFilter } from '../../types';
import type { LiveFacets } from '../../hooks/useLiveFacets';
import { MATRIX_LIMITS } from '../../../config/matrixLimits';

const SAMAR_TOP_N = 10;

interface Level1PrimaryProps {
  searchContext: SearchContext;
  onContextChange: (ctx: SearchContext) => void;
  selectedFeatures: SelectedFeature[];

  loadingInitial: boolean;
  initialData: InitialDataResponse | null;
  sortedBrands: string[];

  loadingTrims: boolean;
  trimsAndOptions: TrimsAndOptionsResponse | null;

  loadingFilters: boolean;
  primaryEnumFacets: EnumFilter[];

  liveFacets: LiveFacets;

  // Actions
  toggleBrand: (brand: string) => void;
  toggleTrim: (trim: string) => void;
  toggleBodyType: (name: string) => void;
  toggleFuelType: (fuel: string) => void;
  toggleTransmission: (transmission: string) => void;
  toggleDriveType: (drive: string) => void;
  toggleSamarClassId: (id: number) => void;
  isFeatureSelected: (key: string, value: string) => boolean;
  toggleFeature: (key: string, value: string, weight?: number, isMustHave?: boolean) => void;
}

export const Level1Primary: React.FC<Level1PrimaryProps> = ({
  searchContext, onContextChange,
  loadingInitial, initialData, sortedBrands,
  loadingTrims, trimsAndOptions,
  loadingFilters, primaryEnumFacets,
  liveFacets,
  toggleBrand, toggleTrim, toggleBodyType,
  toggleFuelType, toggleTransmission, toggleDriveType, toggleSamarClassId,
  isFeatureSelected, toggleFeature,
}) => {
  const [samarExpanded, setSamarExpanded] = useState(false);

  const hasAnyFilter =
    searchContext.fuelTypes.length > 0 ||
    searchContext.transmissions.length > 0 ||
    searchContext.driveTypes.length > 0 ||
    searchContext.samarClassIds.length > 0 ||
    searchContext.bodyTypes.length > 0;

  const samarVisible = samarExpanded
    ? liveFacets.samarItems
    : liveFacets.samarItems.slice(0, SAMAR_TOP_N);
  const hiddenSamarCount = liveFacets.samarItems.length - SAMAR_TOP_N;

  return (
    <>
      {/* Section: Matrix calc — first, so user immediately marks they want prices */}
      <Section>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0 }}>
          <SectionLabel label="Kalkulacje (Matrix)" />
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={!!searchContext.useMatrixFilters}
                onChange={(e) => onContextChange({ ...searchContext, useMatrixFilters: e.target.checked, exact_mode: true })}
                sx={{
                  '& .MuiSwitch-switchBase.Mui-checked': { color: '#1e40af' },
                  '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { bgcolor: '#3b82f6' },
                }}
              />
            }
            label={
              <Typography variant="caption" sx={{ color: searchContext.useMatrixFilters ? '#1e40af' : '#94a3b8', fontWeight: 600, fontSize: '0.68rem' }}>
                {searchContext.useMatrixFilters ? 'Włączone' : 'Wyłączone'}
              </Typography>
            }
            labelPlacement="start"
            sx={{ m: 0, gap: 0.5 }}
          />
        </Box>

        <Collapse in={!!searchContext.useMatrixFilters} timeout={200}>
          <Box sx={{ pt: 1.5 }}>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: -0.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>Okres (m-ce)</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
                  {searchContext.exact_duration_months} mc
                </Typography>
              </Box>
              <Slider
                value={searchContext.exact_duration_months}
                onChange={(_, val) => onContextChange({ ...searchContext, exact_duration_months: val as number, exact_mode: true })}
                min={24} max={60} step={12}
                marks={[24, 36, 48, 60].map(v => ({ value: v, label: String(v) }))}
                valueLabelDisplay="auto"
                sx={{ mt: 1, '& .MuiSlider-markLabel': { fontSize: '0.65rem' } }}
              />
            </Box>

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: -0.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>Łączny przebieg na kontrakt (km)</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
                  {(searchContext.exact_total_mileage / 1000).toFixed(0)}k km
                </Typography>
              </Box>
              <Slider
                value={searchContext.exact_total_mileage}
                onChange={(_, val) => onContextChange({ ...searchContext, exact_total_mileage: val as number, exact_mode: true })}
                min={MATRIX_LIMITS.KM_MIN_CONTRACT} max={MATRIX_LIMITS.KM_MAX_CONTRACT} step={MATRIX_LIMITS.KM_STEP_CONTRACT}
                marks={[20000, 100000, 200000, 300000].map(v => ({ value: v, label: `${(v / 1000).toFixed(0)}k` }))}
                valueLabelDisplay="auto" valueLabelFormat={(v) => `${(v / 1000).toFixed(0)}k`}
                sx={{ mt: 1, '& .MuiSlider-markLabel': { fontSize: '0.65rem' } }}
              />
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, mt: 2 }}>
              <AdaptiveSliderField
                label="Marża min (%)"
                min={0}
                max={100}
                value={searchContext.margin_pct || 0}
                onChange={(val) => onContextChange({ ...searchContext, margin_pct: val })}
              />
              <TextField
                label="Max Rata (Netto)" type="number" size="small"
                value={searchContext.monthly_budget || ''}
                onChange={(e) => onContextChange({ ...searchContext, monthly_budget: parseInt(e.target.value) || undefined })}
                sx={{ flex: 1 }}
              />
            </Box>
          </Box>
        </Collapse>
      </Section>

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

      {/* Section: Fuel type */}
      {liveFacets.fuels.length > 0 && (
        <Section>
          <SectionLabel label="Paliwo" selectedCount={searchContext.fuelTypes.length} />
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {liveFacets.fuels.map(item => {
              const selected = searchContext.fuelTypes.includes(item.value);
              const dim = hasAnyFilter && !selected && item.count === 0;
              return (
                <FilterChip
                  key={item.value}
                  label={`${item.value} (${item.count})`}
                  selected={selected}
                  onClick={() => toggleFuelType(item.value)}
                  variant="primary"
                  dim={dim}
                />
              );
            })}
          </Box>
        </Section>
      )}

      {/* Section: Transmission */}
      {liveFacets.transmissions.length > 0 && (
        <Section alt>
          <SectionLabel label="Skrzynia biegów" selectedCount={searchContext.transmissions.length} />
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {liveFacets.transmissions.map(item => {
              const selected = searchContext.transmissions.includes(item.value);
              const dim = hasAnyFilter && !selected && item.count === 0;
              return (
                <FilterChip
                  key={item.value}
                  label={`${item.value} (${item.count})`}
                  selected={selected}
                  onClick={() => toggleTransmission(item.value)}
                  variant="primary"
                  dim={dim}
                />
              );
            })}
          </Box>
        </Section>
      )}

      {/* Section: Drive type */}
      {liveFacets.driveTypes.length > 0 && (
        <Section>
          <SectionLabel label="Napęd" selectedCount={searchContext.driveTypes.length} />
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {liveFacets.driveTypes.map(item => {
              const selected = searchContext.driveTypes.includes(item.value);
              const dim = hasAnyFilter && !selected && item.count === 0;
              return (
                <FilterChip
                  key={item.value}
                  label={`${item.value} (${item.count})`}
                  selected={selected}
                  onClick={() => toggleDriveType(item.value)}
                  variant="primary"
                  dim={dim}
                />
              );
            })}
          </Box>
        </Section>
      )}

      {/* Section: SAMAR class */}
      {liveFacets.samarItems.length > 0 && (
        <Section alt>
          <SectionLabel label="Klasa SAMAR" selectedCount={searchContext.samarClassIds.length} />
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
            {samarVisible.map(item => {
              const selected = searchContext.samarClassIds.includes(item.id);
              const dim = hasAnyFilter && !selected && item.count === 0;
              return (
                <FilterChip
                  key={item.id}
                  label={`${item.value} (${item.count})`}
                  selected={selected}
                  onClick={() => toggleSamarClassId(item.id)}
                  variant="secondary"
                  dim={dim}
                />
              );
            })}
          </Box>
          {hiddenSamarCount > 0 && (
            <Button
              size="small"
              onClick={() => setSamarExpanded(prev => !prev)}
              endIcon={samarExpanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
              sx={{ mt: 0.75, fontSize: '0.7rem', p: 0, color: '#64748b', minWidth: 0, textTransform: 'none' }}
            >
              {samarExpanded ? 'Zwiń' : `Pokaż pozostałe (${hiddenSamarCount})`}
            </Button>
          )}
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

    </>
  );
};
