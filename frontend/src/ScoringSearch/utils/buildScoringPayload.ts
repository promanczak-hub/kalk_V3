import type { SelectedFeature, SearchContext } from '../types';
import { computeSearchRanges } from './computeSearchRanges';

export const buildScoringPayload = (searchContext: SearchContext, selectedFeatures: SelectedFeature[]) => {
  // Build requirements payload out of selectedFeatures and context
  const requirements = [...selectedFeatures];

  // SOFT MATRIX MODE: when a semantic query is present (AI-extracted from text),
  // we trust vector search to surface relevant candidates. Matrix params then
  // become preferences (NICE_TO_HAVE) rather than hard filters that wipe results
  // to zero. Without semanticQuery (manual matrix mode), keep MUST_HAVE for
  // precision.
  const softMatrix = !!searchContext.semanticQuery?.trim();
  const matrixReq = softMatrix ? 'NICE_TO_HAVE' : 'MUST_HAVE';

  // Apply matrix filters only if the toggle is enabled
  if (searchContext.useMatrixFilters) {
    const {
      searchDurationMin,
      searchDurationMax,
      searchAnnualMin,
      searchAnnualMax
    } = computeSearchRanges(searchContext);

    // Duration range (gte + lte pair)
    requirements.push({ feature_key: 'duration_months', operator: 'gte', value: searchDurationMin, requirement: matrixReq, weight: 1 });
    requirements.push({ feature_key: 'duration_months', operator: 'lte', value: searchDurationMax, requirement: matrixReq, weight: 1 });
    // Mileage range (gte + lte pair)
    requirements.push({ feature_key: 'annual_mileage', operator: 'gte', value: searchAnnualMin, requirement: matrixReq, weight: 1 });
    requirements.push({ feature_key: 'annual_mileage', operator: 'lte', value: searchAnnualMax, requirement: matrixReq, weight: 1 });

    if (searchContext.margin_pct !== undefined) {
      requirements.push({ feature_key: 'margin_pct', operator: 'gte', value: searchContext.margin_pct, requirement: matrixReq, weight: 1 });
    }
    if (searchContext.monthly_budget) {
      // Budget always stays soft when semantic — backend already computes
      // applied_margin_pct per car to fit budget; we don't need to filter.
      requirements.push({ feature_key: 'monthly_price_net', operator: 'lte', value: searchContext.monthly_budget, requirement: matrixReq, weight: 1 });
    }
  }

  // Body type filter — keep as MUST_HAVE because body style (kombi vs SUV) is
  // a categorical choice, not a soft preference.
  if (searchContext.bodyTypes.length > 0) {
    requirements.push({
      feature_key: 'body_style',
      operator: 'in',
      value: searchContext.bodyTypes,
      requirement: 'MUST_HAVE',
      weight: 1
    });
  }

  return {
    brands: searchContext.brands.length > 0 ? searchContext.brands : null,
    models: searchContext.models.length > 0 ? searchContext.models : null,
    trims: searchContext.trims.length > 0 ? searchContext.trims : null,
    samar_class_ids: searchContext.samarClassIds.length > 0 ? searchContext.samarClassIds : null,
    requirements: requirements,
    semantic_query: searchContext.semanticQuery || null
  };
};
