import React, { useMemo, useState } from 'react';
import { Box, Typography, Card, CardContent, Chip, Tooltip, IconButton, ToggleButton, ToggleButtonGroup, LinearProgress } from '@mui/material';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import AddIcon from '@mui/icons-material/Add';
import CheckIcon from '@mui/icons-material/Check';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import type { SimilarVehicle, SimilarityReasons } from '../hooks/useBatchData';
import { useOfferCartStore } from '../../stores/offerCartStore';

interface SimilarVehiclesPanelProps {
  vehicles: SimilarVehicle[];
  sourceVehicle: Record<string, unknown>;
  title?: string;
  loadingProgress?: { current: number; total: number } | null;
}

// ── Source-vehicle helpers ──────────────────────────────────────────────────

interface SourceContext {
  brand: string;
  isDelivery: boolean;
  discountPct: number | null;
  finalPriceNet: number | null;
}

function extractSourceContext(source: Record<string, unknown>): SourceContext {
  const brand = String(source.brand || '');
  const vehicleClass = String(source.vehicle_class || '').toLowerCase();
  const bodyStyle = String(source.body_style || '').toLowerCase();
  const isDelivery =
    vehicleClass.includes('dostaw') ||
    bodyStyle.includes('furgon') ||
    bodyStyle.includes('podwozie') ||
    bodyStyle.includes('skrzyniow') ||
    bodyStyle.includes('wywrotk');

  const cs = (source.synthesis_data as Record<string, unknown> | undefined)?.card_summary as
    | Record<string, unknown>
    | undefined;
  const discount = cs?.discount as { computed_pct?: number | null } | undefined;
  const discountPct =
    typeof discount?.computed_pct === 'number'
      ? discount.computed_pct
      : typeof cs?.offer_discount_pct === 'string'
        ? Number(cs.offer_discount_pct) || null
        : null;

  const finalPriceRaw = cs?.total_price;
  const finalPriceNet =
    typeof finalPriceRaw === 'string'
      ? Number(finalPriceRaw.replace(/[^0-9.,]/g, '').replace(',', '.')) || null
      : null;

  return { brand, isDelivery, discountPct, finalPriceNet };
}

// ── Similarity Category Logic ────────────────────────────────────────────────

interface SimilarityCategory {
  label: string;
  color: 'success' | 'primary' | 'info' | 'secondary' | 'warning' | 'default';
}

function getSimilarityCategory(v: SimilarVehicle, rank: number): SimilarityCategory {
  const reasons = v.similarity_reasons;
  if (!reasons) return { label: `#${rank} Podobny`, color: 'default' };

  const { samar_match, body_match, price_pct_diff, is_cheaper, equipment_match, is_same_brand } = reasons;
  const isSignificantlyCheaper = Boolean(is_cheaper) && price_pct_diff !== null && price_pct_diff >= 15;
  const isSignificantlyMoreExpensive = is_cheaper === false && price_pct_diff !== null && price_pct_diff >= 15;

  // Hierarchy: most specific → least specific
  if (equipment_match && !is_same_brand) {
    return { label: 'Technologiczny Bliźniak', color: 'success' };
  }
  if (samar_match && body_match && price_pct_diff !== null && price_pct_diff <= 5) {
    return { label: 'Bliźniak', color: 'success' };
  }
  if (isSignificantlyCheaper) {
    return { label: `Tańszy o ${Math.round(price_pct_diff!)}%`, color: 'success' };
  }
  if (isSignificantlyMoreExpensive && samar_match) {
    return { label: 'Klasa wyżej w budżecie', color: 'warning' };
  }
  if (samar_match && body_match) {
    return { label: 'Ta sama klasa i typ', color: 'primary' };
  }
  if (samar_match && !body_match) {
    return { label: 'Ta sama klasa', color: 'primary' };
  }
  if (body_match) {
    return { label: 'Ten sam typ nadwozia', color: 'info' };
  }

  return { label: `#${rank} Podobny`, color: 'default' };
}

// ── Reason Tags ───────────────────────────────────────────────────────────────

interface ReasonTag {
  kind: 'match' | 'approx' | 'warn' | 'positive' | 'negative';
  label: string;
}

