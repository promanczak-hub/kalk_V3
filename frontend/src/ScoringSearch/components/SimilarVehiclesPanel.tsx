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
import { KalkulacjaParamsRow } from './Results/KalkulacjaParamsRow';

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

// ── Headline chip ────────────────────────────────────────────────────────────
// Only emitted for genuinely informative cases. The right-side score% already
// conveys "how similar" — a chip on top of that should add information the
// score alone can't: cross-brand matches, true twins, etc. For the common case
// (same brand, same model, decent score) we emit nothing and let the score
// number + reason tags speak.

interface SimilarityCategory {
  label: string;
  color: 'success' | 'primary' | 'info' | 'secondary' | 'warning' | 'default';
}

function getHeadlineChip(v: SimilarVehicle): SimilarityCategory | null {
  const reasons = v.similarity_reasons;
  if (!reasons) return null;

  const score = v.similarity_score_pct ?? 0;
  const {
    samar_match,
    body_match,
    fuel_match,
    drive_match,
    is_same_brand,
    equipment_match,
    price_pct_diff,
  } = reasons;

  // Cross-brand technology twin: very high equipment overlap, different brand
  if (equipment_match && !is_same_brand && score >= 80) {
    return { label: 'Technologiczny Bliźniak', color: 'success' };
  }

  // Strict twin: every core dimension lines up AND price is within ~5%
  const allCoreMatch = samar_match && body_match && fuel_match && drive_match;
  const priceVeryClose = price_pct_diff !== null && price_pct_diff <= 5;
  if (allCoreMatch && priceVeryClose && score >= 92) {
    return { label: 'Bliźniak', color: 'success' };
  }

  // Genuinely competitive cross-brand alternative
  if (!is_same_brand && score >= 85) {
    return { label: 'Inna marka', color: 'primary' };
  }

  return null;
}

// ── Reason Tags ───────────────────────────────────────────────────────────────
// Each match tag carries a `weight` reflecting how much signal it adds; we
// sort and take the top N so cluttered rows show only the most informative
// reasons. Warnings (mismatches the dealer must see) are always rendered.

interface ReasonTag {
  kind: 'match' | 'approx' | 'warn' | 'positive' | 'negative';
  label: string;
  weight?: number;
}

const MAX_MATCH_TAGS = 4;

