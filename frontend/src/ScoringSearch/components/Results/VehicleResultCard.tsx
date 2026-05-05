import React, { useState } from 'react';
import { ExternalLink, ShoppingCart, Check, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

import type { SearchContext } from '../../types';
import type { PriceForParams, SimilarVehicle } from '../../hooks/useBatchData';
import { SimilarVehiclesSection } from './SimilarVehiclesSection';
import { useOfferCartStore } from '../../../stores/offerCartStore';
import type { ScoredVehicle } from '../../types';

interface VehicleResultCardProps {
  car: ScoredVehicle;
  searchContext: SearchContext;
  targetDuration: number;
  targetAnnualMileage: number;
  priceData?: { price_for_params?: PriceForParams; variants?: PriceForParams[] };
  pricesLoading: boolean;
  similarData?: SimilarVehicle[];
  // When set, this card represents a specific pinned calculation for the vehicle.
  // The card fetches its own price scoped to this kalkulacja_id instead of using priceData.
  pinnedKalkulacjaId?: string;
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
  pinnedKalkulacjaId,
}) => {
  const addToCart = useOfferCartStore((s) => s.addItem);
  const vehicleId = car.vehicle_id;
  const isInCart = useOfferCartStore((s) => s.items.some((i) => i.id.startsWith(vehicleId)));

  // Inline expand/collapse for "Opcje fabryczne" / "Opcje serwisowe" rows.
  const [factoryOptionsOpen, setFactoryOptionsOpen] = useState(false);
  const [serviceOptionsOpen, setServiceOptionsOpen] = useState(false);

  // For pinned-calc cards, fetch price scoped to the specific kalkulacja_id.
  // Falls through to the batch priceData when no pin is set.
  const [pinnedPrice, setPinnedPrice] = useState<PriceForParams | null>(null);
  const [pinnedPriceLoading, setPinnedPriceLoading] = useState(false);
  React.useEffect(() => {
    if (!pinnedKalkulacjaId) {
      setPinnedPrice(null);
      return;
    }
    let cancelled = false;
    setPinnedPriceLoading(true);
    import('../../../lib/apiClient')
      .then(({ apiClient }) =>
        apiClient.fetch(
          `/api/scoring-search/vehicle/${vehicleId}/price-for-params?duration_months=${targetDuration}&annual_mileage=${targetAnnualMileage}&kalkulacja_id=${pinnedKalkulacjaId}`,
        ),
      )
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: PriceForParams) => { if (!cancelled) setPinnedPrice(data); })
      .catch(() => { if (!cancelled) setPinnedPrice(null); })
      .finally(() => { if (!cancelled) setPinnedPriceLoading(false); });
    return () => { cancelled = true; };
  }, [pinnedKalkulacjaId, vehicleId, targetDuration, targetAnnualMileage]);

  const matchedFeatures = car.matched_features || [];
  const missingFeatures = car.missing_features || [];
  const score = car.match_score_pct;

  const price = pinnedKalkulacjaId ? (pinnedPrice ?? undefined) : priceData?.price_for_params;
  const effectivePricesLoading = pinnedKalkulacjaId ? pinnedPriceLoading : pricesLoading;
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
  // Base monthly rate before any margin markup. When usingAppliedMargin is true,
  // rawMonthly already contains the applied margin baked in by the RPC.
  const trueBaseMonthly = usingAppliedMargin
    ? (rawMonthly != null ? rawMonthly * (1 - marginFrac) : null)
    : (rawMonthly ?? null);
  const budget = searchContext.useMatrixFilters && searchContext.monthly_budget && searchContext.monthly_budget > 0
    ? searchContext.monthly_budget
    : null;
  const overBudget = budget != null && monthlyDisplay != null && monthlyDisplay > budget;
  // Margin at which the rate would equal the budget exactly: budget = base / (1 - m)
  // → m = 1 - base/budget. If base > budget, this becomes negative (loss territory).
  const marginToFitPct = budget != null && trueBaseMonthly != null
    ? (1 - trueBaseMonthly / budget) * 100
    : null;

  // ── Eager variants fetch for over-budget cards ──────────────────────────
  // When the current rate exceeds budget, we want the banner to list which
  // (period × mileage) variants DO fit at the user's expected margin. The
  // VariantsTable below also lazy-fetches the same endpoint on expand — we
  // share the result via this state so the table skips its own fetch.
  const [eagerVariants, setEagerVariants] = useState<PriceForParams[] | null>(null);
  React.useEffect(() => {
    if (!overBudget || !budget || !vehicleId || !targetAnnualMileage) {
      setEagerVariants(null);
      return;
    }
    let cancelled = false;
    import('../../../lib/apiClient')
      .then(({ apiClient }) =>
        apiClient.fetch(
          `/api/scoring-search/vehicle/${vehicleId}/price-variants?annual_mileage=${targetAnnualMileage}${pinnedKalkulacjaId ? `&kalkulacja_id=${pinnedKalkulacjaId}` : ''}`,
        ),
      )
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: PriceForParams[]) => {
        if (!cancelled) setEagerVariants(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (!cancelled) setEagerVariants([]);
      });
    return () => {
      cancelled = true;
    };
  }, [overBudget, budget, vehicleId, targetAnnualMileage, pinnedKalkulacjaId]);

  // Variants from this vehicle that DO fit the budget at the user's currently
  // displayed margin (displayMarginPct). Sorted by rate ascending — cheapest
  // first, since "fits the budget" is the relevant ordering here.
  const fittingVariants = React.useMemo(() => {
    if (!eagerVariants || !budget || marginFrac >= 1) return [];
    return eagerVariants
      .filter(
        (v) =>
          v.monthly_price_net != null &&
          v.duration_months != null &&
          v.annual_mileage != null,
      )
      .map((v) => {
        const base = v.monthly_price_net as number;
        const rate = base / (1 - marginFrac);
        const variantMarginToFit = (1 - base / budget) * 100;
        return { v, rate, variantMarginToFit };
      })
      .filter((row) => row.variantMarginToFit >= displayMarginPct)
      .sort((a, b) => a.rate - b.rate)
      .slice(0, 3);
  }, [eagerVariants, budget, marginFrac, displayMarginPct]);
  const calcDate = price?.calculated_at
    ? new Date(price.calculated_at).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : null;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    const basePrice = car.best_monthly_price ?? 0;
    const finalPrice = usingAppliedMargin ? basePrice : (marginFrac < 1 ? basePrice / (1 - marginFrac) : basePrice);
    const variantPriceData = price; // pinned price when set, else batch
    const dur = variantPriceData?.duration_months ?? targetDuration;
    const mil = variantPriceData?.annual_mileage ?? targetAnnualMileage;
    // Pinned cards include the kalkulacja_id in their cart id so different
    // pins of the same vehicle stay distinct entries.
    const kidForId = pinnedKalkulacjaId ?? variantPriceData?.kalkulacja_id ?? '';
    // Margin is part of the cart-entry identity: the same vehicle calculated at
    // two different margins must produce two distinct cart rows so the user can
    // compare them in the offer.
    const marginTag = `m${Math.round((displayMarginPct ?? 0) * 10)}`;
    const uniqueId = kidForId
      ? `${vehicleId}_${dur}_${mil}_${kidForId}_${marginTag}`
      : `${vehicleId}_${dur}_${mil}_${marginTag}`;

    addToCart({
      id: uniqueId,
      brand: car.brand || '',
      model: car.model || '',
      powertrain: car.fuel || '',
      vin_or_config: car.configuration_code || car.offer_number || 'Brak',
      term: dur,
      mileage: mil,
      net_installment: finalPrice,
      contribution: 0,
      margin_pct: displayMarginPct,
      variants: priceData?.variants || [],
      system_recommendation: typeof score === 'number' && score >= 90 ? 'Najlepsze dopasowanie' : undefined,
      standard_equipment: [],
      factory_options: [],
      dealer_options: [],
      calculation_data: { ...car, vehicle_id: vehicleId, kalkulacja_id: pinnedKalkulacjaId ?? variantPriceData?.kalkulacja_id },
    });
  };

  const versionMentionsPower = !!car.version && /\b\d+\s*(KM|kW)\b/i.test(car.version);

  // ── Helper: clean up vehicle_class duplicates like "Średnie dostawcze - ŚREDNIE DOSTAWCZE"
  const cleanVehicleClass = (raw: string): string => {
    // Split on " - " and deduplicate (case-insensitive)
    const parts = raw.split(/\s*-\s*/);
    const seen = new Set<string>();
    const unique = parts.filter(p => {
      const key = p.trim().toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    // Title-case the result
    const cleaned = unique.join(' – ');
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1).toLowerCase();
  };

  // ── Helper: check if drive_type is already embedded in transmission text
  const transmissionStr = String(car.transmission || '').toUpperCase();
  const driveTypeStr = String(car.drive_type || '').replace(/^Napęd\s*/i, '').toUpperCase();
  const driveTypeInTransmission = driveTypeStr.length > 0 && transmissionStr.includes(driveTypeStr);

  // Structured spec badges instead of a single blended line.
  // power_hp + transmission are rendered inline next to the engine pill above, so they're omitted here.
  const specBadges: { label: string; color: string }[] = [
    car.fuel ? { label: car.fuel, color: car.fuel.toLowerCase().includes('diesel') ? 'bg-amber-100 text-amber-800' : car.fuel.toLowerCase().includes('elektr') ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800' } : null,
    // Skip drive_type if already mentioned in transmission (e.g. "MANUALNA, NA TYLNE KOŁA RWD" + "RWD")
    car.drive_type && !driveTypeInTransmission ? { label: car.drive_type.replace(/^Napęd\s*/i, ''), color: 'bg-slate-100 text-slate-700' } : null,
    car.body_style ? { label: car.body_style, color: 'bg-indigo-100 text-indigo-800' } : null,
  ].filter((b): b is { label: string; color: string } => b !== null);

  return (
    <div
      className={`flex flex-col rounded-lg border shadow-sm transition-all hover:shadow-md ${
        isInCart
          ? 'bg-white border-emerald-300'
          : pinnedKalkulacjaId
            ? 'bg-white border-amber-300 hover:border-amber-400'
            : overBudget
              ? 'bg-red-50/40 border-red-200 opacity-75 hover:opacity-95'
              : 'bg-white border-slate-200 hover:border-slate-300'
      }`}
    >
      {/* Header: identification + score */}
      <div className="flex items-start justify-between gap-4 p-4">
        <div className="flex-grow min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-slate-900 leading-tight">
              {car.brand} {car.model}
            </h3>
            {pinnedKalkulacjaId && (
              <span
                className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full"
                title={`Przypięta kalkulacja${price?.kalkulacja_id ? ` (${price.kalkulacja_id.slice(0, 8)}…)` : ''}`}
              >
                <Sparkles className="w-3 h-3" /> przypięta
              </span>
            )}
            {isInCart && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full">
                <Check className="w-3 h-3" /> w ofercie
              </span>
            )}
          </div>
          <div className="flex items-center gap-x-2 gap-y-0.5 mt-1 flex-wrap text-xs">
            {car.trim_level && car.trim_level !== 'Brak' && (
              <span className="text-slate-600 font-medium">{car.trim_level}</span>
            )}
            {car.version && car.version !== car.trim_level && (
              <span className="text-slate-500 truncate max-w-[260px]">{car.version}</span>
            )}
            {(car.engine_capacity || car.engine_designation || (car.power_hp && !versionMentionsPower)) && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 font-mono text-[11px]">
                {[
                  car.engine_capacity ? `${car.engine_capacity}L` : null,
                  car.engine_designation,
                  car.power_hp && !versionMentionsPower ? `${car.power_hp}KM` : null,
                ]
                  .filter(Boolean)
                  .join(' ')}
              </span>
            )}
            {car.transmission && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-violet-100 text-violet-800 text-[11px] font-medium">
                {car.transmission}
              </span>
            )}
            {car.vehicle_class && car.vehicle_class !== 'Brak' && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 text-[11px]">
                {cleanVehicleClass(car.vehicle_class)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-x-2 gap-y-0.5 mt-1 flex-wrap text-[11px]">
            {(car.configuration_code || car.offer_number) && (
              <span
                className="font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md"
                title="Kod konfiguracji"
              >
                {car.configuration_code || car.offer_number}
              </span>
            )}
            {car.extraction_date && (
              <span className="text-slate-600" title="Data ekstrakcji oferty">
                Ekstrakcja:{' '}
                <span className="font-mono text-slate-700">
                  {new Date(car.extraction_date).toLocaleDateString('pl-PL', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                  })}
                </span>
              </span>
            )}
          </div>
          {specBadges.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {specBadges.map((b) => (
                <span key={b.label} className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${b.color}`}>
                  {b.label}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex-shrink-0 flex items-start gap-3">
          <div className="text-right">
            <div className={`text-lg font-semibold tabular-nums ${scoreColorClass(score)}`}>{score ?? 0}%</div>
            <div className="text-[11px] uppercase tracking-wider text-slate-600">dopasowanie</div>
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

      {/* Catalog price strip — total + breakdown into base, factory options, service options */}
      {(car.base_price_net || car.total_price_net) && (
        <div className="px-4 py-2.5 border-t border-slate-200">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] uppercase tracking-wider text-slate-600 font-semibold">Cena katalogowa</span>
            <div className="text-sm font-semibold text-slate-900 font-mono tabular-nums">
              {fmtPLN(car.total_price_net ?? car.base_price_net)}{' '}
              <span className="text-slate-700 font-normal">PLN netto</span>
              <span className="text-xs text-slate-600 font-normal ml-2">
                ({fmtPLN(((car.total_price_net ?? car.base_price_net ?? 0) as number) * 1.23)} brutto)
              </span>
            </div>
          </div>
          {(car.base_price_net != null
            || car.factory_options_price_net != null
            || car.service_options_price_net != null
            || car.options_price_net != null) && (
            <div className="mt-1.5 flex flex-col gap-0.5 text-xs font-mono text-slate-700">
              {car.base_price_net != null && (
                <div className="flex justify-between">
                  <span className="text-slate-600">Cena bazowa</span>
                  <span className="tabular-nums">
                    {fmtPLN(car.base_price_net)} PLN
                    <span className="text-slate-500 ml-1.5">({fmtPLN(car.base_price_net * 1.23)} brutto)</span>
                  </span>
                </div>
              )}
              {car.factory_options_price_net != null && car.factory_options_price_net > 0 && (() => {
                const items = car.factory_options ?? [];
                const expandable = items.length > 0;
                return (
                  <div>
                    <button
                      type="button"
                      disabled={!expandable}
                      onClick={() => expandable && setFactoryOptionsOpen((v) => !v)}
                      className={`w-full flex justify-between items-center text-left ${expandable ? 'hover:text-slate-700 cursor-pointer' : 'cursor-default'}`}
                    >
                      <span className="text-slate-600 flex items-center gap-1">
                        Opcje fabryczne
                        {expandable && (factoryOptionsOpen
                          ? <ChevronUp className="w-3 h-3" />
                          : <ChevronDown className="w-3 h-3" />)}
                      </span>
                      <span className="tabular-nums">
                        + {fmtPLN(car.factory_options_price_net)} PLN
                        <span className="text-slate-500 ml-1.5">({fmtPLN(car.factory_options_price_net * 1.23)} brutto)</span>
                      </span>
                    </button>
                    {expandable && factoryOptionsOpen && (
                      <ul className="mt-1 ml-3 flex flex-col gap-0.5">
                        {items.map((opt, i) => (
                          <li key={`fo-${i}-${opt.name}`} className="flex justify-between gap-2">
                            <span className="text-slate-400 truncate">· {opt.name}</span>
                            <span className="tabular-nums whitespace-nowrap text-slate-500">
                              {opt.price_net != null ? `${fmtPLN(opt.price_net)} PLN` : '—'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })()}
              {car.service_options_price_net != null && car.service_options_price_net > 0 && (() => {
                const items = car.service_options ?? [];
                const expandable = items.length > 0;
                return (
                  <div>
                    <button
                      type="button"
                      disabled={!expandable}
                      onClick={() => expandable && setServiceOptionsOpen((v) => !v)}
                      className={`w-full flex justify-between items-center text-left ${expandable ? 'hover:text-slate-700 cursor-pointer' : 'cursor-default'}`}
                    >
                      <span className="text-slate-600 flex items-center gap-1">
                        Opcje serwisowe
                        {expandable && (serviceOptionsOpen
                          ? <ChevronUp className="w-3 h-3" />
                          : <ChevronDown className="w-3 h-3" />)}
                      </span>
                      <span className="tabular-nums">
                        + {fmtPLN(car.service_options_price_net)} PLN
                        <span className="text-slate-500 ml-1.5">({fmtPLN(car.service_options_price_net * 1.23)} brutto)</span>
                      </span>
                    </button>
                    {expandable && serviceOptionsOpen && (
                      <ul className="mt-1 ml-3 flex flex-col gap-0.5">
                        {items.map((opt, i) => (
                          <li key={`so-${i}-${opt.name}`} className="flex justify-between gap-2">
                            <span className="text-slate-400 truncate">· {opt.name}</span>
                            <span className="tabular-nums whitespace-nowrap text-slate-500">
                              {opt.price_net != null ? `${fmtPLN(opt.price_net)} PLN` : '—'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })()}
              {/* Fallback when split isn't available but a combined options figure is */}
              {car.factory_options_price_net == null
                && car.service_options_price_net == null
                && car.options_price_net != null
                && car.options_price_net > 0 && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Opcje (łącznie)</span>
                    <span className="tabular-nums">
                      + {fmtPLN(car.options_price_net)} PLN
                      <span className="text-slate-500 ml-1.5">({fmtPLN(car.options_price_net * 1.23)} brutto)</span>
                    </span>
                  </div>
                )}
            </div>
          )}
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
            <span className="text-[11px] uppercase tracking-wider text-slate-600 font-mono" title="Rabat dealerski zastosowany w kalkulacji">
              BD <span className="font-semibold text-slate-700">{car.applied_discount_pct}%</span>
            </span>
          )}
        </div>

        {effectivePricesLoading ? (
          <div className="text-xs text-slate-400">Ładowanie kalkulacji…</div>
        ) : monthlyDisplay != null ? (
          <>
            {/* Budget-first banner: shown when matrix mode + budget set + we have a per-car margin */}
            <BudgetMatchBanner
              monthlyBudget={searchContext.monthly_budget}
              matrixActive={!!searchContext.useMatrixFilters}
              appliedMarginPct={car.applied_margin_pct}
              monthlyDisplay={monthlyDisplay}
              overBudget={overBudget}
              marginToFitPct={marginToFitPct}
              displayMarginPct={displayMarginPct}
              fittingVariants={fittingVariants}
            />

            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-slate-600">Czynsz miesięczny</div>
                <div className="text-base font-bold text-slate-900 font-mono tabular-nums">
                  {fmtPLN(monthlyDisplay)}{' '}
                  <span className="text-xs font-normal text-slate-500">zł / mc netto</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-wider text-slate-600">Marża</div>
                <div className="text-base font-bold text-slate-900 font-mono tabular-nums">
                  {displayMarginPct}%
                </div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-wider text-slate-600">Okres × Przebieg</div>
                <div className="text-xs text-slate-700 font-mono tabular-nums">
                  {targetDuration} mc · {fmtPLN(Math.round(targetAnnualMileage * targetDuration / 12))} km
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] uppercase tracking-wider text-slate-600">Opony · Serwis</div>
                <div className="text-xs text-slate-700 font-mono">
                  {[car.tire_class, car.service_cost_type].filter(Boolean).join(' · ') || '—'}
                </div>
              </div>
            </div>

            {/* Multi-variant table — shows other (period × mileage) cache combos for this car */}
            <VariantsTable
              vehicleId={vehicleId}
              variants={eagerVariants ?? priceData?.variants}
              currentDuration={price?.duration_months ?? targetDuration}
              currentMileage={price?.annual_mileage ?? targetAnnualMileage}
              monthlyBudget={searchContext.monthly_budget}
              currentMarginFrac={marginFrac}
              car={car}
              displayMarginPct={displayMarginPct}
              pinnedKalkulacjaId={pinnedKalkulacjaId}
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
        marginPct={displayMarginPct}
        matrixActive={!!searchContext.useMatrixFilters}
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

interface FittingVariant {
  v: PriceForParams;
  rate: number;
  variantMarginToFit: number;
}

interface BudgetMatchBannerProps {
  monthlyBudget: number | null | undefined;
  matrixActive: boolean;
  appliedMarginPct: number | null | undefined;
  monthlyDisplay: number | null | undefined;
  overBudget?: boolean;
  marginToFitPct?: number | null;
  displayMarginPct?: number;
  fittingVariants?: FittingVariant[];
}

const BudgetMatchBanner: React.FC<BudgetMatchBannerProps> = ({
  monthlyBudget,
  matrixActive,
  appliedMarginPct,
  monthlyDisplay,
  overBudget,
  marginToFitPct,
  displayMarginPct,
  fittingVariants,
}) => {
  // Only show when in budget-match mode
  if (!matrixActive || !monthlyBudget || monthlyBudget <= 0) return null;

  // OVER-BUDGET banner — replaces the green "fits" banner when rate exceeds budget.
  // Shows the overshoot and the margin at which the car would fit (or "even at 0%
  // it doesn't fit" when base price already exceeds budget).
  if (overBudget && monthlyDisplay != null) {
    const overshoot = monthlyDisplay - monthlyBudget;
    const currentMargin = displayMarginPct ?? 0;
    const fitsAtPositiveMargin = marginToFitPct != null && marginToFitPct > 0;
    const cannotFit = marginToFitPct != null && marginToFitPct <= 0;

    return (
      <div className="mb-3 p-3 rounded-md border bg-red-50 border-red-300">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-red-900 uppercase tracking-wider">
              ⚠ Nad budżet
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-600 text-white">
              + {fmtPLN(overshoot)} PLN/mc
            </span>
          </div>
          <div className="flex items-baseline gap-3 font-mono tabular-nums text-red-900">
            <div>
              <span className="text-[10px] uppercase tracking-wider opacity-75">Rata</span>{' '}
              <span className="text-base font-bold">{fmtPLN(monthlyDisplay)}</span>
              <span className="text-[10px] opacity-75 ml-0.5">PLN/mc</span>
            </div>
            <div className="text-red-300">·</div>
            <div>
              <span className="text-[10px] uppercase tracking-wider opacity-75">Budżet</span>{' '}
              <span className="text-base font-bold">{fmtPLN(monthlyBudget)}</span>
              <span className="text-[10px] opacity-75 ml-0.5">PLN/mc</span>
            </div>
          </div>
        </div>
        <div className="mt-1.5 text-[11px] text-red-800">
          {fitsAtPositiveMargin ? (
            <>
              Zmieści się w budżecie przy marży{' '}
              <strong className="text-red-900">{(marginToFitPct as number).toFixed(1)}%</strong>
              {' '}(obecna marża: {currentMargin}%).
            </>
          ) : cannotFit ? (
            <>
              Cena bazowa przekracza budżet — auto nie zmieści się nawet bez marży
              (potrzebna marża {(marginToFitPct as number).toFixed(1)}%).
            </>
          ) : (
            <>Cena przekracza budżet {fmtPLN(monthlyBudget)} PLN/mc.</>
          )}
        </div>
        {fittingVariants && fittingVariants.length > 0 && (
          <div className="mt-2 pt-2 border-t border-red-200">
            <div className="text-[11px] font-semibold text-emerald-800 mb-1.5">
              ✓ Wchodzą w budżet przy marży ≥ {currentMargin}%:
            </div>
            <div className="flex flex-wrap gap-1.5">
              {fittingVariants.map((row) => (
                <div
                  key={`${row.v.duration_months}_${row.v.annual_mileage}`}
                  className="inline-flex items-baseline gap-1.5 bg-emerald-50 border border-emerald-200 rounded-md px-2 py-1 text-[11px]"
                >
                  <span className="font-mono tabular-nums text-emerald-900 font-medium">
                    {row.v.duration_months}mc · {fmtPLN((row.v.annual_mileage as number) / 1000)}k km/rok
                  </span>
                  <span className="font-mono tabular-nums font-bold text-emerald-900">
                    {fmtPLN(row.rate)} PLN/mc
                  </span>
                  <span className="text-[10px] text-emerald-700">
                    (marża do {row.variantMarginToFit.toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // FITS-BUDGET banner — only when backend actively dialed a per-car margin.
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
  car: ScoredVehicle;
  displayMarginPct: number;
  pinnedKalkulacjaId?: string;
}

const VariantsTable: React.FC<VariantsTableProps> = ({
  vehicleId,
  variants: passedVariants,
  currentDuration,
  currentMileage,
  monthlyBudget,
  currentMarginFrac,
  car,
  displayMarginPct,
  pinnedKalkulacjaId,
}) => {
  const addToCart = useOfferCartStore((s) => s.addItem);
  const cartItems = useOfferCartStore((s) => s.items);
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
          `/api/scoring-search/vehicle/${vehicleId}/price-variants?annual_mileage=${currentMileage}${pinnedKalkulacjaId ? `&kalkulacja_id=${pinnedKalkulacjaId}` : ''}`,
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
  }, [expanded, vehicleId, currentMileage, fetchedVariants, pinnedKalkulacjaId]);

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

  // Per variant: rate at user's current margin + (if budget set) max margin
  // at which the variant still fits the budget. fitsBudget compares the
  // achievable margin against the user's expected margin — anything below
  // it is "tight" or "over budget", not "świetna".
  type Row = {
    v: PriceVariant;
    rate: number;
    marginToFitPct: number | null; // null when no budget set
    fitsBudget: boolean;
    isCurrent: boolean;
  };

  const userMarginPct = currentMarginFrac * 100;

  const rows: Row[] = usable.map((v) => {
    const base = v.monthly_price_net as number;
    const rate = currentMarginFrac < 1 ? base / (1 - currentMarginFrac) : base;
    const marginToFitPct = monthlyBudget && monthlyBudget > 0
      ? (1 - base / monthlyBudget) * 100
      : null;
    const fitsBudget = marginToFitPct == null
      ? true
      : marginToFitPct >= userMarginPct;
    const isCurrent =
      v.duration_months === currentDuration && v.annual_mileage === currentMileage;
    return { v, rate, marginToFitPct, fitsBudget, isCurrent };
  });

  // Sort: current first, then fitting variants by margin-to-fit desc (best
  // business first), then non-fitting variants by margin-to-fit desc.
  rows.sort((a, b) => {
    if (a.isCurrent && !b.isCurrent) return -1;
    if (b.isCurrent && !a.isCurrent) return 1;
    if (a.fitsBudget !== b.fitsBudget) return a.fitsBudget ? -1 : 1;
    if (a.marginToFitPct != null && b.marginToFitPct != null) {
      return b.marginToFitPct - a.marginToFitPct;
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
                <th className="text-right px-2 py-1.5 font-semibold">Przebieg/kontrakt</th>
                <th className="text-right px-2 py-1.5 font-semibold">Rata @ {(currentMarginFrac * 100).toFixed(0)}%</th>
                {monthlyBudget && monthlyBudget > 0 && (
                  <th className="text-right px-2 py-1.5 font-semibold">Marża</th>
                )}
                <th className="text-center px-2 py-1.5 font-semibold">Status</th>
                <th className="text-center px-2 py-1.5 font-semibold">Akcja</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => {
                // Tier model when budget is set:
                //   marginToFit < 0          → 'fail'    (nawet bez marży nie wchodzi)
                //   fitsBudget=false         → 'tight'   (zmieści się tylko przy niższej marży)
                //   marginToFit ≥ 12         → 'good'    (świetna)
                //   marginToFit ≥ 5          → 'warning' (graniczna)
                //   else                     → 'loss'    (niska)
                // Without budget → 'neutral'.
                const tier = row.marginToFitPct == null
                  ? 'neutral'
                  : row.marginToFitPct < 0
                  ? 'fail'
                  : !row.fitsBudget
                  ? 'tight'
                  : row.marginToFitPct >= 12
                  ? 'good'
                  : row.marginToFitPct >= 5
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
                  : tier === 'tight'
                  ? 'bg-amber-50/60 hover:bg-amber-100'
                  : tier === 'fail'
                  ? 'bg-red-50/40 hover:bg-red-50 opacity-70'
                  : 'hover:bg-slate-50';

                const tierBadge = {
                  good: { text: '✓ świetna', cls: 'bg-emerald-100 text-emerald-800' },
                  warning: { text: '⚠ graniczna', cls: 'bg-amber-100 text-amber-800' },
                  loss: { text: '⚠ niska', cls: 'bg-orange-100 text-orange-800' },
                  tight: { text: '⚠ obniż marżę', cls: 'bg-amber-100 text-amber-900' },
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
                      {fmtPLN((row.v.annual_mileage as number) * (row.v.duration_months as number) / 12)} km
                    </td>
                    <td className="px-2 py-1.5 font-mono tabular-nums text-right font-semibold text-slate-900">
                      {fmtPLN(row.rate)}
                    </td>
                    {monthlyBudget && monthlyBudget > 0 && (
                      <td
                        className={`px-2 py-1.5 font-mono tabular-nums text-right font-semibold ${
                          row.marginToFitPct == null
                            ? 'text-slate-900'
                            : row.marginToFitPct < 0
                            ? 'text-red-700'
                            : row.fitsBudget
                            ? 'text-emerald-700'
                            : 'text-amber-700'
                        }`}
                        title={
                          row.marginToFitPct != null
                            ? `Maks. marża, przy której wariant wchodzi w budżet (oczekiwana: ${userMarginPct.toFixed(1)}%)`
                            : undefined
                        }
                      >
                        {row.marginToFitPct != null
                          ? `${row.marginToFitPct.toFixed(1)}%`
                          : '—'}
                      </td>
                    )}
                    <td className="px-2 py-1.5 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${tierBadge.cls}`}>
                        {tierBadge.text}
                      </span>
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      {(() => {
                        const dur = row.v.duration_months as number;
                        const mil = row.v.annual_mileage as number;
                        const marginTag = `m${Math.round((displayMarginPct ?? 0) * 10)}`;
                        const variantId = row.v.kalkulacja_id
                          ? `${vehicleId}_${dur}_${mil}_${row.v.kalkulacja_id}_${marginTag}`
                          : `${vehicleId}_${dur}_${mil}_${marginTag}`;
                        const inCart = cartItems.some((it) => it.id === variantId);
                        return (
                          <button
                            type="button"
                            disabled={inCart}
                            onClick={(e) => {
                              e.stopPropagation();
                              addToCart({
                                id: variantId,
                                brand: car.brand || '',
                                model: car.model || '',
                                powertrain: car.fuel || '',
                                vin_or_config: car.configuration_code || car.offer_number || 'Brak',
                                term: dur,
                                mileage: mil,
                                net_installment: row.rate,
                                contribution: 0,
                                margin_pct: displayMarginPct,
                                variants: [],
                                standard_equipment: [],
                                factory_options: [],
                                dealer_options: [],
                                calculation_data: { ...car, vehicle_id: vehicleId, kalkulacja_id: row.v.kalkulacja_id },
                              });
                            }}
                            title={inCart ? 'Wariant już w ofercie' : 'Dodaj ten wariant do oferty'}
                            className={`inline-flex items-center justify-center w-6 h-6 rounded-md border transition-all ${
                              inCart
                                ? 'border-emerald-200 bg-emerald-50 text-emerald-600 cursor-default'
                                : 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:border-blue-400'
                            }`}
                          >
                            {inCart ? <Check className="w-3 h-3" /> : <ShoppingCart className="w-3 h-3" />}
                          </button>
                        );
                      })()}
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
