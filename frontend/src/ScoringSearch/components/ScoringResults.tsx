import React, { useMemo, useState, useCallback, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Chip, FormControl, Select, MenuItem,
  Tooltip, Button, CircularProgress, IconButton, Skeleton,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import LocalGasStationIcon from '@mui/icons-material/LocalGasStation';
import BoltIcon from '@mui/icons-material/Bolt';
import SpeedIcon from '@mui/icons-material/Speed';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import SettingsIcon from '@mui/icons-material/Settings';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import CalculateIcon from '@mui/icons-material/Calculate';
import BuildIcon from '@mui/icons-material/Build';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import RefreshIcon from '@mui/icons-material/Refresh';
import { apiFetch } from '../../lib/api';
import type { SearchContext } from '../types';
import { useOfferCartStore } from '../../stores/offerCartStore';

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

/* ── Types ── */

interface PriceForParams {
  duration_months: number | null;
  annual_mileage: number | null;
  monthly_price_net: number | null;
  calculated_at: string | null;
  found: boolean;
}

interface SimilarVehicle {
  vehicle_id: string;
  brand: string | null;
  model: string | null;
  best_monthly_price: number | null;
  similarity_score_pct: number | null;
}

/* ── Sub-hooks ── */

function usePriceForParams(
  vehicleId: string,
  hasCache: boolean,
  durationMonths: number,
  annualMileage: number,
): { price: PriceForParams | null; loading: boolean } {
  const [price, setPrice] = useState<PriceForParams | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!hasCache) return;
    let cancelled = false;

    const doFetch = async () => {
      setLoading(true);
      try {
        const r = await apiFetch(`/api/scoring-search/vehicle/${vehicleId}/price-for-params?duration_months=${durationMonths}&annual_mileage=${annualMileage}`);
        const data: PriceForParams = await r.json();
        if (!cancelled) setPrice(data);
      } catch {
        if (!cancelled) setPrice(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    const handleRefreshEvent = () => {
      if (!cancelled) doFetch();
    };

    window.addEventListener('SCORING_SEARCH_REFRESH', handleRefreshEvent);
    
    doFetch();
    return () => { 
      cancelled = true; 
      window.removeEventListener('SCORING_SEARCH_REFRESH', handleRefreshEvent);
    };
  }, [vehicleId, hasCache, durationMonths, annualMileage]);

  return { price, loading };
}

function usePriceVariants(
  vehicleId: string,
  hasCache: boolean,
  annualMileage: number,
): { variants: PriceForParams[] | null; loading: boolean } {
  const [variants, setVariants] = useState<PriceForParams[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!hasCache) return;
    let cancelled = false;

    const doFetch = async () => {
      setLoading(true);
      try {
        const r = await apiFetch(`/api/scoring-search/vehicle/${vehicleId}/price-variants?annual_mileage=${annualMileage}`);
        const data: PriceForParams[] = await r.json();
        if (!cancelled) setVariants(data);
      } catch {
        if (!cancelled) setVariants(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    doFetch();
    return () => { cancelled = true; };
  }, [vehicleId, hasCache, annualMileage]);

  return { variants, loading };
}

function useSimilarVehicles(vehicleId: string, durationMonths?: number, annualMileage?: number): {
  similar: SimilarVehicle[];
  loading: boolean;
} {
  const [similar, setSimilar] = useState<SimilarVehicle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    
    const doFetch = async () => {
      setLoading(true);
      const params = new URLSearchParams({ limit: '3' });
      if (durationMonths) params.append('duration_months', durationMonths.toString());
      if (annualMileage) params.append('annual_mileage', annualMileage.toString());
      
      try {
        const r = await apiFetch(`/api/scoring-search/vehicle/${vehicleId}/similar?${params.toString()}`);
        const data: SimilarVehicle[] = await r.json();
        if (!cancelled) setSimilar(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setSimilar([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    doFetch();
    return () => { cancelled = true; };
  }, [vehicleId, durationMonths, annualMileage]);

  return { similar, loading };
}

/* ── Card sub-components ── */

interface LtrPriceBlockProps {
  vehicleId: string;
  hasCache: boolean;
  bestMonthlyPrice: number | null;
  durationMonths: number;
  annualMileage: number;
  isCalculating: boolean;
  onCalculate: (id: string) => void;
  suggestedDiscountPct?: number | null;
  marginPct?: number;
}

const LtrPriceBlock: React.FC<LtrPriceBlockProps> = ({
  vehicleId, hasCache, bestMonthlyPrice, durationMonths, annualMileage,
  isCalculating, onCalculate, suggestedDiscountPct, marginPct = 0,
}) => {
  const { price, loading } = usePriceForParams(
    vehicleId, !!hasCache, durationMonths, annualMileage
  );
  const { variants } = usePriceVariants(
    vehicleId, !!hasCache, annualMileage
  );

  if (!hasCache || !bestMonthlyPrice) {
    return (
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
            onClick={() => onCalculate(vehicleId)}
            sx={{ fontSize: '0.72rem', textTransform: 'none' }}
          >
            Przelicz LTR
          </Button>
        )}
      </Box>
    );
  }

  const rawPrice = price?.found && price.monthly_price_net != null
    ? price.monthly_price_net
    : bestMonthlyPrice;
  const m = Math.min(marginPct, 99) / 100.0;
  const displayPrice = rawPrice != null && m < 1.0 ? rawPrice / (1.0 - m) : null;

  const paramLabel = price?.found && price.duration_months != null && price.annual_mileage != null
    ? `${price.duration_months} mc / ${((price.annual_mileage * price.duration_months / 12) / 1000).toFixed(0)}k km`
    : null;

  return (
    <Box sx={{ mt: 0.75, textAlign: 'right', bgcolor: 'primary.main', color: 'primary.contrastText', px: 1.5, py: 1, borderRadius: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" sx={{ opacity: 0.9 }}>Rata LTR:</Typography>
        {suggestedDiscountPct !== undefined && suggestedDiscountPct !== null && (
          <Box
            sx={{
              display: 'inline-block',
              fontSize: '0.65rem',
              fontWeight: 600,
              bgcolor: 'rgba(255,255,255,0.2)',
              px: 0.75,
              py: 0.25,
              borderRadius: 1,
            }}
          >
            {suggestedDiscountPct > 0 ? `Rabat: ${suggestedDiscountPct}%` : 'Cena katalogowa'}
          </Box>
        )}
      </Box>
      {loading ? (
        <Skeleton variant="text" width={80} sx={{ ml: 'auto', bgcolor: 'rgba(255,255,255,0.2)' }} />
      ) : (
        <Typography variant="body1" sx={{ fontWeight: 'bold', mt: 0.5 }}>
          {Number(displayPrice).toLocaleString('pl-PL')} PLN
        </Typography>
      )}
      {paramLabel && !loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
          <Tooltip title="Cena dla wybranych parametrów">
            <Typography
              variant="caption"
              sx={{ opacity: 0.85, fontSize: '0.68rem', cursor: 'default' }}
            >
              {paramLabel}
            </Typography>
          </Tooltip>

          {/* Cache Date & Refresh */}
          {price?.calculated_at && (
            <Box sx={{ display: 'flex', alignItems: 'center', ml: 0.5, borderLeft: '1px solid rgba(255,255,255,0.3)', pl: 0.5 }}>
              <Tooltip title={`Ostatnia aktualizacja: ${new Date(price.calculated_at).toLocaleString('pl-PL')}. Kliknij, aby odświeżyć.`}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, cursor: 'pointer', '&:hover': { opacity: 1 } }} onClick={() => onCalculate(vehicleId)}>
                  <Typography variant="caption" sx={{ fontSize: '0.6rem', opacity: 0.7 }}>
                    {new Date(price.calculated_at).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit' })} {new Date(price.calculated_at).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })}
                  </Typography>
                  {isCalculating ? (
                    <CircularProgress size={10} color="inherit" thickness={6} />
                  ) : (
                    <RefreshIcon sx={{ fontSize: 10, opacity: 0.7 }} />
                  )}
                </Box>
              </Tooltip>
            </Box>
          )}
        </Box>
      )}
      {!paramLabel && !loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
          <Typography variant="caption" sx={{ opacity: 0.9 }}>netto / mc</Typography>
          
          {/* Cache Date & Refresh (Small fallback) */}
          {price?.calculated_at && (
            <Tooltip title={`Ostatnia aktualizacja: ${new Date(price.calculated_at).toLocaleString('pl-PL')}. Kliknij, aby odświeżyć.`}>
              <IconButton 
                size="small" 
                onClick={() => onCalculate(vehicleId)} 
                sx={{ color: 'inherit', p: 0.25, ml: 0.5, opacity: 0.6, '&:hover': { opacity: 1 } }}
                disabled={isCalculating}
              >
                {isCalculating ? <CircularProgress size={10} color="inherit" /> : <RefreshIcon sx={{ fontSize: 10 }} />}
              </IconButton>
            </Tooltip>
          )}
        </Box>
      )}

      {/* Rendering price variants */}
      {variants && variants.length > 0 && (
        <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid rgba(255,255,255,0.2)', display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {variants.filter(v => v.duration_months !== durationMonths).map(v => {
            const variantPrice = v.monthly_price_net != null && m < 1.0 ? v.monthly_price_net / (1.0 - m) : 0;
            return (
              <Typography key={v.duration_months} variant="caption" sx={{ fontSize: '0.65rem', display: 'flex', justifyContent: 'space-between', opacity: 0.85 }}>
                <span>{v.duration_months}mc/{( (v.annual_mileage || 0) * (v.duration_months || 0) / 12 / 1000).toFixed(0)}k:</span>
                <span style={{ fontWeight: 600 }}>{Number(variantPrice).toLocaleString('pl-PL')} PLN</span>
              </Typography>
            );
          })}
        </Box>
      )}
    </Box>
  );
};

