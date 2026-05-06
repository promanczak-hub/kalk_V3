import React, { useMemo, useState } from 'react';
import { Box, Typography, Chip, Tooltip, IconButton, ToggleButton, ToggleButtonGroup, LinearProgress } from '@mui/material';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import AddIcon from '@mui/icons-material/Add';
import CheckIcon from '@mui/icons-material/Check';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import type { SimilarVehicle, SimilarityReasons } from '../hooks/useBatchData';
import { useOfferCartStore } from '../../stores/offerCartStore';

interface SimilarVehiclesPanelProps {
  vehicles: SimilarVehicle[];
  sourceVehicle: Record<string, unknown>;
  title?: string;
  loadingProgress?: { current: number; total: number } | null;
  marginPct?: number;
  targetDuration?: number;
  targetAnnualMileage?: number;
  matrixActive?: boolean;
}

// ── Source-vehicle helpers ──────────────────────────────────────────────────

interface SourceContext {
  brand: string;
  isDelivery: boolean;
  discountPct: number | null;
  finalPriceNet: number | null;
  /** Source catalog price, normalized to PLN brutto. */
  sourceBaseBrutto: number | null;
}

function parsePriceText(raw: unknown): { value: number; isBrutto: boolean } | null {
  if (raw == null) return null;
  if (typeof raw === 'number' && isFinite(raw)) return { value: raw, isBrutto: true };
  if (typeof raw !== 'string') return null;
  const txt = raw.toLowerCase();
  const num = Number(raw.replace(/[^0-9.,]/g, '').replace(/\s/g, '').replace(',', '.'));
  if (!isFinite(num) || num <= 0) return null;
  const isNetto = txt.includes('netto') || txt.includes('net');
  return { value: num, isBrutto: !isNetto };
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

  // Source catalog price → normalize to brutto
  const parsed = parsePriceText(cs?.base_price);
  const sourceBaseBrutto = parsed
    ? parsed.isBrutto
      ? parsed.value
      : Math.round(parsed.value * 1.23)
    : null;

  return { brand, isDelivery, discountPct, finalPriceNet, sourceBaseBrutto };
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

  if (reasons.equipment_match && reasons.equipment_similarity_pct) {
    tags.push({
      kind: 'match',
      label: `Zbieżne opcje (${Math.round(reasons.equipment_similarity_pct)}%)`,
    });
  }

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

  if (reasons.samar_match && reasons.samar_category && reasons.samar_category !== 'N/A') {
    tags.push({ kind: 'match', label: `Klasa ${reasons.samar_category}` });
  }

  if (reasons.body_match && reasons.body_style && reasons.body_style !== 'N/A') {
    tags.push({ kind: 'match', label: `Nadwozie: ${reasons.body_style}` });
  }

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

  if (!reasons.fuel_match) {
    tags.push({ kind: 'warn', label: 'Inne paliwo / silnik' });
  }
  if (!reasons.drive_match) {
    tags.push({ kind: 'warn', label: 'Inny typ napędu (FWD/AWD)' });
  }

  return tags.slice(0, 5);
}

function TagIcon({ kind }: { kind: ReasonTag['kind'] }) {
  const sx = { fontSize: '0.75rem' };
  switch (kind) {
    case 'match':
      return <CheckIcon sx={{ ...sx, color: '#10B981' }} />;
    case 'approx':
      return <CheckIcon sx={{ ...sx, color: '#F59E0B' }} />;
    case 'warn':
      return <WarningAmberIcon sx={{ ...sx, color: '#F97316' }} />;
    case 'positive':
      return <TrendingUpIcon sx={{ ...sx, color: '#10B981' }} />;
    case 'negative':
      return <TrendingDownIcon sx={{ ...sx, color: '#EF4444' }} />;
  }
}

// ── Spec helpers ───────────────────────────────────────────────────────────────

const isMeaningful = (v: string | null | undefined): v is string =>
  Boolean(v) && v !== 'N/A' && v !== '0' && v !== 'null';