function buildReasonTags(
  reasons: SimilarityReasons | null | undefined,
  source: SourceContext,
): ReasonTag[] {
  if (!reasons) return [];

  const matches: ReasonTag[] = [];
  const warnings: ReasonTag[] = [];

  // Equipment overlap — most concrete "are these the same kind of car" signal
  if (reasons.equipment_similarity_pct != null) {
    const pct = Math.round(reasons.equipment_similarity_pct);
    if (pct >= 60) {
      matches.push({ kind: 'match', label: `Zbieżne opcje (${pct}%)`, weight: pct });
    }
  }

  // SAMAR class — most specific identification of segment
  if (reasons.samar_match && reasons.samar_category && reasons.samar_category !== 'N/A') {
    matches.push({ kind: 'match', label: `Klasa ${reasons.samar_category}`, weight: 95 });
  }

  // Body style match
  if (reasons.body_match && reasons.body_style && reasons.body_style !== 'N/A') {
    matches.push({ kind: 'match', label: `Nadwozie: ${reasons.body_style}`, weight: 80 });
  }

  // Fuel/drive matches — only emit as ✓ when worth saying; warnings handled below
  if (reasons.fuel_match) {
    matches.push({ kind: 'match', label: 'Ten sam silnik / paliwo', weight: 65 });
  }
  if (reasons.drive_match) {
    matches.push({ kind: 'match', label: 'Ten sam typ napędu', weight: 55 });
  }

  // Price proximity — apple-to-apple
  if (reasons.price_pct_diff !== null && reasons.price_pct_diff <= 5) {
    matches.push({ kind: 'match', label: `Cena ±${reasons.price_pct_diff.toFixed(1)}%`, weight: 75 });
  }

  // Discount diff — positional (always relevant when meaningful)
  if (
    typeof reasons.discount_pct_diff === 'number' &&
    typeof source.discountPct === 'number' &&
    Math.abs(reasons.discount_pct_diff) >= 1
  ) {
    const better = reasons.discount_pct_diff > 0;
    const sign = better ? '+' : '';
    matches.push({
      kind: better ? 'positive' : 'negative',
      label: `${better ? 'Lepszy' : 'Słabszy'} rabat (${sign}${reasons.discount_pct_diff.toFixed(1)} pp.)`,
      weight: 90,
    });
  }

  // Delivery-vehicle specifics — domain-critical, always near the top
  if (source.isDelivery) {
    if (typeof reasons.payload_kg === 'number') {
      matches.push({ kind: 'match', label: `Ładowność ${reasons.payload_kg} kg`, weight: 100 });
    }
    if (typeof reasons.cargo_volume_m3 === 'number') {
      matches.push({ kind: 'match', label: `Pojemność ${reasons.cargo_volume_m3} m³`, weight: 100 });
    }
    if (reasons.body_type && reasons.body_type !== 'N/A') {
      matches.push({ kind: 'match', label: `Zabudowa: ${reasons.body_type}`, weight: 100 });
    }
  }

  if (!reasons.fuel_match) {
    warnings.push({ kind: 'warn', label: 'Inne paliwo / silnik' });
  }
  if (!reasons.drive_match) {
    warnings.push({ kind: 'warn', label: 'Inny typ napędu (FWD/AWD)' });
  }

  matches.sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0));
  return [...matches.slice(0, MAX_MATCH_TAGS), ...warnings];
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

// ── Expandable details block ─────────────────────────────────────────────────
// Surfaces pricing context that the row summary doesn't show: catalog price &
// Δ vs source, applied discount & Δ vs source, derived offer price after
// discount, the matrix the rate was priced for, and whether the candidate
// really has the same setup as the source (apple-to-apple) or is a fallback.

interface DetailsBlockProps {
  v: SimilarVehicle;
  source: SourceContext;
  fallbackDuration?: number;
  fallbackAnnualMileage?: number;
}

const fmtPLN = (n: number) => n.toLocaleString('pl-PL', { maximumFractionDigits: 0 });

