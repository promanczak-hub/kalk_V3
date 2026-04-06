import React, { useMemo, useState } from 'react';
import {
  Box, Paper, Typography, Button, IconButton, Select, MenuItem,
  TextField, Chip, Tooltip, CircularProgress, InputLabel, FormControl,
  Autocomplete,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ClearAllIcon from '@mui/icons-material/ClearAll';
import type {
  TenderCriterion,
  FeatureDictionaryEntry,
  TenderPriority,
} from '../hooks/useTenderEngine';

const OPERATORS = ['>=', '<=', '>', '<', '=', '!='] as const;

const PRIORITY_COLORS: Record<TenderPriority, { bg: string; text: string; label: string }> = {
  MUST: { bg: '#fef2f2', text: '#dc2626', label: 'Wymagane' },
  SHOULD: { bg: '#fffbeb', text: '#d97706', label: 'Pożądane' },
  NICE: { bg: '#f0fdf4', text: '#16a34a', label: 'Opcjonalne' },
};

interface TenderCriteriaBuilderProps {
  dictionary: FeatureDictionaryEntry[];
  criteria: TenderCriterion[];
  isLoadingDict: boolean;
  onAdd: (featureKey: string, displayName?: string) => void;
  onUpdate: (id: string, updates: Partial<TenderCriterion>) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
  onEvaluate: () => void;
  isEvaluating: boolean;
}

export const TenderCriteriaBuilder: React.FC<TenderCriteriaBuilderProps> = ({
  dictionary,
  criteria,
  isLoadingDict,
  onAdd,
  onUpdate,
  onRemove,
  onClear,
  onEvaluate,
  isEvaluating,
}) => {
  const [searchValue, setSearchValue] = useState<FeatureDictionaryEntry | null>(null);

  // Group dictionary by feature_tier
  const groupedOptions = useMemo(() => {
    const tiers: Record<string, FeatureDictionaryEntry[]> = {
      CORE: [],
      EXTENDED: [],
      EDGE: [],
    };
    for (const entry of dictionary) {
      const tier = entry.feature_tier || 'EXTENDED';
      tiers[tier]?.push(entry);
    }
    return tiers;
  }, [dictionary]);

  // Flatten into MUI-friendly option groups
  const autocompleteOptions = useMemo(() => {
    const result: FeatureDictionaryEntry[] = [];
    for (const tier of ['CORE', 'EXTENDED', 'EDGE']) {
      const items = groupedOptions[tier] || [];
      result.push(...items.sort((a, b) => a.display_name.localeCompare(b.display_name)));
    }
    return result;
  }, [groupedOptions]);

  const usedKeys = new Set(criteria.map(c => c.feature_key));

  const handleAddFeature = (entry: FeatureDictionaryEntry | null) => {
    if (!entry) return;
    onAdd(entry.feature_key, entry.display_name);
    setSearchValue(null);
  };

  const getFeatureType = (featureKey: string): string => {
    return dictionary.find(d => d.feature_key === featureKey)?.feature_type || 'bool';
  };

  const getUnit = (featureKey: string): string | null => {
    return dictionary.find(d => d.feature_key === featureKey)?.canonical_unit || null;
  };

  return (
    <Box>
      {/* Search & Add */}
      <Box sx={{ mb: 2 }}>
        <Autocomplete
          value={searchValue}
          onChange={(_, newValue) => handleAddFeature(newValue)}
          options={autocompleteOptions.filter(o => !usedKeys.has(o.feature_key))}
          getOptionLabel={(option) => option.display_name}
          groupBy={(option) => {
            const tier = option.feature_tier || 'EXTENDED';
            const labels: Record<string, string> = {
              CORE: '⭐ Kluczowe (CORE)',
              EXTENDED: '📋 Rozszerzone',
              EDGE: '✨ Szczegółowe',
            };
            return labels[tier] || tier;
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Dodaj kryterium przetargowe"
              placeholder="Szukaj cechy..."
              size="small"
              InputProps={{
                ...params.InputProps,
                startAdornment: (
                  <>
                    <AddCircleOutlineIcon sx={{ color: 'action.active', mr: 0.5, fontSize: 20 }} />
                    {params.InputProps.startAdornment}
                  </>
                ),
              }}
            />
          )}
          renderOption={(props, option) => (
            <li {...props} key={option.feature_key}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                <Typography variant="body2" sx={{ flexGrow: 1 }}>
                  {option.display_name}
                </Typography>
                {option.canonical_unit && (
                  <Chip label={option.canonical_unit} size="small" variant="outlined" sx={{ fontSize: '0.65rem', height: 18 }} />
                )}
                {option.feature_type !== 'bool' && (
                  <Chip label={option.feature_type} size="small" sx={{ fontSize: '0.6rem', height: 16, bgcolor: '#f1f5f9' }} />
                )}
              </Box>
            </li>
          )}
          loading={isLoadingDict}
          noOptionsText="Brak pasujących cech"
          size="small"
          fullWidth
          blurOnSelect
        />
      </Box>

      {/* Criteria List */}
      {criteria.length === 0 ? (
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Brak kryteriów. Użyj wyszukiwarki powyżej aby dodać wymagania przetargowe.
          </Typography>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {criteria.map((criterion) => {
            const featureType = getFeatureType(criterion.feature_key);
            const unit = getUnit(criterion.feature_key);
            const priorityConfig = PRIORITY_COLORS[criterion.priority];

            return (
              <Paper
                key={criterion.id}
                elevation={0}
                sx={{
                  p: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 2,
                  bgcolor: priorityConfig.bg,
                  transition: 'all 0.15s ease',
                  '&:hover': { borderColor: priorityConfig.text, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  {/* Feature name */}
                  <Tooltip title={criterion.feature_key} arrow>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 600, minWidth: 140, flexShrink: 0 }}
                    >
                      {criterion.display_name || criterion.feature_key}
                    </Typography>
                  </Tooltip>

                  {/* Operator */}
                  {featureType !== 'bool' && (
                    <FormControl size="small" sx={{ minWidth: 70 }}>
                      <Select
                        value={criterion.operator}
                        onChange={(e) => onUpdate(criterion.id, { operator: e.target.value as TenderCriterion['operator'] })}
                        variant="outlined"
                        sx={{ fontSize: '0.8rem', height: 32 }}
                      >
                        {OPERATORS.map(op => (
                          <MenuItem key={op} value={op} sx={{ fontSize: '0.8rem' }}>{op}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}

                  {/* Value */}
                  {featureType === 'bool' ? (
                    <Select
                      value={criterion.value === true || criterion.value === 'true' ? 'true' : 'false'}
                      onChange={(e) => onUpdate(criterion.id, { value: e.target.value === 'true', operator: '=' })}
                      size="small"
                      sx={{ fontSize: '0.8rem', height: 32, minWidth: 80 }}
                    >
                      <MenuItem value="true" sx={{ fontSize: '0.8rem' }}>✓ Tak</MenuItem>
                      <MenuItem value="false" sx={{ fontSize: '0.8rem' }}>✗ Nie</MenuItem>
                    </Select>
                  ) : (
                    <TextField
                      value={criterion.value}
                      onChange={(e) => {
                        const val = featureType === 'int' || featureType === 'float'
                          ? parseFloat(e.target.value) || 0
                          : e.target.value;
                        onUpdate(criterion.id, { value: val });
                      }}
                      size="small"
                      type={featureType === 'int' || featureType === 'float' ? 'number' : 'text'}
                      sx={{ width: 100, '& input': { fontSize: '0.8rem', py: 0.5 } }}
                      InputProps={{
                        endAdornment: unit ? (
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 0.5, whiteSpace: 'nowrap' }}>
                            {unit}
                          </Typography>
                        ) : undefined,
                      }}
                    />
                  )}

                  {/* Priority */}
                  <FormControl size="small" sx={{ minWidth: 100 }}>
                    <InputLabel sx={{ fontSize: '0.7rem' }}>Priorytet</InputLabel>
                    <Select
                      value={criterion.priority}
                      onChange={(e) => onUpdate(criterion.id, { priority: e.target.value as TenderPriority })}
                      label="Priorytet"
                      sx={{ fontSize: '0.8rem', height: 32 }}
                    >
                      {Object.entries(PRIORITY_COLORS).map(([key, cfg]) => (
                        <MenuItem key={key} value={key} sx={{ fontSize: '0.8rem' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: cfg.text }} />
                            {cfg.label}
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  {/* Delete */}
                  <IconButton size="small" onClick={() => onRemove(criterion.id)} sx={{ ml: 'auto', color: 'text.secondary' }}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Paper>
            );
          })}
        </Box>
      )}

      {/* Action buttons */}
      {criteria.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button
            variant="contained"
            onClick={onEvaluate}
            disabled={isEvaluating}
            startIcon={isEvaluating ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
            sx={{
              flexGrow: 1,
              background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
              fontWeight: 600,
              textTransform: 'none',
            }}
          >
            {isEvaluating ? 'Oceniam flotę...' : `Oceń flotę (${criteria.length} kryteriów)`}
          </Button>
          <Tooltip title="Wyczyść wszystkie kryteria">
            <IconButton onClick={onClear} color="error" size="small">
              <ClearAllIcon />
            </IconButton>
          </Tooltip>
        </Box>
      )}
    </Box>
  );
};