function buildSpecChips(v: SimilarVehicle): string[] {
  const chips: string[] = [];
  if (isMeaningful(v.body_style)) chips.push(v.body_style);
  // Engine label preferred (e.g. "1.5 TSI 150 KM"), else fuel + power
  if (isMeaningful(v.engine_label)) {
    chips.push(v.engine_label);
  } else {
    const parts: string[] = [];
    if (isMeaningful(v.fuel)) parts.push(v.fuel);
    if (v.power_hp && v.power_hp > 0) parts.push(`${v.power_hp} KM`);
    if (parts.length > 0) chips.push(parts.join(' '));
  }
  if (isMeaningful(v.transmission)) chips.push(v.transmission);
  if (isMeaningful(v.drive_type)) chips.push(v.drive_type);
  return chips;
}

interface CatalogPriceInfo {
  candidateNet: number | null;
  candidateBrutto: number | null;
  diffPct: number | null; // signed: + means more expensive than source
  diffAbsBrutto: number | null; // signed PLN brutto
  isCheaper: boolean | null;
}

function computeCatalogPriceInfo(
  v: SimilarVehicle,
  source: SourceContext,
): CatalogPriceInfo {
  const reasons = v.similarity_reasons;
  // backend normalizes base_price to net (line 199 in scoring_search_routes.py)
  const candidateNet = reasons?.base_price ?? null;
  const candidateBrutto = candidateNet != null ? Math.round(candidateNet * 1.23) : null;

  const isCheaper = reasons?.is_cheaper ?? null;
  const pct = reasons?.price_pct_diff ?? null;
  // Signed % (positive => more expensive)
  const diffPct =
    pct == null ? null : isCheaper === true ? -Math.abs(pct) : isCheaper === false ? Math.abs(pct) : pct;

  let diffAbsBrutto: number | null = null;
  if (candidateBrutto != null && source.sourceBaseBrutto != null) {
    diffAbsBrutto = candidateBrutto - source.sourceBaseBrutto;
  }

  return { candidateNet, candidateBrutto, diffPct, diffAbsBrutto, isCheaper };
}

// ── Component ──────────────────────────────────────────────────────────────────

type BrandFilter = 'all' | 'others';