const DetailsBlock: React.FC<DetailsBlockProps> = ({ v, source, fallbackDuration, fallbackAnnualMileage }) => {
  const r = v.similarity_reasons;
  if (!r) return null;

  const candNet = r.base_price ?? null;
  const candBrutto = candNet != null ? Math.round(candNet * 1.23) : null;
  const discountPct = r.discount_pct ?? null;
  const discountDiff = r.discount_pct_diff ?? null;
  const finalNet = candNet != null && discountPct != null
    ? Math.round(candNet * (1 - discountPct / 100))
    : null;

  // Matrix the rate was priced for
  const dur = r.matched_duration_months ?? fallbackDuration ?? null;
  const annual = r.matched_annual_mileage ?? fallbackAnnualMileage ?? null;
  const contractKm = dur != null && annual != null ? Math.round((dur * annual) / 12) : null;
  const tire = r.source_tire_class || null;
  const service = r.source_service_type || null;
  const setupOk = r.setup_match === true;

  // Δ vs source — computed in brutto to align with the existing Cena kat. line
  const diffPlnBrutto = candBrutto != null && source.sourceBaseBrutto != null
    ? candBrutto - source.sourceBaseBrutto
    : null;
  const diffPctBrutto = diffPlnBrutto != null && source.sourceBaseBrutto
    ? (diffPlnBrutto / source.sourceBaseBrutto) * 100
    : null;

  const Row: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
    <Box sx={{ display: 'flex', gap: 1, fontSize: '0.7rem', lineHeight: 1.5 }}>
      <Typography component="span" sx={{ color: '#64748B', fontWeight: 500, minWidth: 110, fontSize: '0.7rem' }}>
        {label}
      </Typography>
      <Typography component="span" sx={{ color: '#0F172A', fontFamily: '"Geist Mono", monospace', fontSize: '0.7rem' }}>
        {children}
      </Typography>
    </Box>
  );

  return (
    <Box
      sx={{
        gridColumn: '1 / -1',
        mt: 1,
        pt: 1,
        borderTop: '1px dashed #E2E8F0',
        display: 'flex',
        flexDirection: 'column',
        gap: 0.25,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {candNet != null && (
        <Row label="Cena katalogowa">
          <strong>{fmtPLN(candNet)} PLN</strong> netto{' '}
          {candBrutto != null && (
            <Typography component="span" sx={{ color: '#94A3B8', fontSize: '0.7rem', fontFamily: 'inherit' }}>
              ({fmtPLN(candBrutto)} brutto)
            </Typography>
          )}
          {diffPctBrutto != null && (
            <Typography
              component="span"
              sx={{
                ml: 0.75,
                fontSize: '0.7rem',
                fontFamily: 'inherit',
                color: diffPctBrutto > 0 ? '#B91C1C' : diffPctBrutto < 0 ? '#047857' : '#64748B',
              }}
            >
              Δ {diffPctBrutto > 0 ? '+' : ''}{diffPctBrutto.toFixed(1)}%
              {diffPlnBrutto != null && (
                <> / {diffPlnBrutto > 0 ? '+' : ''}{fmtPLN(diffPlnBrutto)} zł vs źródło</>
              )}
            </Typography>
          )}
        </Row>
      )}

      {discountPct != null && (
        <Row label="Rabat oferty">
          <strong>{discountPct.toFixed(1)}%</strong>
          {discountDiff != null && Math.abs(discountDiff) >= 0.1 && (
            <Typography
              component="span"
              sx={{
                ml: 0.75,
                fontSize: '0.7rem',
                fontFamily: 'inherit',
                color: discountDiff > 0 ? '#047857' : '#B91C1C',
              }}
            >
              ({discountDiff > 0 ? '+' : ''}{discountDiff.toFixed(1)} pp vs źródło)
            </Typography>
          )}
        </Row>
      )}

      {finalNet != null && (
        <Row label="Cena ofertowa">
          <strong>{fmtPLN(finalNet)} PLN</strong> netto{' '}
          <Typography component="span" sx={{ color: '#94A3B8', fontSize: '0.7rem', fontFamily: 'inherit' }}>
            (po rabacie)
          </Typography>
        </Row>
      )}

      <Row label="Matrix raty">
        {dur != null ? `${dur} mc` : '? mc'}
        {contractKm != null && (
          <>
            {' · '}
            <strong>{fmtPLN(contractKm)} km</strong>
            <Typography component="span" sx={{ color: '#94A3B8', fontSize: '0.7rem', fontFamily: 'inherit' }}>
              {' '}kontrakt
            </Typography>
          </>
        )}
        {tire && <> · opony <strong>{tire}</strong></>}
        {service && <> · serwis <strong>{service}</strong></>}
      </Row>

      <Row label="Setup">
        {setupOk ? (
          <Typography component="span" sx={{ color: '#047857', fontSize: '0.7rem', fontFamily: 'inherit' }}>
            ✓ Apple-to-apple (ten sam matrix co źródło)
          </Typography>
        ) : (
          <Typography component="span" sx={{ color: '#C2410C', fontSize: '0.7rem', fontFamily: 'inherit' }}>
            ⚠ Brak ceny dla matrixa źródła — fallback / brak oferty
          </Typography>
        )}
      </Row>
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
  marginPct,
  targetDuration,
  targetAnnualMileage,
  matrixActive = true,
}) => {
  const addToCart = useOfferCartStore(state => state.addItem);
  const [brandFilter, setBrandFilter] = useState<BrandFilter>('all');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

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
    return vehicles.filter(
      (v) => (v.brand || '').toLowerCase() !== sourceContext.brand.toLowerCase(),
    );
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
      // TODO(types): SimilarVehicle has no configuration_code; fall back to vehicle_id.
      vin_or_config: v.vehicle_id || '',
      term: dur,
      mileage: mil,
      net_installment: Math.round(installmentWithMargin),
      contribution: 0,
      margin_pct: marginPct ?? 0,
      calculation_data: { ...v, kalkulacja_id: v.kalkulacja_id },
      standard_equipment: [],
      factory_options: [],
      dealer_options: [],
      // Freeze the candidate kalkulacja's snapshot at add time. Source-side
      // tire_class/service_type live on similarity_reasons (apple-to-apple
      // setup means the candidate has the same setup as the source).
      kalkulacja_snapshot: {
        tire_class: v.tire_class ?? v.similarity_reasons?.source_tire_class ?? null,
        service_type: v.service_type ?? v.similarity_reasons?.source_service_type ?? null,
        discount_pct: v.discount_pct ?? v.similarity_reasons?.discount_pct ?? null,
        bank_margin_pct: v.bank_margin_pct ?? null,
        wibor_pct: v.wibor_pct ?? null,
        tires_included: v.tires_included ?? null,
        tire_buyback: v.tire_buyback ?? null,
        insurance_included: v.insurance_included ?? null,
        replacement_car: v.replacement_car ?? null,
        service_included: v.service_included ?? null,
      },
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
          const headlineChip = getHeadlineChip(v);
          const tags = buildReasonTags(v.similarity_reasons, sourceContext);
          const scoreRounded = v.similarity_score_pct ? Math.round(v.similarity_score_pct) : null;
          const specs = buildSpecChips(v);
          // TODO: price is computed but not consumed in render — kept call for side-effect-free precompute.
          const _price = computeCatalogPriceInfo(v, sourceContext);
          void _price;

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
                  {headlineChip && (
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
                        label={headlineChip.label}
                        color={headlineChip.color}
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
                  )}
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
                            fontWeight: 600,
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

                <Tooltip title={expandedIds.has(v.vehicle_id) ? 'Zwiń szczegóły' : 'Rozwiń szczegóły (cena, rabat, matrix)'}>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleExpanded(v.vehicle_id);
                    }}
                    sx={{
                      p: 0.5,
                      color: '#64748B',
                      bgcolor: '#F1F5F9',
                      borderRadius: '6px',
                      '&:hover': { bgcolor: '#E2E8F0' },
                    }}
                  >
                    {expandedIds.has(v.vehicle_id)
                      ? <ExpandLessIcon sx={{ fontSize: '1.1rem' }} />
                      : <ExpandMoreIcon sx={{ fontSize: '1.1rem' }} />}
                  </IconButton>
                </Tooltip>
              </Box>
              )}

              {expandedIds.has(v.vehicle_id) && (
                <DetailsBlock
                  v={v}
                  source={sourceContext}
                  fallbackDuration={targetDuration}
                  fallbackAnnualMileage={targetAnnualMileage}
                />
              )}

              {/* Kalkulacja snapshot — wherever a price is shown, render the
                  same params row (rabat / opony / ubezpieczenie / auto
                  zastępcze / serwis / WIBOR / marża bankowa) so the user can
                  read each candidate's pricing context at a glance. Spans both
                  grid columns so it sits beneath the price/score row. */}
              <Box sx={{ gridColumn: '1 / -1', mt: 0.5 }}>
                <KalkulacjaParamsRow
                  snapshot={v}
                  fallbackTireClass={v.similarity_reasons?.source_tire_class}
                  fallbackServiceType={v.similarity_reasons?.source_service_type}
                  fallbackDiscountPct={v.similarity_reasons?.discount_pct}
                />
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};
