import React from 'react';
import { ExternalLink, ShoppingCart, Check } from 'lucide-react';

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
  const marginFrac = Math.min(searchContext.margin_pct ?? 0, 99) / 100;
  const monthlyDisplay = rawMonthly != null && marginFrac < 1 ? rawMonthly / (1 - marginFrac) : null;
  const calcDate = price?.calculated_at
    ? new Date(price.calculated_at).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : null;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    const basePrice = car.best_monthly_price ?? 0;
    const finalPrice = marginFrac < 1 ? basePrice / (1 - marginFrac) : basePrice;
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
      margin_pct: searchContext.margin_pct || 0,
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
          {!!car.suggested_discount_pct && car.suggested_discount_pct > 0 && (
            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono" title="Sugerowany rabat dealerski">
              BD <span className="font-semibold text-slate-700">{car.suggested_discount_pct}%</span>
            </span>
          )}
        </div>

        {pricesLoading ? (
          <div className="text-xs text-slate-400">Ładowanie kalkulacji…</div>
        ) : monthlyDisplay != null ? (
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
                {searchContext.margin_pct ?? 0}%
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">Okres × Przebieg</div>
              <div className="text-xs text-slate-700 font-mono tabular-nums">
                {targetDuration} mc · {fmtPLN(targetAnnualMileage)} km/rok
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">Opony · Serwis</div>
              <div className="text-xs text-slate-700 font-mono">
                {[car.tire_class, car.service_cost_type].filter(Boolean).join(' · ') || '—'}
              </div>
            </div>
          </div>
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