export const SimilarVehiclesPanel: React.FC<SimilarVehiclesPanelProps> = ({
  vehicles,
  sourceVehicle,
  title,
  loadingProgress,
  marginPct,
  targetDuration,
  targetAnnualMileage,
  matrixActive = true,
}) => {
  const addToCart = useOfferCartStore(state => state.addItem);
  const [brandFilter, setBrandFilter] = useState<BrandFilter>('all');
  // Per-row, per-options-category expansion state. Key = `${vehicle_id}:${cat}`.
  const [expandedOptions, setExpandedOptions] = useState<Set<string>>(new Set());

  const toggleOptions = (vehicleId: string, cat: 'factory' | 'service') => {
    const key = `${vehicleId}:${cat}`;
    setExpandedOptions((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const sourceContext = useMemo(() => extractSourceContext(sourceVehicle), [sourceVehicle]);

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
    if (v.best_monthly_price == null) return;
    const dur = targetDuration ?? 0;
    const mil = targetAnnualMileage ?? 0;
    const marginFrac = typeof marginPct === 'number' ? Math.min(marginPct, 99) / 100 : 0;
    const installmentWithMargin = marginFrac > 0 ? v.best_monthly_price / (1 - marginFrac) : v.best_monthly_price;
    const marginTag = `m${Math.round((marginPct ?? 0) * 10)}`;
    const cartId = v.kalkulacja_id
      ? `${v.vehicle_id}_${dur}_${mil}_${v.kalkulacja_id}_${marginTag}`
      : `${v.vehicle_id}_${dur}_${mil}_${marginTag}`;
    addToCart({
      id: cartId,
      brand: v.brand || '',
      model: v.model || '',
      powertrain: v.fuel || '',
      vin_or_config: `Podobny pojazd dla: ${sourceVehicle.brand} ${sourceVehicle.model}`,
      term: dur,
      mileage: mil,
      net_installment: Math.round(installmentWithMargin),
      contribution: 0,
      margin_pct: marginPct ?? 0,
      calculation_data: { ...v, kalkulacja_id: v.kalkulacja_id },
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
          {title || 'Podobne pojazdy'}
        </Typography>

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

      {/* Rows ── one full-width row per vehicle */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {filteredVehicles.map((v, idx) => {
          const rank = idx + 1;
          const category = getSimilarityCategory(v, rank);
          const tags = buildReasonTags(v.similarity_reasons, sourceContext);
          const scoreRounded = v.similarity_score_pct ? Math.round(v.similarity_score_pct) : null;
          const specs = buildSpecChips(v);
          const price = computeCatalogPriceInfo(v, sourceContext);

          const marginFrac = typeof marginPct === 'number' ? Math.min(marginPct, 99) / 100 : 0;
          const monthlyWithMargin =
            v.best_monthly_price != null
              ? marginFrac > 0
                ? v.best_monthly_price / (1 - marginFrac)
                : v.best_monthly_price
              : null;

          return (
            <Box
              key={v.vehicle_id}
              onClick={(e) => {
                e.stopPropagation();
                window.open(`/scoring-details/${v.vehicle_id}`, '_blank');
              }}
              sx={{
                display: 'grid',
                gridTemplateColumns: matrixActive ? { xs: '1fr', md: '1fr auto' } : '1fr',
                alignItems: 'center',
                gap: { xs: 1, md: 2 },
                p: 1.25,
                bgcolor: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.15s',
                '&:hover': {
                  borderColor: '#2563EB',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.08)',
                },
              }}
            >
              {/* Left column ── identity + specs + tags */}
              <Box sx={{ minWidth: 0 }}>
                {/* Header line ── rank, category, brand+model */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                  <Typography
                    variant="caption"
                    sx={{
                      bgcolor: '#F1F5F9',
                      color: '#475569',
                      px: 0.75,
                      py: 0.25,
                      borderRadius: '4px',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      fontFamily: '"Geist Mono", monospace',
                    }}
                  >
                    #{rank}
                  </Typography>
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
                  <Typography
                    sx={{
                      fontWeight: 700,
                      color: '#0F172A',
                      fontSize: '0.85rem',
                      lineHeight: 1.2,
                    }}
                  >
                    {v.brand} {v.model}
                    {v.version ? (
                      <Typography component="span" sx={{ color: '#64748B', fontWeight: 500, ml: 0.5, fontSize: '0.8rem' }}>
                        {v.version}
                      </Typography>
                    ) : null}
                  </Typography>
                </Box>

                {/* Spec chips line ── nadwozie · silnik+moc · skrzynia · napęd */}
                {specs.length > 0 && (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                    {specs.map((label, i) => (
                      <React.Fragment key={i}>
                        <Typography
                          variant="caption"
                          sx={{
                            fontSize: '0.7rem',
                            color: '#475569',
                            fontFamily: '"Geist Mono", monospace',
                            bgcolor: '#F8FAFC',
                            px: 0.75,
                            py: 0.125,
                            borderRadius: '4px',
                            border: '1px solid #E2E8F0',
                          }}
                        >
                          {label}
                        </Typography>
                      </React.Fragment>
                    ))}
                  </Box>
                )}

                {/* Catalog price block ── total + bazowa + opcje fabryczne/serwisowe (parity z VehicleResultCard) */}
                {(v.base_price_net != null || v.total_price_net != null) && (() => {
                  const fmt = (n: number) => n.toLocaleString('pl-PL', { maximumFractionDigits: 0 });
                  const totalNet = v.total_price_net ?? v.base_price_net ?? 0;
                  const totalBrutto = v.total_price_gross ?? v.base_price_gross ?? Math.round(totalNet * 1.23);
                  const hasFactory = (v.factory_options_price_net ?? 0) > 0;
                  const hasService = (v.service_options_price_net ?? 0) > 0;
                  const factoryItems = v.factory_options ?? [];
                  const serviceItems = v.service_options ?? [];
                  const factoryOpen = expandedOptions.has(`${v.vehicle_id}:factory`);
                  const serviceOpen = expandedOptions.has(`${v.vehicle_id}:service`);
                  // Δ vs źródło — porównujemy TOTAL (po opcjach) z bazą źródła w brutto
                  const sourceBrutto = sourceContext.sourceBaseBrutto;
                  const diffPlnBrutto = sourceBrutto != null ? totalBrutto - sourceBrutto : null;
                  const diffPctBrutto = diffPlnBrutto != null && sourceBrutto
                    ? (diffPlnBrutto / sourceBrutto) * 100
                    : null;

                  return (
                    <Box sx={{ mb: 0.5, py: 0.75, px: 1, bgcolor: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                      {/* Header line */}
                      <Box sx={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', flexWrap: 'wrap', gap: 0.5, mb: 0.5 }}>
                        <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#475569', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          Cena katalogowa
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75, flexWrap: 'wrap' }}>
                          <Typography component="span" sx={{ fontWeight: 700, color: '#0F172A', fontSize: '0.75rem', fontFamily: '"Geist Mono", monospace' }}>
                            {fmt(totalNet)} <Typography component="span" sx={{ fontWeight: 400, fontSize: '0.7rem', color: '#475569' }}>PLN netto</Typography>
                          </Typography>
                          <Typography component="span" sx={{ color: '#94A3B8', fontSize: '0.7rem', fontFamily: '"Geist Mono", monospace' }}>
                            ({fmt(totalBrutto)} brutto)
                          </Typography>
                          {diffPctBrutto != null && (
                            <Typography
                              component="span"
                              sx={{
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                fontFamily: '"Geist Mono", monospace',
                                color: diffPctBrutto > 0 ? '#B91C1C' : diffPctBrutto < 0 ? '#047857' : '#64748B',
                              }}
                            >
                              Δ {diffPctBrutto > 0 ? '+' : ''}{diffPctBrutto.toFixed(1)}%
                              {diffPlnBrutto != null && (
                                <> / {diffPlnBrutto > 0 ? '+' : ''}{fmt(diffPlnBrutto)} zł</>
                              )}
                              {' vs źródło'}
                            </Typography>
                          )}
                        </Box>
                      </Box>

                      {/* Breakdown rows */}
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.125 }}>
                        {v.base_price_net != null && (
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', fontFamily: '"Geist Mono", monospace' }}>
                            <Typography component="span" sx={{ color: '#475569', fontSize: '0.7rem' }}>Cena bazowa</Typography>
                            <Typography component="span" sx={{ color: '#0F172A', fontSize: '0.7rem' }}>
                              {fmt(v.base_price_net)} PLN
                              <Typography component="span" sx={{ color: '#94A3B8', ml: 0.75, fontSize: '0.7rem' }}>
                                ({fmt(v.base_price_gross ?? v.base_price_net * 1.23)} brutto)
                              </Typography>
                            </Typography>
                          </Box>
                        )}

                        {hasFactory && (
                          <Box>
                            <Box
                              component="button"
                              type="button"
                              onClick={(e) => { e.stopPropagation(); if (factoryItems.length > 0) toggleOptions(v.vehicle_id, 'factory'); }}
                              sx={{
                                width: '100%',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                background: 'none',
                                border: 0,
                                p: 0,
                                cursor: factoryItems.length > 0 ? 'pointer' : 'default',
                                fontFamily: '"Geist Mono", monospace',
                                fontSize: '0.7rem',
                                textAlign: 'left',
                                color: '#475569',
                                '&:hover': { color: factoryItems.length > 0 ? '#0F172A' : '#475569' },
                              }}
                            >
                              <Typography component="span" sx={{ display: 'flex', alignItems: 'center', gap: 0.25, fontSize: '0.7rem' }}>
                                Opcje fabryczne
                                {factoryItems.length > 0 && (factoryOpen
                                  ? <ExpandLessIcon sx={{ fontSize: '0.85rem' }} />
                                  : <ExpandMoreIcon sx={{ fontSize: '0.85rem' }} />)}
                              </Typography>
                              <Typography component="span" sx={{ color: '#0F172A', fontSize: '0.7rem' }}>
                                + {fmt(v.factory_options_price_net!)} PLN
                                <Typography component="span" sx={{ color: '#94A3B8', ml: 0.75, fontSize: '0.7rem' }}>
                                  ({fmt(v.factory_options_price_gross ?? v.factory_options_price_net! * 1.23)} brutto)
                                </Typography>
                              </Typography>
                            </Box>
                            {factoryOpen && factoryItems.length > 0 && (
                              <Box component="ul" sx={{ m: 0, mt: 0.25, ml: 1.5, p: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 0.125 }}>
                                {factoryItems.map((opt, i) => (
                                  <Box component="li" key={`fo-${i}-${opt.name}`} sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, fontSize: '0.65rem', fontFamily: '"Geist Mono", monospace' }}>
                                    <Typography component="span" sx={{ color: '#475569', fontSize: '0.65rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>· {opt.name}</Typography>
                                    <Typography component="span" sx={{ color: '#475569', fontSize: '0.65rem', whiteSpace: 'nowrap' }}>
                                      {opt.price_net != null
                                        ? <>{fmt(opt.price_net)} PLN <Typography component="span" sx={{ color: '#94A3B8', ml: 0.5, fontSize: '0.65rem' }}>({fmt(opt.price_gross ?? opt.price_net * 1.23)} brutto)</Typography></>
                                        : '—'}
                                    </Typography>
                                  </Box>
                                ))}
                              </Box>
                            )}
                          </Box>
                        )}

                        {hasService && (
                          <Box>
                            <Box
                              component="button"
                              type="button"
                              onClick={(e) => { e.stopPropagation(); if (serviceItems.length > 0) toggleOptions(v.vehicle_id, 'service'); }}
                              sx={{
                                width: '100%',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                background: 'none',
                                border: 0,
                                p: 0,
                                cursor: serviceItems.length > 0 ? 'pointer' : 'default',
                                fontFamily: '"Geist Mono", monospace',
                                fontSize: '0.7rem',
                                textAlign: 'left',
                                color: '#475569',
                                '&:hover': { color: serviceItems.length > 0 ? '#0F172A' : '#475569' },
                              }}
                            >
                              <Typography component="span" sx={{ display: 'flex', alignItems: 'center', gap: 0.25, fontSize: '0.7rem' }}>
                                Opcje serwisowe
                                {serviceItems.length > 0 && (serviceOpen
                                  ? <ExpandLessIcon sx={{ fontSize: '0.85rem' }} />
                                  : <ExpandMoreIcon sx={{ fontSize: '0.85rem' }} />)}
                              </Typography>
                              <Typography component="span" sx={{ color: '#0F172A', fontSize: '0.7rem' }}>
                                + {fmt(v.service_options_price_net!)} PLN
                                <Typography component="span" sx={{ color: '#94A3B8', ml: 0.75, fontSize: '0.7rem' }}>
                                  ({fmt(v.service_options_price_gross ?? v.service_options_price_net! * 1.23)} brutto)
                                </Typography>
                              </Typography>
                            </Box>
                            {serviceOpen && serviceItems.length > 0 && (
                              <Box component="ul" sx={{ m: 0, mt: 0.25, ml: 1.5, p: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 0.125 }}>
                                {serviceItems.map((opt, i) => (
                                  <Box component="li" key={`so-${i}-${opt.name}`} sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, fontSize: '0.65rem', fontFamily: '"Geist Mono", monospace' }}>
                                    <Typography component="span" sx={{ color: '#475569', fontSize: '0.65rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>· {opt.name}</Typography>
                                    <Typography component="span" sx={{ color: '#475569', fontSize: '0.65rem', whiteSpace: 'nowrap' }}>
                                      {opt.price_net != null
                                        ? <>{fmt(opt.price_net)} PLN <Typography component="span" sx={{ color: '#94A3B8', ml: 0.5, fontSize: '0.65rem' }}>({fmt(opt.price_gross ?? opt.price_net * 1.23)} brutto)</Typography></>
                                        : '—'}
                                    </Typography>
                                  </Box>
                                ))}
                              </Box>
                            )}
                          </Box>
                        )}
                      </Box>
                    </Box>
                  );
                })()}

                {/* Reason tags */}
                {tags.length > 0 && (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, columnGap: 1.25 }}>
                    {tags.map((tag, i) => (
                      <Box
                        key={i}
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.4,
                          fontSize: '0.65rem',
                          lineHeight: 1.3,
                          color:
                            tag.kind === 'warn'
                              ? '#C2410C'
                              : tag.kind === 'negative'
                                ? '#B91C1C'
                                : tag.kind === 'positive'
                                  ? '#047857'
                                  : '#475569',
                        }}
                      >
                        <TagIcon kind={tag.kind} />
                        <span>{tag.label}</span>
                      </Box>
                    ))}
                  </Box>
                )}
              </Box>

              {/* Right column ── monthly price, score, add */}
              {matrixActive && (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  pl: { xs: 0, md: 1 },
                  pt: { xs: 0.75, md: 0 },
                  borderTop: { xs: '1px dashed #E2E8F0', md: 'none' },
                  borderLeft: { xs: 'none', md: '1px solid #F1F5F9' },
                  justifyContent: { xs: 'space-between', md: 'flex-end' },
                  flexShrink: 0,
                }}
              >
                <Tooltip
                  title={
                    monthlyWithMargin == null
                      ? `Brak oferty dla setup'u źródła (${v.similarity_reasons?.source_tire_class ?? '—'} / ${v.similarity_reasons?.source_service_type ?? '—'})`
                      : typeof marginPct === 'number' && marginPct > 0
                        ? `Cena z marżą ${marginPct}% dla ${targetDuration ?? '?'}mc / ${(targetAnnualMileage ?? 0).toLocaleString('pl-PL')} km, opony ${v.similarity_reasons?.source_tire_class ?? '—'}, serwis ${v.similarity_reasons?.source_service_type ?? '—'} (źródło: ${v.best_monthly_price?.toLocaleString('pl-PL')} zł netto bez marży)`
                        : `Rata netto bez marży dla ${targetDuration ?? '?'}mc / ${(targetAnnualMileage ?? 0).toLocaleString('pl-PL')} km`
                  }
                  placement="top"
                  arrow
                >
                  <Box sx={{ textAlign: 'right', cursor: 'help' }}>
                    <Typography
                      sx={{
                        fontWeight: 700,
                        fontFamily: '"Geist Mono", "Space Mono", monospace',
                        color: monthlyWithMargin == null ? '#94A3B8' : '#0F172A',
                        fontSize: '0.95rem',
                        lineHeight: 1.1,
                      }}
                    >
                      {monthlyWithMargin == null
                        ? 'Brak oferty'
                        : `${Math.round(monthlyWithMargin).toLocaleString('pl-PL')} zł`}
                    </Typography>
                    <Typography sx={{ fontSize: '0.6rem', color: '#94A3B8', lineHeight: 1 }}>
                      {monthlyWithMargin != null ? '/ mies' : ' '}
                    </Typography>
                  </Box>
                </Tooltip>

                {scoreRounded !== null && (
                  <Tooltip title="Wynik dopasowania cech (zaokrąglony)" placement="top">
                    <Typography
                      sx={{
                        color: scoreRounded >= 90 ? '#059669' : scoreRounded >= 75 ? '#D97706' : '#64748B',
                        fontWeight: 700,
                        fontSize: '0.8rem',
                        fontFamily: '"Geist Mono", "Space Mono", monospace',
                        minWidth: 36,
                        textAlign: 'right',
                      }}
                    >
                      {scoreRounded}%
                    </Typography>
                  </Tooltip>
                )}

                <Tooltip title={v.best_monthly_price == null ? 'Brak ceny dla porównywalnego setupu' : 'Dodaj snapshot do koszyka'}>
                  <span>
                    <IconButton
                      size="small"
                      disabled={v.best_monthly_price == null}
                      onClick={(e) => handleAddToCart(e, v)}
                      sx={{
                        p: 0.5,
                        color: '#2563EB',
                        bgcolor: '#EFF6FF',
                        borderRadius: '6px',
                        '&:hover': { bgcolor: '#DBEAFE' },
                        '&.Mui-disabled': { bgcolor: '#F1F5F9', color: '#CBD5E1' },
                      }}
                    >
                      <AddIcon sx={{ fontSize: '1.1rem' }} />
                    </IconButton>
                  </span>
                </Tooltip>
              </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};
