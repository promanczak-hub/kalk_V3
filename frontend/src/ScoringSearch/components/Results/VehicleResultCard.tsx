import React, { useState } from 'react';
import { ExternalLink, ShoppingCart, Check, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

import type { SearchContext } from '../../types';
import type { PriceForParams, SimilarVehicle } from '../../hooks/useBatchData';
import { SimilarVehiclesSection } from './SimilarVehiclesSection';
import { useOfferCartStore } from '../../../stores/offerCartStore';
import type { SelectedFeature, ScoredVehicle } from '../../types';

interface VehicleResultCardProps {
  car: ScoredVehicle;
  searchContext: SearchContext;
  targetDuration: number;
  targetAnnualMileage: number;
  priceData?: { price_for_params?: PriceForParams; variants?: PriceForParams[] };
  pricesLoading: boolean;
  similarData?: SimilarVehicle[];
  requirements?: SelectedFeature[];
}

const fmtPLN = (n?: number | null, maxFrac = 0): string =>
  n != null ? Number(n).toLocaleString('pl-PL', { maximumFractionDigits: maxFrac }) : '—';

const scoreColorClass = (pct?: number): string => {
  const v = pct ?? 0;
  if (v >= 90) return 'text-emerald-600';
  if (v >= 70) return 'text-blue-600';
  if (v >= 50) return 'text-amber-600';
  return 'text-slate-400';
};

const VehicleResultCardBase: React.FC<VehicleResultCardProps> = ({
  car,
  searchContext,
  targetDuration,
  targetAnnualMileage,
  priceData,
  pricesLoading,
  similarData,
  requirements = [],
}) => {
  const addToCart = useOfferCartStore((s) => s.addItem);
  const vehicleId = car.vehicle_id;
  const isInCart = useOfferCartStore((s) => s.items.some((i) => i.id.startsWith(vehicleId)));

  const matchedFeatures = car.matched_features || [];
  const missingFeatures = car.missing_features || [];
  const score = car.match_score_pct;

  const price = priceData?.price_for_params;
  const variantsCount = price?.variants_count;
  const hasPriceFromAPI = price?.found === true && price?.monthly_price_net != null;
  const rawMonthly = hasPriceFromAPI ? price!.monthly_price_net : car.best_monthly_price;
  // When applied_margin_pct is available and we're using best_monthly_price (not per-params batch),
  // best_monthly_price is already priced at applied_margin_pct by the RPC — display it directly.
  const usingAppliedMargin = !hasPriceFromAPI && car.applied_margin_pct != null;
  // Always prefer per-vehicle applied_margin_pct (backend's budget-matched margin)
  // over the global searchContext.margin_pct, so banner and grid show the same number.
  const displayMarginPct = car.applied_margin_pct ?? (searchContext.margin_pct ?? 0);
  const marginFrac = Math.min(displayMarginPct, 99) / 100;
  const monthlyDisplay = usingAppliedMargin
    ? (car.best_monthly_price ?? null)
    : rawMonthly != null && marginFrac < 1 ? rawMonthly / (1 - marginFrac) : null;
  const calcDate = price?.calculated_at
    ? new Date(price.calculated_at).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : null;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    const basePrice = car.best_monthly_price ?? 0;
    const finalPrice = usingAppliedMargin ? basePrice : (marginFrac < 1 ? basePrice / (1 - marginFrac) : basePrice);
    const variantPriceData = priceData?.price_for_params;
    const uniqueId = `${vehicleId}_${variantPriceData?.duration_months ?? targetDuration}_${variantPriceData?.annual_mileage ?? targetAnnualMileage}`;

    addToCart({
      id: uniqueId,
      brand: car.brand || '',
      model: car.model || '',
      powertrain: car.fuel || '',
      vin_or_config: car.configuration_code || car.offer_number || 'Brak',
      term: variantPriceData?.duration_months || targetDuration,
      mileage: variantPriceData?.annual_mileage || targetAnnualMileage,
      net_installment: finalPrice,
      contribution: 0,
      margin_pct: displayMarginPct,
      variants: priceData?.variants || [],
      system_recommendation: typeof score === 'number' && score >= 90 ? 'Najlepsze dopasowanie' : undefined,
      standard_equipment: [],
      factory_options: [],
      dealer_options: [],
      calculation_data: { ...car, vehicle_id: vehicleId, kalkulacja_id: variantPriceData?.kalkulacja_id },
    });
  };

  const versionMentionsPower = !!car.version && /\b\d+\s*(KM|kW)\b/i.test(car.version);
  const specsLine = [
    car.version,
    car.power_hp && !versionMentionsPower ? `${car.power_hp} KM` : null,
    car.transmission,
    car.drive_type ? car.drive_type.replace(/^Napęd\s*/i, '') : null,
    car.body_style,
    car.fuel,
    car.vehicle_class && car.vehicle_class !== 'Osobowy' ? car.vehicle_class : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div
      className={`flex flex-col bg-white rounded-lg border shadow-sm transition-all hover:shadow-md ${
        isInCart ? 'border-emerald-300' : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      {/* Header: identification + score */}
      <div className="flex items-start justify-between gap-4 p-4">
        <div className="flex-grow min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-slate-900 leading-tight">
              {car.brand} {car.model}
            </h3>
            {isInCart && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full">
                <Check className="w-3 h-3" /> w ofercie
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {car.trim_level && car.trim_level !== 'Brak' && (
              <span className="text-xs text-slate-500 font-medium">{car.trim_level}</span>
            )}
            {(car.configuration_code || car.offer_number) && (
              <span className="text-[11px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
                {car.configuration_code || car.offer_number}
              </span>
            )}
          </div>
          {!!specsLine && (
            <p className="text-xs text-slate-500 font-mono mt-1.5 truncate">{specsLine}</p>
          )}
        </div>

        <div className="flex-shrink-0 flex items-start gap-3">
          <div className="text-right">
            <div className={`text-lg font-semibold tabular-nums ${scoreColorClass(score)}`}>{score ?? 0}%</div>
            <div className="text-[10px] uppercase tracking-wider text-slate-400">dopasowanie</div>
          </div>
          <a
            href={`/?highlight=${vehicleId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-slate-600 mt-0.5"
            title="Otwórz w Ekstrakcji"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Catalog price strip */}
      {(car.base_price_net || car.total_price_net) && (
        <div className="flex items-baseline justify-between px-4 py-2.5 border-t border-slate-200">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Cena katalogowa</span>
          <div className="text-right">
            <div className="text-sm font-semibold text-slate-900 font-mono tabular-nums">
              {fmtPLN(car.total_price_net ?? car.base_price_net)}{' '}
              <span className="text-slate-500 font-normal">PLN netto</span>
              <span className="text-[11px] text-slate-400 font-normal ml-2">
                ({fmtPLN(((car.total_price_net ?? car.base_price_net ?? 0) as number) * 1.23)} brutto)
              </span>
            </div>
            {car.base_price_net && car.options_price_net != null && (
              <div className="text-[11px] text-slate-400 font-mono">
                Podstawa {fmtPLN(car.base_price_net)} + Opcje {fmtPLN(car.options_price_net)}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Calculation snapshot */}
      <div className="px-4 py-3 border-t border-slate-200 bg-slate-50">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
            Kalkulacja{calcDate ? ` · ${calcDate}` : ''}
            {variantsCount && variantsCount > 1 ? ` · 1 z ${variantsCount} wariantów` : ''}
          </span>
          {!!car.applied_discount_pct && car.applied_discount_pct > 0 && (
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono" title="Rabat dealerski zastosowany w kalkulacji">
              BD <span className="font-semibold text-slate-700">{car.applied_discount_pct}%</span>
            </span>
          )}
        </div>

        {pricesLoading ? (
          <div className="text-xs text-slate-400">Ładowanie kalkulacji…</div>
        ) : monthlyDisplay != null ? (
          <>
            {/* Budget-first banner: shown when matrix mode + budget set + we have a per-car margin */}
            <BudgetMatchBanner
              monthlyBudget={searchContext.monthly_budget}
              matrixActive={!!searchContext.useMatrixFilters}
              appliedMarginPct={car.applied_margin_pct}
              monthlyDisplay={monthlyDisplay}
            />

            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-400">Czynsz miesięczny</div>
                <div className="text-base font-bold text-slate-900 font-mono tabular-nums">
                  {fmtPLN(monthlyDisplay)}{' '}
                  <span className="text-xs font-normal text-slate-500">zł / mc netto</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-wider text-slate-400">Marża</div>
                <div className="text-base font-bold text-slate-900 font-mono tabular-nums">
                  {displayMarginPct}%
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-400">Okres × Przebieg</div>
                <div className="text-xs text-slate-700 font-mono tabular-nums">
                  {targetDuration} mc · {fmtPLN(Math.round(targetAnnualMileage * targetDuration / 12))} km
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-wider text-slate-400">Opony · Serwis</div>
                <div className="text-xs text-slate-700 font-mono">
                  {[car.tire_class, car.service_cost_type].filter(Boolean).join(' · ') || '—'}
                </div>
              </div>
            </div>

            {/* Multi-variant table — shows other (period × mileage) cache combos for this car */}
            <VariantsTable
              vehicleId={vehicleId}
              variants={priceData?.variants}
              currentDuration={price?.duration_months ?? targetDuration}
              currentMileage={price?.annual_mileage ?? targetAnnualMileage}
              monthlyBudget={searchContext.monthly_budget}
              currentMarginFrac={marginFrac}
            />
          </>
        ) : (
          <div className="text-xs text-slate-400 italic">Brak kalkulacji dla tych parametrów</div>
        )}

        {!!car.has_ltr_cache && monthlyDisplay != null && (
          <div className="flex justify-end mt-3">
            <button
              type="button"
              onClick={handleAddToCart}
              disabled={isInCart}
              className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md border transition-all ${
                isInCart
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700 cursor-default'
                  : 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:border-blue-400 shadow-sm hover:shadow'
              }`}
            >
              <ShoppingCart className="w-3.5 h-3.5" />
              {isInCart ? 'W ofercie' : 'Dodaj do oferty'}
            </button>
          </div>
        )}
      </div>

      {/* Requirement match summary */}
      {(matchedFeatures.length > 0 || missingFeatures.length > 0) && (
        <div className="px-4 py-3 border-t border-slate-200 flex flex-col gap-2">
          {matchedFeatures.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-700 font-semibold mb-1">
                Spełnione wymagania ({matchedFeatures.length})
              </div>
              <div className="flex flex-wrap gap-1">
                {matchedFeatures.map((f) => (
                  <span
                    key={f}
                    className="text-[11px] text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full font-medium"
                  >
                    {f.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
          {missingFeatures.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-700 font-semibold mb-1">
                Brakujące cechy ({missingFeatures.length})
              </div>
              <div className="flex flex-wrap gap-1">
                {missingFeatures.map((f) => (
                  <span
                    key={f}
                    className="text-[11px] text-red-800 bg-red-100 px-2 py-0.5 rounded-full font-medium"
                  >
                    {f.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <SimilarVehiclesSection
        vehicleId={vehicleId}
        sourceVehicle={car as unknown as Record<string, unknown>}
        targetDuration={targetDuration}
        targetAnnualMileage={targetAnnualMileage}
        similarData={similarData}
        requirements={requirements}
      />
    </div>
  );
};

export const VehicleResultCard = React.memo(VehicleResultCardBase);

// ── Budget Match Banner ─────────────────────────────────────────────────────
// Highlights the per-vehicle margin computed by the backend to fit the
// customer's monthly_budget. Color tier:
//   ≥ 12% → emerald ("świetna marża, mocny biznes")
//   5-12% → amber  ("graniczna, do negocjacji")
//   < 5%  → orange ("niska marża, ostrożnie")
//   null  → not shown (backend filtered out / no matrix mode)

interface BudgetMatchBannerProps {
  monthlyBudget: number | null | undefined;
  matrixActive: boolean;
  appliedMarginPct: number | null | undefined;
  monthlyDisplay: number | null | undefined;
}

const BudgetMatchBanner: React.FC<BudgetMatchBannerProps> = ({
  monthlyBudget,
  matrixActive,
  appliedMarginPct,
  monthlyDisplay,
}) => {
  // Only show when in budget-match mode AND backend gave us a per-car margin
  if (!matrixActive || !monthlyBudget || monthlyBudget <= 0) return null;
  if (appliedMarginPct == null) return null;

  const tier: 'good' | 'warning' | 'loss' =
    appliedMarginPct >= 12 ? 'good' : appliedMarginPct >= 5 ? 'warning' : 'loss';

  const tierStyle = {
    good: 'bg-emerald-50 border-emerald-300',
    warning: 'bg-amber-50 border-amber-300',
    loss: 'bg-orange-50 border-orange-300',
  }[tier];

  const textStyle = {
    good: 'text-emerald-800',
    warning: 'text-amber-800',
    loss: 'text-orange-800',
  }[tier];

  const badgeStyle = {
    good: 'bg-emerald-600 text-white',
    warning: 'bg-amber-600 text-white',
    loss: 'bg-orange-600 text-white',
  }[tier];

  const tierLabel = {
    good: '✓ Świetna marża',
    warning: '⚠ Marża graniczna',
    loss: '⚠ Niska marża',
  }[tier];

  return (
    <div className={`mb-3 p-3 rounded-md border ${tierStyle}`}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
            💰 Dopasowane do budżetu
          </span>
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${badgeStyle}`}>
            {tierLabel}
          </span>
        </div>
        <div className={`flex items-baseline gap-3 font-mono tabular-nums ${textStyle}`}>
          <div>
            <span className="text-[10px] uppercase tracking-wider opacity-75">Cena</span>{' '}
            <span className="text-base font-bold">
              {fmtPLN(monthlyDisplay ?? monthlyBudget)}
            </span>
            <span className="text-[10px] opacity-75 ml-0.5">PLN/mc</span>
          </div>
          <div className="text-slate-300">·</div>
          <div>
            <span className="text-[10px] uppercase tracking-wider opacity-75">Marża</span>{' '}
            <span className="text-base font-bold">{appliedMarginPct.toFixed(1)}%</span>
          </div>
        </div>
      </div>
      <div className="mt-1 text-[10px] text-slate-500">
        Backend dobrał marżę tak, by cena auta zmieściła się w Twoim budżecie {fmtPLN(monthlyBudget)} PLN.
      </div>
    </div>
  );
};

// ── Variants Table ─────────────────────────────────────────────────────────
// Mini-table of all (period × mileage) cache combos available for this car.
// Sorted by margin-to-budget descending (best deal first). Highlights:
//   - Currently displayed variant (matches current params)
//   - Variants that fit budget (green) vs over-budget (red)
// Computed entirely on frontend from priceData.variants[] — no backend changes.

interface PriceVariant {
  duration_months: number | null;
  annual_mileage: number | null;
  monthly_price_net: number | null;
  tire_class?: string;
  service_type?: string;
  kalkulacja_id?: string;
}

interface VariantsTableProps {
  vehicleId: string;
  variants: PriceVariant[] | undefined;
  currentDuration: number | null;
  currentMileage: number | null;
  monthlyBudget: number | null | undefined;
  currentMarginFrac: number; // 0..0.99 — global margin used in main display
}

const VariantsTable: React.FC<VariantsTableProps> = ({
  vehicleId,
  variants: passedVariants,
  currentDuration,
  currentMileage,
  monthlyBudget,
  currentMarginFrac,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [fetchedVariants, setFetchedVariants] = useState<PriceVariant[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lazy-fetch variants when user opens the panel — backend's batch-prices
  // endpoint returns empty variants[] (data overflow guard), so we hit the
  // dedicated /scoring-search/vehicle/{id}/price-variants endpoint instead.
  // Returns 4 variants (24/36/48/60mc) for the given annual_mileage.
  React.useEffect(() => {
    if (!expanded || fetchedVariants !== null || !vehicleId || !currentMileage) return;
    setLoading(true);
    setError(null);
    import('../../../lib/apiClient')
      .then(({ apiClient }) =>
        apiClient.fetch(
          `/api/scoring-search/vehicle/${vehicleId}/price-variants?annual_mileage=${currentMileage}`,
        ),
      )
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: PriceVariant[]) => {
        setFetchedVariants(Array.isArray(data) ? data : []);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Nieznany błąd';
        setError(msg);
        setFetchedVariants([]);
      })
      .finally(() => setLoading(false));
  }, [expanded, vehicleId, currentMileage, fetchedVariants]);

  // Use lazily-fetched if available, else fall back to passed
  const variants = fetchedVariants ?? passedVariants ?? [];

  // Filter out invalid rows + dedupe by (duration, mileage)
  const seen = new Set<string>();
  const usable = variants.filter((v) => {
    if (v.monthly_price_net == null || v.duration_months == null || v.annual_mileage == null) {
      return false;
    }
    const key = `${v.duration_months}_${v.annual_mileage}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Always show the toggle button (we'll lazy-fetch on click). Hide if no
  // vehicle id or no annual mileage to query against.
  if (!vehicleId || !currentMileage) return null;

  // Per variant: rate at current global margin + (if budget set) margin-to-budget
  type Row = {
    v: PriceVariant;
    rate: number;
    appliedMargin: number | null; // null if no budget
    fitsBudget: boolean;
    isCurrent: boolean;
  };

  const rows: Row[] = usable.map((v) => {
    const base = v.monthly_price_net as number;
    const rate = currentMarginFrac < 1 ? base / (1 - currentMarginFrac) : base;
    const appliedMargin =
      monthlyBudget && monthlyBudget > 0 && base < monthlyBudget
        ? (1 - base / monthlyBudget) * 100
        : monthlyBudget && monthlyBudget > 0
        ? 0
        : null;
    const fitsBudget = monthlyBudget ? base <= monthlyBudget : true;
    const isCurrent =
      v.duration_months === currentDuration && v.annual_mileage === currentMileage;
    return { v, rate, appliedMargin, fitsBudget, isCurrent };
  });

  // Sort: current first, then by appliedMargin desc (best business), then by rate asc
  rows.sort((a, b) => {
    if (a.isCurrent && !b.isCurrent) return -1;
    if (b.isCurrent && !a.isCurrent) return 1;
    if (a.appliedMargin != null && b.appliedMargin != null) {
      return b.appliedMargin - a.appliedMargin;
    }
    return a.rate - b.rate;
  });

  return (
    <div className="mt-3 pt-3 border-t border-slate-200">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        className="w-full text-left flex items-center justify-between gap-2 text-xs text-blue-700 hover:bg-blue-50 px-2 py-1.5 rounded-md transition-colors"
      >
        <span className="font-medium inline-flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          {expanded
            ? 'Ukryj warianty cenowe'
            : `Pokaż warianty (24 / 36 / 48 / 60 mc dla ${(currentMileage / 1000).toFixed(0)}k km/rok)`}
          {monthlyBudget && monthlyBudget > 0 && (
            <span className="text-slate-500 font-normal ml-1">
              (sortowane po marży dopasowanej do budżetu)
            </span>
          )}
        </span>
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {expanded && loading && (
        <div className="mt-2 text-xs text-slate-500 italic px-2 py-2">Ładowanie wariantów cenowych...</div>
      )}

      {expanded && error && (
        <div className="mt-2 text-xs text-red-700 bg-red-50 border border-red-200 px-2 py-1.5 rounded-md">
          Błąd ładowania: {error}
        </div>
      )}

      {expanded && !loading && !error && rows.length === 0 && (
        <div className="mt-2 text-xs text-slate-500 italic px-2 py-2">
          Brak alternatywnych wariantów w cache dla tego pojazdu i przebiegu.
        </div>
      )}

      {expanded && !loading && !error && rows.length > 0 && (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-xs border border-slate-200 rounded-md overflow-hidden">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-[10px] uppercase tracking-wider text-slate-600">
                <th className="text-left px-2 py-1.5 font-semibold">Okres</th>
                <th className="text-right px-2 py-1.5 font-semibold">Przebieg/rok</th>
                <th className="text-right px-2 py-1.5 font-semibold">Rata @ {(currentMarginFrac * 100).toFixed(0)}%</th>
                {monthlyBudget && monthlyBudget > 0 && (
                  <th className="text-right px-2 py-1.5 font-semibold">Marża dopasowana</th>
                )}
                <th className="text-center px-2 py-1.5 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => {
                const tier = row.appliedMargin == null
                  ? 'neutral'
                  : !row.fitsBudget
                  ? 'fail'
                  : row.appliedMargin >= 12
                  ? 'good'
                  : row.appliedMargin >= 5
                  ? 'warning'
                  : 'loss';

                const rowBg = row.isCurrent
                  ? 'bg-blue-50 border-l-2 border-blue-500'
                  : tier === 'good'
                  ? 'bg-emerald-50/40 hover:bg-emerald-50'
                  : tier === 'warning'
                  ? 'bg-amber-50/40 hover:bg-amber-50'
                  : tier === 'loss'
                  ? 'bg-orange-50/40 hover:bg-orange-50'
                  : tier === 'fail'
                  ? 'bg-red-50/40 hover:bg-red-50 opacity-70'
                  : 'hover:bg-slate-50';

                const tierBadge = {
                  good: { text: '✓ świetna', cls: 'bg-emerald-100 text-emerald-800' },
                  warning: { text: '⚠ graniczna', cls: 'bg-amber-100 text-amber-800' },
                  loss: { text: '⚠ niska', cls: 'bg-orange-100 text-orange-800' },
                  fail: { text: '✗ nad budżet', cls: 'bg-red-100 text-red-800' },
                  neutral: { text: '—', cls: 'bg-slate-100 text-slate-600' },
                }[tier];

                return (
                  <tr
                    key={`${row.v.duration_months}_${row.v.annual_mileage}_${idx}`}
                    className={`border-b border-slate-100 ${rowBg} transition-colors`}
                  >
                    <td className="px-2 py-1.5 font-mono tabular-nums text-slate-900">
                      {row.v.duration_months} mc
                      {row.isCurrent && <span className="ml-1 text-[9px] text-blue-600 font-semibold uppercase">akt</span>}
                    </td>
                    <td className="px-2 py-1.5 font-mono tabular-nums text-right text-slate-700">
                      {fmtPLN(row.v.annual_mileage)} km
                    </td>
                    <td className="px-2 py-1.5 font-mono tabular-nums text-right font-semibold text-slate-900">
                      {fmtPLN(row.rate)}
                    </td>
                    {monthlyBudget && monthlyBudget > 0 && (
                      <td className="px-2 py-1.5 font-mono tabular-nums text-right font-semibold text-slate-900">
                        {row.appliedMargin != null ? `${row.appliedMargin.toFixed(1)}%` : '—'}
                      </td>
                    )}
                    <td className="px-2 py-1.5 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${tierBadge.cls}`}>
                        {tierBadge.text}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="text-[10px] text-slate-500 mt-1.5 px-1">
            💡 Każda kombinacja okres × przebieg ma własną marżę dopasowaną do Twojego budżetu.
            Wybierz wariant który ci najbardziej pasuje biznesowo.
          </p>
        </div>
      )}
    </div>
  );
};
