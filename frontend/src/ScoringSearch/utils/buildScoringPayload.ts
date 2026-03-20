import type { SelectedFeature, SearchContext } from '../types';

export const buildScoringPayload = (searchContext: SearchContext, selectedFeatures: SelectedFeature[]) => {
  // Build requirements payload out of selectedFeatures and context
  const requirements = [...selectedFeatures];
  
  // Apply matrix filters only if the toggle is enabled
  if (searchContext.useMatrixFilters) {
    let searchDurationMin = searchContext.duration_months_range[0];
    let searchDurationMax = searchContext.duration_months_range[1];
    const targetDurationForAnnualMin = searchDurationMax; // To get minimum annual, divide by max duration
    const targetDurationForAnnualMax = searchDurationMin; // To get maximum annual, divide by min duration
    let searchAnnualMin = Math.max(10000, Math.round((searchContext.total_mileage_range[0] * 12) / targetDurationForAnnualMin));
    let searchAnnualMax = Math.min(80000, Math.round((searchContext.total_mileage_range[1] * 12) / targetDurationForAnnualMax));

    if (searchContext.exact_mode) {
       const d = searchContext.exact_duration_months;
       if (d <= 24) { searchDurationMin = 24; searchDurationMax = 24; }
       else if (d <= 36) { searchDurationMin = 24; searchDurationMax = 36; }
       else if (d <= 48) { searchDurationMin = 36; searchDurationMax = 48; }
       else { searchDurationMin = 48; searchDurationMax = 60; }
       
       const annual = Math.round((searchContext.exact_total_mileage * 12) / d);
       const bucket = Math.round(annual / 5000) * 5000;
       searchAnnualMin = Math.max(10000, bucket - 5000);
       searchAnnualMax = Math.min(80000, bucket + 5000);
    }

    // Duration range (gte + lte pair)
    requirements.push({ feature_key: 'duration_months', operator: 'gte', value: searchDurationMin, requirement: 'MUST_HAVE', weight: 1 });
    requirements.push({ feature_key: 'duration_months', operator: 'lte', value: searchDurationMax, requirement: 'MUST_HAVE', weight: 1 });
    // Mileage range (gte + lte pair)
    requirements.push({ feature_key: 'annual_mileage', operator: 'gte', value: searchAnnualMin, requirement: 'MUST_HAVE', weight: 1 });
    requirements.push({ feature_key: 'annual_mileage', operator: 'lte', value: searchAnnualMax, requirement: 'MUST_HAVE', weight: 1 });
    
    if (searchContext.margin_pct !== undefined) {
      requirements.push({ feature_key: 'margin_pct', operator: 'gte', value: searchContext.margin_pct, requirement: 'MUST_HAVE', weight: 1 });
    }
    if (searchContext.monthly_budget) {
      requirements.push({ feature_key: 'monthly_price_net', operator: 'lte', value: searchContext.monthly_budget, requirement: 'MUST_HAVE', weight: 1 });
    }
  }

  // Body type filter — każdy wybrany typ jako osobna cecha MUST_HAVE
  if (searchContext.bodyTypes.length > 0) {
    for (const bt of searchContext.bodyTypes) {
      requirements.push({
        feature_key: 'body_style',
        operator: 'eq',
        value: bt,
        requirement: 'MUST_HAVE',
        weight: 1
      });
    }
  }

  return {
    brands: searchContext.brands.length > 0 ? searchContext.brands : null,
    models: searchContext.models.length > 0 ? searchContext.models : null,
    trims: searchContext.trims.length > 0 ? searchContext.trims : null,
    samar_class_ids: searchContext.samarClassIds.length > 0 ? searchContext.samarClassIds : null,
    requirements: requirements
  };
};
