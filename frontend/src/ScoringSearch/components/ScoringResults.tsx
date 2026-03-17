import React, { useMemo, useState, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, Chip, FormControl, Select, MenuItem,
  Tooltip, Button, CircularProgress
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import LocalGasStationIcon from '@mui/icons-material/LocalGasStation';
import BoltIcon from '@mui/icons-material/Bolt';
import SpeedIcon from '@mui/icons-material/Speed';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import SettingsIcon from '@mui/icons-material/Settings';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import CalculateIcon from '@mui/icons-material/Calculate';
import BuildIcon from '@mui/icons-material/Build';
import { apiFetch } from '../../lib/api';

export type SortOption = 'score_desc' | 'price_asc' | 'price_desc' | 'brand_asc';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'score_desc', label: 'Dopasowanie ↓' },
  { value: 'price_asc', label: 'Cena ↑ (najtańsze)' },
  { value: 'price_desc', label: 'Cena ↓ (najdroższe)' },
  { value: 'brand_asc', label: 'Marka A-Z' },
];

/* ── Fuel helpers ── */
const fuelIcon = (fuel: string | null) => {
  if (!fuel) return <LocalGasStationIcon sx={{ fontSize: 14 }} />;
  const low = fuel.toLowerCase();
  if (low.includes('elektr') || low.includes('ev') || low.includes('bev'))
    return <BoltIcon sx={{ fontSize: 14 }} />;
  if (low.includes('hybr')) return <BoltIcon sx={{ fontSize: 14 }} />;
  return <LocalGasStationIcon sx={{ fontSize: 14 }} />;
};

const fuelColor = (fuel: string | null): 'default' | 'success' | 'info' => {
  if (!fuel) return 'default';
  const low = fuel.toLowerCase();
  if (low.includes('elektr') || low.includes('ev') || low.includes('bev')) return 'success';
  if (low.includes('hybr')) return 'info';
  return 'default';
};

/* ── Spec chip styling ── */
const specChipSx = {
  height: 24,
  fontSize: '0.72rem',
  fontWeight: 500,
  borderRadius: '6px',
  '& .MuiChip-icon': { fontSize: 14 },
};

interface ScoringResultsProps {
  results: Record<string, unknown>[];
  loading: boolean;
}

