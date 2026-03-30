import { useState, useEffect } from 'react';
import { apiClient } from '../../lib/apiClient';

export interface PriceForParams {
  duration_months: number | null;
  annual_mileage: number | null;
  monthly_price_net: number | null;
  calculated_at: string | null;
  found: boolean;
  variants_count?: number;
  tire_class?: string;
  service_type?: string;
  kalkulacja_id?: string;
}

export interface SimilarVehicle {
  vehicle_id: string;
  brand: string | null;
  model: string | null;
  version: string | null;
  fuel: string | null;
  transmission: string | null;
  best_monthly_price: number | null;
  similarity_score_pct: number | null;
  image_url?: string;
  // New technical metadata
  power_hp: number | null;
  body_style: string | null;
  vehicle_class: string | null;
  drive_type: string | null;
}

export function useBatchPrices(
  vehicleIds: string[],
  durationMonthsMin: number,
  durationMonthsMax: number,
  annualMileageMin: number,
  annualMileageMax: number,
  enabled: boolean,
): { prices: Record<string, { price_for_params?: PriceForParams, variants?: PriceForParams[] }>; loading: boolean } {
  const [prices, setPrices] = useState<Record<string, { price_for_params?: PriceForParams, variants?: PriceForParams[] }>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled || !vehicleIds.length) {
      setPrices({});
      return;
    }
    let cancelled = false;

    const doFetch = async () => {
      setLoading(true);
      try {
        const r = await apiClient.fetch(`/api/scoring-search/cache/batch-prices`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            vehicle_ids: vehicleIds, 
            duration_months_min: durationMonthsMin,
            duration_months_max: durationMonthsMax,
            annual_mileage_min: annualMileageMin,
            annual_mileage_max: annualMileageMax,
          }),
        });
        const data = await r.json();
        if (!cancelled) setPrices(data.prices || {});
      } catch {
        if (!cancelled) setPrices({});
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleIds.join(','), durationMonthsMin, durationMonthsMax, annualMileageMin, annualMileageMax, enabled]);

  return { prices, loading };
}

export function useBatchSimilarVehicles(
  vehicleIds: string[],
  durationMonths: number,
  annualMileage: number,
  enabled: boolean,
  mode: 'rule-based' | 'semantic' = 'rule-based'
): { similarVehicles: Record<string, SimilarVehicle[]>; loading: boolean } {
  const [similarVehicles, setSimilarVehicles] = useState<Record<string, SimilarVehicle[]>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled || !vehicleIds.length) {
      setSimilarVehicles({});
      return;
    }
    let cancelled = false;
    const doFetch = async () => {
      setLoading(true);
      try {
        const r = await apiClient.fetch(`/api/scoring-search/cache/batch-similar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            vehicle_ids: vehicleIds, 
            duration_months: durationMonths, 
            annual_mileage: annualMileage,
            limit: 5,
            mode: mode
          }),
        });
        const data = await r.json();
        if (!cancelled) setSimilarVehicles(data.results || {});
      } catch {
        if (!cancelled) setSimilarVehicles({});
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleIds.join(','), durationMonths, annualMileage, enabled, mode]);

  return { similarVehicles, loading };
}