function buildReasonTags(
  reasons: SimilarityReasons | null | undefined,
  source: SourceContext,
): ReasonTag[] {
  if (!reasons) return [];

  const tags: ReasonTag[] = [];

  // 1. Equipment match — najsilniejszy sygnał
  if (reasons.equipment_match && reasons.equipment_similarity_pct) {
    tags.push({
      kind: 'match',
      label: `Zbieżne opcje (${Math.round(reasons.equipment_similarity_pct)}%)`,
    });
  }

  // 2. Rabat-aware comparison (V2) — krytyczne dla decyzji zakupowej
  if (
    typeof reasons.discount_pct_diff === 'number' &&
    typeof source.discountPct === 'number' &&
    Math.abs(reasons.discount_pct_diff) >= 1
  ) {
    const better = reasons.discount_pct_diff > 0;
    const sign = better ? '+' : '';
    tags.push({
      kind: better ? 'positive' : 'negative',
      label: `${better ? 'Lepszy' : 'Słabszy'} rabat (${sign}${reasons.discount_pct_diff.toFixed(1)} pp.)`,
    });
  }

  // 3. Cena finalna (po rabacie) jeśli dostępna — bardziej miarodajna niż katalogowa
  if (typeof reasons.final_price_pct_diff === 'number') {
    const diff = reasons.final_price_pct_diff;
    if (diff <= 5) {
      tags.push({ kind: 'match', label: `Cena finalna ±${diff.toFixed(1)}%` });
    } else if (diff <= 15) {
      tags.push({ kind: 'approx', label: `Cena finalna ±${diff.toFixed(1)}%` });
    }
  } else if (typeof reasons.price_pct_diff === 'number' && reasons.price_pct_diff <= 15) {
    // Fallback — cena katalogowa
    const diff = reasons.price_pct_diff;
    tags.push({
      kind: diff <= 5 ? 'match' : 'approx',
      label: `Cena katalogowa ±${diff.toFixed(1)}%`,
    });
  }

  // 4. Klasa SAMAR (tylko jeśli różna od głównej / informacyjnie)
  if (reasons.samar_match && reasons.samar_category && reasons.samar_category !== 'N/A') {
    tags.push({ kind: 'match', label: `Klasa ${reasons.samar_category}` });
  }

  // 5. Nadwozie (tylko gdy wnosi info)
  if (reasons.body_match && reasons.body_style && reasons.body_style !== 'N/A') {
    tags.push({ kind: 'match', label: `Nadwozie: ${reasons.body_style}` });
  }

  // 6. Utility features dla dostawczaków — pokazujemy jako pierwsze
  if (source.isDelivery) {
    if (typeof reasons.payload_kg === 'number') {
      tags.unshift({ kind: 'match', label: `Ładowność ${reasons.payload_kg} kg` });
    }
    if (typeof reasons.cargo_volume_m3 === 'number') {
      tags.unshift({ kind: 'match', label: `Pojemność ${reasons.cargo_volume_m3} m³` });
    }
    if (reasons.body_type && reasons.body_type !== 'N/A') {
      tags.unshift({ kind: 'match', label: `Zabudowa: ${reasons.body_type}` });
    }
  }

  // 7. Diff napędu — TYLKO gdy się różni (sygnał ostrzegawczy)
  if (!reasons.fuel_match) {
    tags.push({ kind: 'warn', label: 'Inny rodzaj napędu' });
  }
  // drive_type diff (FWD vs AWD) — ostrzegawczy
  if (!reasons.drive_match) {
    tags.push({ kind: 'warn', label: 'Inny typ napędu (FWD/AWD)' });
  }

  return tags.slice(0, 4); // 4 tagi maksymalnie (zwiększone z 3 dla rabat-info)
}

// ── Tag rendering ──

function TagIcon({ kind }: { kind: ReasonTag['kind'] }) {
  const sx = { fontSize: '0.7rem' };
  switch (kind) {
    case 'match':
      return <CheckIcon sx={{ ...sx, color: '#10B981' }} />;
    case 'approx':
      // Light-color check for "approximate match"
      return <CheckIcon sx={{ ...sx, color: '#F59E0B' }} />;
    case 'warn':
      return <WarningAmberIcon sx={{ ...sx, color: '#F97316' }} />;
    case 'positive':
      return <TrendingUpIcon sx={{ ...sx, color: '#10B981' }} />;
    case 'negative':
      return <TrendingDownIcon sx={{ ...sx, color: '#EF4444' }} />;
  }
}

// ── Tooltip ────────────────────────────────────────────────────────────────────

