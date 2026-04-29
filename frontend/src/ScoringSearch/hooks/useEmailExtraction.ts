import { useState, useCallback } from 'react';
import { apiClient } from '../../lib/apiClient';
import type { SearchContext, SelectedFeature } from '../types';

interface ExtractedFeatureItem {
  feature_key: string;
  feature_type?: 'boolean' | 'numeric' | 'text' | 'enum';
  op?: 'eq' | 'gte' | 'lte' | 'in';
  value_bool?: boolean | null;
  value_num?: number | null;
  value_text?: string | null;
  display_name?: string;
}

interface ExtractionResponse {
  status?: string;
  extracted_features?: ExtractedFeatureItem[];
  extracted_financials?: {
    price_max?: number | null;
    duration_months?: number | null;
    annual_mileage?: number | null;
  };
  extracted_brands?: string[];
  extracted_models?: string[];
  rejected_count?: number;
}

export interface ExtractionSummary {
  brands: string[];
  models: string[];
  budget?: number;
  durationMonths?: number;
  annualMileage?: number;
  featuresCount: number;
  unmatchedBrands: string[];
  unmatchedModels: string[];
}

const featureToRequirement = (f: ExtractedFeatureItem): SelectedFeature | null => {
  if (f.feature_type === 'boolean' && f.value_bool === true) {
    return {
      feature_key: f.feature_key,
      operator: 'eq',
      value: true,
      requirement: 'MUST_HAVE',
      weight: 1,
    };
  }
  if (f.feature_type === 'numeric' && f.value_num != null) {
    return {
      feature_key: f.feature_key,
      operator: f.op === 'gte' || f.op === 'lte' ? f.op : 'eq',
      value: f.value_num,
      requirement: 'MUST_HAVE',
      weight: 1,
    };
  }
  if ((f.feature_type === 'text' || f.feature_type === 'enum') && f.value_text) {
    return {
      feature_key: f.feature_key,
      operator: 'eq',
      value: f.value_text,
      requirement: 'MUST_HAVE',
      weight: 1,
    };
  }
  return null;
};

const matchCaseInsensitive = (needles: string[], haystack: string[]): {
  matched: string[];
  unmatched: string[];
} => {
  const haystackLower = new Map(haystack.map((h) => [h.toLowerCase(), h]));
  const matched: string[] = [];
  const unmatched: string[] = [];
  for (const n of needles) {
    const canonical = haystackLower.get(n.toLowerCase());
    if (canonical) matched.push(canonical);
    else unmatched.push(n);
  }
  return { matched, unmatched };
};

interface UseEmailExtractionParams {
  searchContext: SearchContext;
  setSearchContext: (ctx: SearchContext) => void;
  setSelectedFeatures: (features: SelectedFeature[]) => void;
  knownBrands: string[];
  brandModelMap: Record<string, string[]>;
}

export function useEmailExtraction({
  searchContext,
  setSearchContext,
  setSelectedFeatures,
  knownBrands,
  brandModelMap,
}: UseEmailExtractionParams) {
  const [emailText, setEmailText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSummary, setLastSummary] = useState<ExtractionSummary | null>(null);

  const extract = useCallback(async () => {
    if (!emailText.trim()) return;
    setExtracting(true);
    setError(null);
    try {
      const res = await apiClient.fetch('/api/features/extract-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_text: emailText }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: ExtractionResponse = await res.json();
      if (data.status !== 'success') {
        throw new Error('Ekstrakcja nie zwróciła sukcesu');
      }

      const extractedBrands = data.extracted_brands || [];
      const extractedModels = data.extracted_models || [];
      const { matched: matchedBrands, unmatched: unmatchedBrands } = matchCaseInsensitive(
        extractedBrands,
        knownBrands,
      );
      const knownModels = Array.from(
        new Set(matchedBrands.flatMap((b) => brandModelMap[b] || [])),
      );
      const { matched: matchedModels, unmatched: unmatchedModels } = matchCaseInsensitive(
        extractedModels,
        knownModels,
      );

      const fin = data.extracted_financials || {};
      const annualMileage = fin.annual_mileage || undefined;
      const durationMonths = fin.duration_months || undefined;

      const newCtx: SearchContext = { ...searchContext };
      if (matchedBrands.length > 0) {
        newCtx.brands = Array.from(new Set([...newCtx.brands, ...matchedBrands]));
      }
      if (matchedModels.length > 0) {
        newCtx.models = Array.from(new Set([...newCtx.models, ...matchedModels]));
      }
      let matrixTouched = false;
      if (fin.price_max && fin.price_max > 0) {
        newCtx.monthly_budget = fin.price_max;
        matrixTouched = true;
      }
      if (durationMonths) {
        newCtx.exact_duration_months = durationMonths;
        newCtx.exact_mode = true;
        matrixTouched = true;
      }
      if (annualMileage && durationMonths) {
        newCtx.exact_total_mileage = Math.round((annualMileage * durationMonths) / 12);
        matrixTouched = true;
      } else if (annualMileage) {
        newCtx.exact_total_mileage = Math.round(annualMileage * (newCtx.exact_duration_months / 12));
        matrixTouched = true;
      }
      if (matrixTouched) {
        newCtx.useMatrixFilters = true;
      }

      const features = data.extracted_features || [];
      const newFeatures = features
        .map(featureToRequirement)
        .filter((f): f is SelectedFeature => f !== null);
      if (newFeatures.length > 0) {
        setSelectedFeatures(newFeatures);
      }

      setSearchContext(newCtx);

      setLastSummary({
        brands: matchedBrands,
        models: matchedModels,
        budget: fin.price_max ?? undefined,
        durationMonths,
        annualMileage,
        featuresCount: newFeatures.length,
        unmatchedBrands,
        unmatchedModels,
      });
    } catch (err) {
      console.error('Email extraction failed:', err);
      setError(err instanceof Error ? err.message : 'Nieznany błąd');
    } finally {
      setExtracting(false);
    }
  }, [emailText, knownBrands, brandModelMap, searchContext, setSearchContext, setSelectedFeatures]);

  return {
    emailText,
    setEmailText,
    extracting,
    error,
    lastSummary,
    extract,
    clearSummary: () => setLastSummary(null),
  };
}
