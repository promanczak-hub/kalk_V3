import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '../../lib/apiClient';
import type { SelectedFeature } from '../types';

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
  // Snapshot of the kalkulacja's pricing toggles + financing knobs. Same for
  // every variant under the same kalkulacja_id.
  discount_pct?: number | null;
  bank_margin_pct?: number | null;
  wibor_pct?: number | null;
  tires_included?: boolean | null;
  tire_buyback?: boolean | null;
  insurance_included?: boolean | null;
  replacement_car?: boolean | null;
  service_included?: boolean | null;
}

export interface SimilarityReasons {
  samar_match: boolean;
  body_match: boolean;
  fuel_match: boolean;
  drive_match: boolean;
  equipment_match: boolean;
  equipment_similarity_pct: number | null;
  is_same_brand: boolean;
  price_pct_diff: number | null;
  is_cheaper?: boolean | null;
  samar_category: string | null;
  body_style: string | null;
  base_price?: number | null;
  paid_options?: Record<string, unknown>[] | null;
  is_fallback_match?: boolean;

  // ── V2 fields (rabat-aware + utility features) ──
  discount_pct?: number | null;          // candidate offer discount % (0-100)
  final_price_net?: number | null;       // candidate's final price after discount
  final_price_pct_diff?: number | null;  // % diff vs source FINAL price
  discount_pct_diff?: number | null;     // candidate.disc - source.disc (pp)

  payload_kg?: number | null;
  cargo_volume_m3?: number | null;
  body_type?: string | null;

  // ── Apple-to-apple setup check ──
  setup_match?: boolean | null;          // true = same (tire, service) as source
  source_tire_class?: string | null;
  source_service_type?: string | null;

  // ── Matrix params the rate was priced for (echoed RPC inputs) ──
  matched_duration_months?: number | null;
  matched_annual_mileage?: number | null;
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
  // Technical metadata
  power_hp: number | null;
  engine_label?: string | null;
  body_style: string | null;
  vehicle_class: string | null;
  drive_type: string | null;
  // Why this vehicle is similar
  similarity_reasons?: SimilarityReasons | null;
  ai_label?: string | null;
  kalkulacja_id?: string | null;
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

    doFetch();
    return () => { 
      cancelled = true; 
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
  similarityMode: 'semantic' | 'exact' = 'semantic',
  requirements: SelectedFeature[] = []
): { similarVehicles: Record<string, SimilarVehicle[]>; loading: boolean } {
  const [similarVehicles, setSimilarVehicles] = useState<Record<string, SimilarVehicle[]>>({});
  const [loading, setLoading] = useState(false);

  // Zbudujmy stabilny hash z tablicy requirements do użycia w useEffect dependencies
  const requirementsHash = useMemo(() => JSON.stringify(requirements), [requirements]);

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
            limit: 8,
            mode: similarityMode,
            requirements: requirements
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

    doFetch();
    return () => { 
      cancelled = true; 
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleIds.join(','), durationMonths, annualMileage, enabled, similarityMode, requirementsHash]);

  return { similarVehicles, loading };
}