interface SimilarVehiclesSectionProps {
  vehicleId: string;
  durationMonths?: number;
  annualMileage?: number;
  marginPct?: number;
}

const SimilarVehiclesSection: React.FC<SimilarVehiclesSectionProps> = ({ vehicleId, durationMonths, annualMileage, marginPct = 0 }) => {
  const { similar, loading } = useSimilarVehicles(vehicleId, durationMonths, annualMileage);

  if (loading) {
    return (
      <Box sx={{ mt: 1.5 }}>
        <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <PeopleAltIcon sx={{ fontSize: 14 }} /> Podobne oferty:
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
          {[1, 2, 3].map((i) => <Skeleton key={i} variant="rounded" width={140} height={24} />)}
        </Box>
      </Box>
    );
  }

  if (!similar.length) return null;

  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <PeopleAltIcon sx={{ fontSize: 14 }} /> Podobne oferty:
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
        {similar.map((s) => {
          const sPrice = s.best_monthly_price != null ? (s.best_monthly_price as number) * (1 + marginPct / 100) : null;
          const label = [
            `${s.brand ?? ''} ${s.model ?? ''}`.trim(),
            sPrice != null
              ? `${Number(sPrice).toLocaleString('pl-PL')} PLN/mc`
              : null,
            s.similarity_score_pct != null ? `${s.similarity_score_pct}%` : null,
          ]
            .filter(Boolean)
            .join(' | ');

          const score = s.similarity_score_pct ?? 0;
          let chipColor: 'success' | 'info' | 'default' = 'default';
          let chipSx = { fontSize: '0.65rem', maxWidth: 280, fontWeight: 400, opacity: 1 };

          if (score >= 75) {
            chipColor = 'success';
            chipSx = { ...chipSx, fontWeight: 600 };
          } else if (score >= 40) {
            chipColor = 'info';
          } else {
            chipColor = 'default';
            chipSx = { ...chipSx, opacity: 0.6 };
          }

          return (
            <Tooltip key={s.vehicle_id} title={`Podobieństwo: ${s.similarity_score_pct ?? '?'}%`}>
              <Chip
                label={label}
                size="small"
                variant="outlined"
                color={chipColor}
                component="a"
                href={`/?highlight=${s.vehicle_id}`}
                target="_blank"
                clickable
                sx={chipSx}
              />
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
};

/* ── Main component ── */

interface ScoringResultsProps {
  results: Record<string, unknown>[];
  loading: boolean;
  searchContext: SearchContext;
}

export const ScoringResults: React.FC<ScoringResultsProps> = ({ results, loading, searchContext }) => {
  const [sortBy, setSortBy] = useState<SortOption>('score_desc');
  const [calculatingIds, setCalculatingIds] = useState<Set<string>>(new Set());
  const addToCart = useOfferCartStore(state => state.addItem);

  let targetDuration = Math.round(
    (searchContext.duration_months_range[0] + searchContext.duration_months_range[1]) / 2
  );
  let targetTotalMileage = Math.round(
    (searchContext.total_mileage_range[0] + searchContext.total_mileage_range[1]) / 2
  );

  if (searchContext.exact_mode) {
    targetDuration = searchContext.exact_duration_months;
    targetTotalMileage = searchContext.exact_total_mileage;
  }

  const targetAnnualMileage = Math.round((targetTotalMileage * 12) / targetDuration);

  const handleCalculateSingle = useCallback(async (vehicleId: string) => {
    setCalculatingIds(prev => new Set(prev).add(vehicleId));
    try {
      const res = await apiFetch('/api/scoring-search/cache/refresh-matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vehicle_ids: [vehicleId] }),
      });
      const data = await res.json();
      const jobId = data.job_id;
      
      if (jobId) {
        const pollTimer = setInterval(async () => {
          try {
            const pollRes = await apiFetch(`/api/scoring-search/cache/progress/${jobId}`);
            if (!pollRes.ok) throw new Error('Poll failed');
            const pollData = await pollRes.json();
            if (pollData.status === 'done' || pollData.status === 'error' || pollData.status === 'unknown') {
              clearInterval(pollTimer);
              setCalculatingIds(prev => {
                const next = new Set(prev);
                next.delete(vehicleId);
                return next;
              });
              // Refresh triggering on window
              window.dispatchEvent(new CustomEvent('SCORING_SEARCH_REFRESH'));
            }
          } catch {
            clearInterval(pollTimer);
            setCalculatingIds(prev => {
              const next = new Set(prev);
              next.delete(vehicleId);
              return next;
            });
          }
        }, 1500);
      } else {
        setCalculatingIds(prev => {
          const next = new Set(prev);
          next.delete(vehicleId);
          return next;
        });
      }
    } catch (err) {
      console.error('Failed to trigger calculation for', vehicleId, err);
      setCalculatingIds(prev => {
        const next = new Set(prev);
        next.delete(vehicleId);
        return next;
      });
    }
  }, []);

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
              <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
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
                    {!!car.trim_level && car.trim_level !== 'Brak' && (
                      <Chip label={car.trim_level as string} size="small" variant="outlined" color="primary"
                        sx={{ height: 20, fontSize: '0.68rem', fontWeight: 600, borderRadius: '4px' }} />
                    )}
                    {(!!car.configuration_code || !!car.offer_number) && (
                      <Chip label={(car.configuration_code as string) || (car.offer_number as string)} size="small" variant="outlined"
                        sx={{ height: 20, fontSize: '0.68rem', fontWeight: 600, borderRadius: '4px', fontFamily: '"Geist Mono", monospace', color: 'slate.600', borderColor: 'slate.300', bgcolor: 'slate.50' }} />
                    )}
                    <Tooltip title="Sprawdź rekord w Ekstrakcji Danych">
                      <IconButton
                        size="small"
                        href={`/?highlight=${vehicleId}`}
                        target="_blank"
                        sx={{ color: 'text.secondary', ml: 'auto' }}
                      >
                        <OpenInNewIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                  <Typography variant="body2" color="textSecondary" sx={{ mt: 0.25 }}>{car.version as string}</Typography>

                  {/* ── Spec Badges ── */}
                  {!!hasSpecs && (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                      {!!car.fuel_type && (
                        <Chip icon={fuelIcon(car.fuel_type as string)} label={car.fuel_type as string} size="small"
                          color={fuelColor(car.fuel_type as string)}
                          variant={fuelColor(car.fuel_type as string) !== 'default' ? 'filled' : 'outlined'}
                          sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                      )}
                      {!!car.power_hp && (
                        <Chip icon={<SpeedIcon />} label={`${car.power_hp} KM`} size="small" variant="outlined" sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                      )}
                      {!!car.transmission && (
                        <Chip icon={<SettingsIcon />}
                          label={(car.transmission as string) === 'Automatyczna' ? 'Automat' : car.transmission as string}
                          size="small"
                          color={(car.transmission as string) === 'Automatyczna' ? 'info' : 'default'}
                          variant={(car.transmission as string) === 'Automatyczna' ? 'filled' : 'outlined'}
                          sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                      )}
                      {!!car.body_style && (
                        <Chip icon={<DirectionsCarIcon />} label={car.body_style as string} size="small" variant="outlined" sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                      )}
                      {!!car.drive_type && (
                        <Chip label={(car.drive_type as string).replace(/^Napęd\s*/i, '')} size="small"
                          color={(car.drive_type as string).toLowerCase().includes('awd') || (car.drive_type as string).toLowerCase().includes('4x4') ? 'warning' : 'default'}
                          variant={(car.drive_type as string).toLowerCase().includes('awd') || (car.drive_type as string).toLowerCase().includes('4x4') ? 'filled' : 'outlined'}
                          sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                      )}
                      {!!car.vehicle_class && (car.vehicle_class as string) !== 'Osobowy' && (
                        <Chip label={car.vehicle_class as string} size="small" variant="outlined" color="secondary" sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                      )}
                    </Box>
                  )}

                  {/* ── Catalog Price Breakdown ── */}
                  {!!(car.base_price_gross || car.total_price_gross) && (
                    <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>Katalog:</Typography>
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

                  {/* LTR Price Block — price for selected params */}
                  <LtrPriceBlock
                    vehicleId={vehicleId}
                    hasCache={!!(car.has_ltr_cache)}
                    bestMonthlyPrice={(car.best_monthly_price as number) || null}
                    durationMonths={targetDuration}
                    annualMileage={targetAnnualMileage}
                    isCalculating={isCalculating}
                    onCalculate={handleCalculateSingle}
                    suggestedDiscountPct={(car.suggested_discount_pct as number) || 0}
                    marginPct={searchContext.margin_pct || 0}
                  />

                  {/* Business badges row */}
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5, mt: 0.75, flexWrap: 'wrap' }}>
                    {!!car.has_ltr_cache && (
                      <Button
                        size="small"
                        variant="contained"
                        color="secondary"
                        startIcon={<ShoppingCartIcon sx={{ fontSize: '14px !important' }} />}
                        sx={{ fontSize: '0.65rem', height: 24, textTransform: 'none', px: 1, minWidth: 0, boxShadow: 'none' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          const basePrice = (car.best_monthly_price as number) || 0;
                          const finalPrice = basePrice * (1 + (searchContext.margin_pct || 0) / 100);
                          addToCart({
                            id: crypto.randomUUID(),
                            brand: (car.brand as string) || '',
                            model: (car.model as string) || '',
                            powertrain: (car.fuel_type as string) || '',
                            vin_or_config: (car.configuration_code as string) || (car.offer_number as string) || 'Brak',
                            term: targetDuration,
                            mileage: targetAnnualMileage,
                            net_installment: finalPrice,
                            contribution: 0,
                            system_recommendation: typeof car.match_score_pct === 'number' && car.match_score_pct >= 90 ? 'Najlepsze dopasowanie' : undefined,
                            standard_equipment: [],
                            factory_options: [],
                            dealer_options: [],
                            calculation_data: car,
                          });
                        }}
                      >
                        Dodaj do oferty
                      </Button>
                    )}
                    {!!car.suggested_discount_pct && (car.suggested_discount_pct as number) > 0 && (
                      <Tooltip title="Sugerowany rabat z bazy dealera">
                        <Chip icon={<LocalOfferIcon />}
                          label={`BD ${car.suggested_discount_pct}%`} size="small"
                          color="success" variant="filled"
                          sx={{ fontWeight: 700, '& .MuiChip-icon': { fontSize: 14 }, height: 24 }} />
                      </Tooltip>
                    )}
                    {(!!car.service_cost_type || !!car.tire_class) && (
                      <Tooltip title="Parametry użyte w kalkulacji">
                        <Chip icon={<BuildIcon />}
                          label={[
                            car.service_cost_type ? `Serwis: ${car.service_cost_type}` : null,
                            car.tire_class ? `Opony: ${car.tire_class}` : null
                          ].filter(Boolean).join(' | ')}
                          size="small" variant="outlined"
                          sx={{ fontSize: '0.65rem', '& .MuiChip-icon': { fontSize: 14 }, height: 24 }} />
                      </Tooltip>
                    )}
                  </Box>
                </Box>
              </Box>

              {/* ── Row 2: Matched features ── */}
              {matchedFeatures.length > 0 && (
                <Box sx={{ mt: 1.5 }}>
                  <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Spełnione wymagania ({matchedFeatures.length}):</Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                    {matchedFeatures.map((f: string) => (
                      <Chip key={f} label={f.replace(/_/g, ' ')} size="small" color="success" variant="outlined" />
                    ))}
                  </Box>
                </Box>
              )}

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

              {/* ── Row 4: Similar vehicles ── */}
              <SimilarVehiclesSection 
                vehicleId={vehicleId} 
                marginPct={searchContext.margin_pct || 0}
              />

            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
};