const PriceOptionsTooltip: React.FC<{ vehicle: SimilarVehicle }> = ({ vehicle }) => {
  const reasons = vehicle.similarity_reasons;
  const options = reasons?.paid_options || [];
  const basePrice = reasons?.base_price;
  const finalPrice = reasons?.final_price_net;
  const discountPct = reasons?.discount_pct;

  const specChips = [
    vehicle.fuel,
    vehicle.power_hp ? `${vehicle.power_hp} KM` : null,
    vehicle.transmission,
    vehicle.drive_type,
  ].filter((s): s is string => Boolean(s) && s !== 'N/A' && s !== '0');

  return (
    <Box sx={{ p: 0.5, minWidth: 220 }}>
      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5, color: '#fff' }}>
        {vehicle.brand} {vehicle.model}
        {vehicle.version && (
          <Typography component="span" variant="caption" sx={{ opacity: 0.8, ml: 0.5 }}>
            ({vehicle.version})
          </Typography>
        )}
      </Typography>
      {specChips.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1, borderBottom: '1px solid rgba(255,255,255,0.2)', pb: 1 }}>
          {specChips.map((label) => (
            <Chip
              key={label}
              size="small"
              label={label}
              sx={{ height: 16, fontSize: '0.6rem', bgcolor: 'rgba(255,255,255,0.1)', color: '#fff', '& .MuiChip-label': { px: 1 } }}
            />
          ))}
        </Box>
      )}

      {basePrice ? (
        <Box sx={{ mb: 1, borderBottom: '1px solid rgba(255,255,255,0.2)', pb: 0.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
            Cena katalogowa: {basePrice.toLocaleString('pl-PL')} PLN netto
          </Typography>
          {typeof discountPct === 'number' && discountPct > 0 && (
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.85)' }}>
              Po rabacie {discountPct.toFixed(1)}%: {(finalPrice ?? basePrice * (1 - discountPct / 100)).toLocaleString('pl-PL')} PLN netto
            </Typography>
          )}
        </Box>
      ) : null}

      {reasons?.is_fallback_match && (
        <Typography variant="caption" sx={{ color: 'warning.light', display: 'block', mb: 1, fontStyle: 'italic', fontSize: '0.6rem' }}>
          * Dopasowano na podstawie klasy pojazdu (brak ścisłej kategorii)
        </Typography>
      )}

      {options && options.length > 0 ? (
        <>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', display: 'block', mb: 0.5 }}>
            Opcje w tej konfiguracji:
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, maxHeight: 150, overflowY: 'auto' }}>
            {options.map((opt: Record<string, unknown> | string, i: number) => {
              const name = typeof opt === 'string' ? opt : ((opt?.name as string) || (opt?.description as string) || 'Opcja');
              const price = typeof opt === 'object' && opt !== null && 'price_gross' in opt ? opt.price_gross
                : (typeof opt === 'object' && opt !== null && 'price' in opt ? opt.price : null);

              let displayPrice = '';
              if (typeof price === 'number') {
                displayPrice = `${price.toLocaleString('pl-PL')} zł`;
              } else if (typeof price === 'string') {
                displayPrice = price;
              }

              return (
                <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.65rem' }}>{name}</Typography>
                  {displayPrice && (
                    <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                      {displayPrice}
                    </Typography>
                  )}
                </Box>
              );
            })}
          </Box>
        </>
      ) : (
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', fontStyle: 'italic', mt: 0.5 }}>
          Wersja bazowa (brak płatnych opcji)
        </Typography>
      )}
    </Box>
  );
};

// ── Component ──────────────────────────────────────────────────────────────────

type BrandFilter = 'all' | 'others';