export const ScoringResults: React.FC<ScoringResultsProps> = ({ results, loading }) => {
  const [sortBy, setSortBy] = useState<SortOption>('score_desc');
  const [calculatingIds, setCalculatingIds] = useState<Set<string>>(new Set());

  const handleCalculateSingle = useCallback(async (vehicleId: string) => {
    setCalculatingIds(prev => new Set(prev).add(vehicleId));
    try {
      await apiFetch('/api/scoring-search/cache/refresh-matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vehicle_ids: [vehicleId] }),
      });
    } catch (err) {
      console.error('Failed to trigger calculation for', vehicleId, err);
    }
    // Don't remove from set — it stays as "calculating in background"
    // User will re-search to see fresh prices
  }, []);

  const sortedResults = useMemo(() => {
    const sorted = [...results];
    switch (sortBy) {
      case 'score_desc':
        sorted.sort((a, b) => ((b.match_score_pct as number) || 0) - ((a.match_score_pct as number) || 0));
        break;
      case 'price_asc':
        sorted.sort((a, b) => {
          const pa = (a.best_monthly_price as number) ?? Infinity;
          const pb = (b.best_monthly_price as number) ?? Infinity;
          return pa - pb;
        });
        break;
      case 'price_desc':
        sorted.sort((a, b) => {
          const pa = (a.best_monthly_price as number) ?? -Infinity;
          const pb = (b.best_monthly_price as number) ?? -Infinity;
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
      {/* Sort Toolbar */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 1 }}>
        <Typography variant="caption" color="textSecondary">Sortuj:</Typography>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <Select
            value={sortBy}
            onChange={(e: SelectChangeEvent) => setSortBy(e.target.value as SortOption)}
            sx={{ fontSize: '0.85rem' }}
          >
            {SORT_OPTIONS.map(opt => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Results */}
      {sortedResults.map((car) => {
        const vehicleId = car.vehicle_id as string;
        const hasSpecs = car.fuel_type || car.power_hp || car.transmission || car.body_style || car.drive_type;
        const isCalculating = calculatingIds.has(vehicleId);
        const matchedFeatures = (car.matched_features || []) as string[];
        const missingFeatures = (car.missing_features || []) as string[];

        return (
          <Card key={vehicleId} elevation={1} sx={{ borderRadius: 2, transition: 'box-shadow 0.2s', '&:hover': { boxShadow: 4 } }}>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              {/* ── Row 1: Title + Score/Price ── */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                {/* Left: Vehicle Identity */}
                <Box sx={{ flex: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                    <Typography variant="h6" sx={{ lineHeight: 1.2 }}>{car.brand as string} {car.model as string}</Typography>
                    {car.trim_level && (
                      <Chip label={car.trim_level as string} size="small" variant="outlined" color="primary"
                        sx={{ height: 20, fontSize: '0.68rem', fontWeight: 600, borderRadius: '4px' }} />
                    )}
                  </Box>
                  <Typography variant="body2" color="textSecondary" sx={{ mt: 0.25 }}>{car.version as string}</Typography>

                  {/* ── Spec Badges ── */}
                  {hasSpecs && (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                      {car.fuel_type && (
                        <Chip icon={fuelIcon(car.fuel_type as string)} label={car.fuel_type as string} size="small"
                          color={fuelColor(car.fuel_type as string)}
                          variant={fuelColor(car.fuel_type as string) !== 'default' ? 'filled' : 'outlined'}
                          sx={specChipSx} />
                      )}
                      {car.power_hp && (
                        <Chip icon={<SpeedIcon />} label={`${car.power_hp} KM`} size="small" variant="outlined" sx={specChipSx} />
                      )}
                      {car.transmission && (
                        <Chip icon={<SettingsIcon />}
                          label={(car.transmission as string) === 'Automatyczna' ? 'Automat' : car.transmission as string}
                          size="small"
                          color={(car.transmission as string) === 'Automatyczna' ? 'info' : 'default'}
                          variant={(car.transmission as string) === 'Automatyczna' ? 'filled' : 'outlined'}
                          sx={specChipSx} />
                      )}
                      {car.body_style && (
                        <Chip icon={<DirectionsCarIcon />} label={car.body_style as string} size="small" variant="outlined" sx={specChipSx} />
                      )}
                      {car.drive_type && (
                        <Chip label={(car.drive_type as string).replace(/^Napęd\s*/i, '')} size="small"
                          color={(car.drive_type as string).toLowerCase().includes('awd') || (car.drive_type as string).toLowerCase().includes('4x4') ? 'warning' : 'default'}
                          variant={(car.drive_type as string).toLowerCase().includes('awd') || (car.drive_type as string).toLowerCase().includes('4x4') ? 'filled' : 'outlined'}
                          sx={specChipSx} />
                      )}
                      {car.vehicle_class && (car.vehicle_class as string) !== 'Osobowy' && (
                        <Chip label={car.vehicle_class as string} size="small" variant="outlined" color="secondary" sx={specChipSx} />
                      )}
                    </Box>
                  )}

                  {/* ── Catalog Price Breakdown ── */}
                  {(car.base_price_gross || car.total_price_gross) && (
                    <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>
                        Katalog:
                      </Typography>
                      {car.base_price_gross && car.options_price_gross && car.total_price_gross ? (
                        <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                          <strong>{car.base_price_gross as string}</strong>
                          {' + opcje '}
                          <strong>{car.options_price_gross as string}</strong>
                          {' = '}
                          <strong style={{ color: '#1565c0' }}>{car.total_price_gross as string}</strong>
                        </Typography>
                      ) : car.total_price_gross ? (
                        <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#1565c0' }}>
                          {car.total_price_gross as string}
                        </Typography>
                      ) : (
                        <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#1565c0' }}>
                          {car.base_price_gross as string}
                        </Typography>
                      )}
                    </Box>
                  )}
                </Box>

                {/* Right: Score + Pricing */}
                <Box sx={{ textAlign: 'right', ml: 2, flexShrink: 0, minWidth: 170 }}>
                  <Typography
                    variant="h4"
                    sx={{
                      fontWeight: 'bold',
                      color: (car.match_score_pct as number) === 100 ? 'success.main' :
                        (car.match_score_pct as number) >= 80 ? 'info.main' :
                          (car.match_score_pct as number) >= 50 ? 'warning.main' : 'error.main'
                    }}
                  >
                    {car.match_score_pct as number}%
                  </Typography>
                  <Typography variant="caption" color="textSecondary">Dopasowanie</Typography>

                  {/* LTR Price Block — show price if cached, button if not */}
                  {car.has_ltr_cache && car.best_monthly_price ? (
                    <Box sx={{ mt: 0.75, textAlign: 'right', bgcolor: 'primary.main', color: 'primary.contrastText', px: 1.5, py: 0.5, borderRadius: 1 }}>
                      <Typography variant="caption" sx={{ display: 'block', opacity: 0.9 }}>Rata LTR:</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {Number(car.best_monthly_price).toLocaleString('pl-PL')} PLN
                      </Typography>
                      <Typography variant="caption" sx={{ opacity: 0.9 }}>netto / mc</Typography>
                    </Box>
                  ) : (
                    <Box sx={{ mt: 0.75 }}>
                      {isCalculating ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1 }}>
                          <CircularProgress size={16} />
                          <Typography variant="caption" color="textSecondary">Przeliczanie…</Typography>
                        </Box>
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<CalculateIcon />}
                          onClick={() => handleCalculateSingle(vehicleId)}
                          sx={{ fontSize: '0.72rem', textTransform: 'none' }}
                        >
                          Przelicz LTR
                        </Button>
                      )}
                    </Box>
                  )}

                  {/* Business badges row */}
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5, mt: 0.75, flexWrap: 'wrap' }}>
                    {car.suggested_discount_pct != null && (car.suggested_discount_pct as number) > 0 && (
                      <Tooltip title="Sugerowany rabat z bazy dealera">
                        <Chip icon={<LocalOfferIcon />}
                          label={`BD ${car.suggested_discount_pct}%`} size="small"
                          color="success" variant="filled"
                          sx={{ ...specChipSx, fontWeight: 700 }} />
                      </Tooltip>
                    )}
                    {/* Calc params: service type + tire class */}
                    {car.service_cost_type && (
                      <Tooltip title="Typ serwisu użyty w kalkulacji">
                        <Chip icon={<BuildIcon />}
                          label={car.service_cost_type as string}
                          size="small" variant="outlined"
                          sx={{ ...specChipSx, fontSize: '0.65rem' }} />
                      </Tooltip>
                    )}
                    {car.tire_class && (
                      <Tooltip title="Klasa opon użyta w kalkulacji">
                        <Chip label={`Opony: ${car.tire_class}`}
                          size="small" variant="outlined"
                          sx={{ ...specChipSx, fontSize: '0.65rem' }} />
                      </Tooltip>
                    )}
                  </Box>
                </Box>
              </Box>

              {/* ── Row 2: Matched features ── */}
              <Box sx={{ mt: 1.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Spełnione wymagania ({matchedFeatures.length}):</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                  {matchedFeatures.length === 0 && <Typography variant="caption" color="textSecondary">- none -</Typography>}
                  {matchedFeatures.map((f: string) => (
                    <Chip key={f} label={f.replace(/_/g, ' ')} size="small" color="success" variant="outlined" />
                  ))}
                </Box>
              </Box>

              {/* ── Row 3: Missing features ── */}
              {missingFeatures.length > 0 && (
                <Box sx={{ mt: 1.5 }}>
                  <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Brakujące cechy ({missingFeatures.length}):</Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                    {missingFeatures.map((f: string) => (
                      <Chip key={f} label={f.replace(/_/g, ' ')} size="small" color="error" variant="outlined" />
                    ))}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
};
