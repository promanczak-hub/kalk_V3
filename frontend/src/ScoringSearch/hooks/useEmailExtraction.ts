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
  requirement?: 'MUST_HAVE' | 'NICE_TO_HAVE';
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
  extracted_trims?: string[];
  semantic_hint?: string | null;
  rejected_count?: number;
}

export interface ExtractionSummary {
  brands: string[];
  models: string[];
  trims: string[];
  bodyTypes: string[];
  budget?: number;
  durationMonths?: number;
  annualMileage?: number;
  featuresCount: number;
  mustHaveCount: number;
  niceToHaveCount: number;
  semanticHint?: string;
  unmatchedBrands: string[];
  unmatchedModels: string[];
}

const featureToRequirement = (f: ExtractedFeatureItem): SelectedFeature | null => {
  const req = f.requirement === 'NICE_TO_HAVE' ? 'NICE_TO_HAVE' : 'MUST_HAVE';
  if (f.feature_type === 'boolean' && f.value_bool === true) {
    return {
      feature_key: f.feature_key,
      operator: 'eq',
      value: true,
      requirement: req,
      weight: 1,
    };
  }
  if (f.feature_type === 'numeric' && f.value_num != null) {
    return {
      feature_key: f.feature_key,
      operator: f.op === 'gte' || f.op === 'lte' ? f.op : 'eq',
      value: f.value_num,
      requirement: req,
      weight: 1,
    };
  }
  if ((f.feature_type === 'text' || f.feature_type === 'enum') && f.value_text) {
    return {
      feature_key: f.feature_key,
      operator: 'eq',
      value: f.value_text,
      requirement: req,
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
  knownBodyTypes?: string[];
}

export function useEmailExtraction({
  searchContext,
  setSearchContext,
  setSelectedFeatures,
  knownBrands,
  brandModelMap,
  knownBodyTypes = [],
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
      const extractedTrims = data.extracted_trims || [];
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
      const semanticHint = data.semantic_hint || undefined;

      const newCtx: SearchContext = { ...searchContext };
      if (matchedBrands.length > 0) {
        newCtx.brands = Array.from(new Set([...newCtx.brands, ...matchedBrands]));
      }
      if (matchedModels.length > 0) {
        newCtx.models = Array.from(new Set([...newCtx.models, ...matchedModels]));
      }
      if (extractedTrims.length > 0) {
        newCtx.trims = Array.from(new Set([...(newCtx.trims || []), ...extractedTrims]));
      }
      // VECTOR-FIRST: always feed the full query into semanticQuery so backend can
      // run multi-vector embedding search (rpc_search_vehicles_multi_vector). Prefer
      // semanticHint when AI extracted one (more focused), otherwise use full text.
      newCtx.semanticQuery = semanticHint || emailText.trim();
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

      // VECTOR-FIRST: extracted features become soft preferences (NICE_TO_HAVE)
      // instead of hard MUST_HAVE filters. Backend's rpc_search_vehicles_multi_vector
      // already accounts for them via the equipment vector (weight 0.2). User can
      // still promote a chip to MUST_HAVE manually in the UI if they want strict
      // filtering — but default is "loose semantic" which always returns results
      // ranked by similarity instead of hard-filtering to zero.
      const features = data.extracted_features || [];

      // body_style is routed to the bodyTypes filter (visible chips in UI, MUST_HAVE)
      // rather than treated as a generic feature — same pattern as brands/models.
      const bodyStyleFeature = features.find((f) => f.feature_key === 'body_style');
      const extractedBodyTypes: string[] = [];
      if (bodyStyleFeature?.value_text) {
        const { matched } = matchCaseInsensitive([bodyStyleFeature.value_text], knownBodyTypes);
        if (matched.length > 0) {
          extractedBodyTypes.push(...matched);
        }
      }
      if (extractedBodyTypes.length > 0) {
        newCtx.bodyTypes = Array.from(new Set([...newCtx.bodyTypes, ...extractedBodyTypes]));
      }

      const nonBodyFeatures = features.filter((f) => f.feature_key !== 'body_style');
      const newFeatures = nonBodyFeatures
        .map((f) => featureToRequirement({ ...f, requirement: 'NICE_TO_HAVE' as const }))
        .filter((f): f is SelectedFeature => f !== null);
      const mustHaveCount = 0; // forced soft
      const niceToHaveCount = newFeatures.length;
      if (newFeatures.length > 0) {
        setSelectedFeatures(newFeatures);
      }

      setSearchContext(newCtx);

      setLastSummary({
        brands: matchedBrands,
        models: matchedModels,
        trims: extractedTrims,
        bodyTypes: extractedBodyTypes,
        budget: fin.price_max ?? undefined,
        durationMonths,
        annualMileage,
        featuresCount: newFeatures.length,
        mustHaveCount,
        niceToHaveCount,
        semanticHint,
        unmatchedBrands,
        unmatchedModels,
      });
    } catch (err) {
      console.error('Email extraction failed:', err);
      setError(err instanceof Error ? err.message : 'Nieznany błąd');
    } finally {
      setExtracting(false);
    }
  }, [emailText, knownBrands, brandModelMap, knownBodyTypes, searchContext, setSearchContext, setSelectedFeatures]);

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