export const SimilarVehiclesPanel: React.FC<SimilarVehiclesPanelProps> = ({
  vehicles,
  sourceVehicle,
  title,
  loadingProgress,
}) => {
  const addToCart = useOfferCartStore(state => state.addItem);
  const [brandFilter, setBrandFilter] = useState<BrandFilter>('all');

  const sourceContext = useMemo(() => extractSourceContext(sourceVehicle), [sourceVehicle]);

  // Filter by brand toggle — but keep at least 2 entries by relaxing if needed
  const filteredVehicles = useMemo(() => {
    if (brandFilter === 'all' || vehicles.length === 0) return vehicles;
    const others = vehicles.filter(
      (v) => (v.brand || '').toLowerCase() !== sourceContext.brand.toLowerCase(),
    );
    return others.length >= 2 ? others : vehicles;
  }, [vehicles, brandFilter, sourceContext.brand]);

  const otherBrandsCount = useMemo(() => {
    return vehicles.filter(
      (v) => (v.brand || '').toLowerCase() !== sourceContext.brand.toLowerCase(),
    ).length;
  }, [vehicles, sourceContext.brand]);

  const handleAddToCart = (e: React.MouseEvent, v: SimilarVehicle) => {
    e.stopPropagation();
    addToCart({
      id: crypto.randomUUID(),
      brand: v.brand || '',
      model: v.model || '',
      powertrain: v.fuel || '',
      vin_or_config: `Bliźniacza alternatywa dla: ${sourceVehicle.brand} ${sourceVehicle.model}`,
      term: 0,
      mileage: 0,
      net_installment: v.best_monthly_price || 0,
      contribution: 0,
      margin_pct: 0,
      calculation_data: v,
      standard_equipment: [],
      factory_options: [],
      dealer_options: [],
    });
  };

  if (!vehicles || vehicles.length === 0) {
    return null;
  }

  const showProgress = loadingProgress && loadingProgress.total > 0 && loadingProgress.current < loadingProgress.total;

  return (
    <Box sx={{ mt: 3, p: 2, bgcolor: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5, flexWrap: 'wrap', gap: 1 }}>
        <Typography
          variant="caption"
          sx={{
            color: '#475569',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            fontWeight: 600,
            fontSize: '0.7rem',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            fontFamily: '"Geist", sans-serif',
          }}
        >
          <DirectionsCarIcon sx={{ fontSize: 16, color: '#2563EB' }} />
          {title || 'Alternatywy okiem AI (rekomendacje)'}
        </Typography>

        {/* Brand filter toggle — pokazuj tylko gdy są kandydaci innej marki */}
        {otherBrandsCount > 0 && (
          <ToggleButtonGroup
            value={brandFilter}
            exclusive
            size="small"
            onChange={(_, val) => val && setBrandFilter(val)}
            sx={{ height: 24 }}
          >
            <ToggleButton value="all" sx={{ fontSize: '0.65rem', textTransform: 'none', px: 1.5, py: 0 }}>
              Wszystkie
            </ToggleButton>
            <ToggleButton value="others" sx={{ fontSize: '0.65rem', textTransform: 'none', px: 1.5, py: 0 }}>
              Tylko inne marki ({otherBrandsCount})
            </ToggleButton>
          </ToggleButtonGroup>
        )}
      </Box>

      {/* Loading progress (#8) */}
      {showProgress && (
        <Box sx={{ mb: 1.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#64748B', fontSize: '0.65rem' }}>
              Analizuję {loadingProgress.current}/{loadingProgress.total} zróżnicowanych opcji…
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748B', fontSize: '0.65rem', fontFamily: 'monospace' }}>
              {Math.round((loadingProgress.current / loadingProgress.total) * 100)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={(loadingProgress.current / loadingProgress.total) * 100}
            sx={{ height: 4, borderRadius: 2 }}
          />
        </Box>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(1, 1fr)',
            sm: 'repeat(2, 1fr)',
            md: 'repeat(3, 1fr)',
            lg: 'repeat(5, 1fr)',
          },
          gap: 2,
        }}
      >
        {filteredVehicles.map((v, idx) => {
          const rank = idx + 1;
          const category = getSimilarityCategory(v, rank);
          const tags = buildReasonTags(v.similarity_reasons, sourceContext);
          // Round score to integer (#5)
          const scoreRounded = v.similarity_score_pct ? Math.round(v.similarity_score_pct) : null;

          return (
            <Tooltip
              key={v.vehicle_id}
              title={<PriceOptionsTooltip vehicle={v} />}
              placement="top"
              arrow
              enterDelay={100}
              leaveDelay={300}
              slotProps={{
                popper: {
                  sx: {
                    zIndex: 9999,
                  },
                },
              }}
            >
              <Card
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  bgcolor: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
                  cursor: 'pointer',
                  borderRadius: '8px',
                  transition: 'all 0.15s',
                  '&:hover': {
                    borderColor: '#2563EB',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
                    transform: 'translateY(-1px)',
                  },
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(`/scoring-details/${v.vehicle_id}`, '_blank');
                }}
              >
                <CardContent sx={{ flexGrow: 1, p: 1.25, '&:last-child': { pb: 1.25 } }}>
                  {/* Category chip + rank + AI label */}
                  <Box sx={{ mb: 0.75, display: 'flex', gap: 0.5, flexWrap: 'wrap', alignItems: 'center' }}>
                    {/* Rank badge */}
                    <Typography
                      variant="caption"
                      sx={{
                        bgcolor: '#F1F5F9',
                        color: '#475569',
                        px: 0.75,
                        py: 0.25,
                        borderRadius: '4px',
                        fontSize: '0.6rem',
                        fontWeight: 700,
                        fontFamily: '"Geist Mono", monospace',
                      }}
                    >
                      #{rank}
                    </Typography>
                    {v.ai_label && (
                      <Chip
                        size="small"
                        label={v.ai_label}
                        sx={{
                          height: 20,
                          fontSize: '0.65rem',
                          fontWeight: 600,
                          borderRadius: '9999px',
                          bgcolor: '#DBEAFE',
                          color: '#1E40AF',
                          '& .MuiChip-label': { px: 1.25 },
                        }}
                      />
                    )}
                    <Tooltip
                      title={
                        tags.length > 0
                          ? tags.map((t) => t.label).join('  •  ')
                          : 'Brak szczegółów podobieństwa'
                      }
                      placement="top"
                      arrow
                    >
                      <Chip
                        size="small"
                        label={category.label}
                        color={category.color}
                        sx={{
                          height: 20,
                          fontSize: '0.65rem',
                          fontWeight: 600,
                          borderRadius: '9999px',
                          cursor: 'help',
                          '& .MuiChip-label': { px: 1.25 },
                        }}
                      />
                    </Tooltip>
                  </Box>

                  {/* Reason tags — spójne ikony zamiast emoji (#10) */}
                  {tags.length > 0 && (
                    <Box sx={{ mb: 0.5, display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                      {tags.map((tag, i) => (
                        <Box
                          key={i}
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.5,
                            fontSize: '0.6rem',
                            lineHeight: 1.3,
                            color:
                              tag.kind === 'warn'
                                ? '#C2410C'
                                : tag.kind === 'negative'
                                  ? '#B91C1C'
                                  : tag.kind === 'positive'
                                    ? '#047857'
                                    : 'text.secondary',
                          }}
                        >
                          <TagIcon kind={tag.kind} />
                          <span>{tag.label}</span>
                        </Box>
                      ))}
                    </Box>
                  )}

                  {/* Vehicle name */}
                  <Typography
                    variant="caption"
                    fontWeight="bold"
                    sx={{ display: 'block', mb: 0.5, lineHeight: 1.2, height: 28, overflow: 'hidden' }}
                  >
                    {v.brand} {v.model}
                  </Typography>

                  {/* Price + score + add to cart */}
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      mt: 'auto',
                      pt: 0.75,
                      borderTop: '1px solid',
                      borderColor: 'rgba(0,0,0,0.05)',
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        fontWeight: 700,
                        fontFamily: '"Geist Mono", "Space Mono", monospace',
                        color: '#0F172A',
                        fontSize: '0.7rem',
                      }}
                    >
                      {v.best_monthly_price
                        ? `${v.best_monthly_price.toLocaleString('pl-PL')} zł/mies`
                        : 'Wycena…'}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {scoreRounded !== null && (
                        <Tooltip title="Wynik dopasowania cech (zaokrąglony)" placement="top">
                          <Typography
                            variant="caption"
                            sx={{
                              color: scoreRounded >= 90 ? '#059669' : scoreRounded >= 75 ? '#D97706' : '#64748B',
                              fontWeight: 700,
                              fontSize: '0.65rem',
                              fontFamily: '"Geist Mono", "Space Mono", monospace',
                            }}
                          >
                            {scoreRounded}%
                          </Typography>
                        </Tooltip>
                      )}
                      <Tooltip title="Dodaj alternatywę do koszyka">
                        <IconButton
                          size="small"
                          onClick={(e) => handleAddToCart(e, v)}
                          sx={{
                            p: 0.5,
                            color: '#2563EB',
                            bgcolor: '#EFF6FF',
                            borderRadius: '6px',
                            '&:hover': { bgcolor: '#DBEAFE' }
                          }}
                        >
                          <AddIcon sx={{ fontSize: '1rem' }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
};
