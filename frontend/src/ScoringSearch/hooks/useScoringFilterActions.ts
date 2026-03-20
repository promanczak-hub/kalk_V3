import type { SearchContext, SelectedFeature } from '../types';

export const useScoringFilterActions = (
  searchContext: SearchContext,
  onContextChange: (ctx: SearchContext) => void,
  selectedFeatures: SelectedFeature[],
  onFeaturesChange: (features: SelectedFeature[]) => void
) => {
  const toggleBrand = (brand: string) => {
    const current = searchContext.brands;
    const next = current.includes(brand)
      ? current.filter((b: string) => b !== brand)
      : [...current, brand];
    onContextChange({ ...searchContext, brands: next, models: [], trims: [] });
  };

  const toggleTrim = (trim: string) => {
    const current = searchContext.trims || [];
    const next = current.includes(trim)
      ? current.filter((t: string) => t !== trim)
      : [...current, trim];
    onContextChange({ ...searchContext, trims: next });
  };

  const toggleBodyType = (name: string) => {
    const current = searchContext.bodyTypes || [];
    const next = current.includes(name)
      ? current.filter((b: string) => b !== name)
      : [...current, name];
    onContextChange({ ...searchContext, bodyTypes: next });
  };

  const isFeatureSelected = (key: string, value: string) =>
    selectedFeatures.some(f => f.feature_key === key && f.value === value);

  const toggleFeature = (key: string, value: string, weight = 1, isMustHave = false) => {
    const existing = selectedFeatures.findIndex(f => f.feature_key === key && f.value === value);
    if (existing >= 0) {
      const clone = [...selectedFeatures];
      clone.splice(existing, 1);
      onFeaturesChange(clone);
    } else {
      onFeaturesChange([...selectedFeatures, {
        feature_key: key,
        operator: 'eq',
        value,
        requirement: isMustHave ? 'MUST_HAVE' : 'NICE_TO_HAVE',
        weight,
      }]);
    }
  };

  const updateRangeFeature = (key: string, val: [number, number], minLimit: number, maxLimit: number) => {
    const clone = [...selectedFeatures].filter(f => !(f.feature_key === key && (f.operator === 'gte' || f.operator === 'lte')));
    
    if (val[0] > minLimit) {
      clone.push({ feature_key: key, operator: 'gte', value: val[0], requirement: 'MUST_HAVE', weight: 1 });
    }
    if (val[1] < maxLimit) {
      clone.push({ feature_key: key, operator: 'lte', value: val[1], requirement: 'MUST_HAVE', weight: 1 });
    }
    
    onFeaturesChange(clone);
  };

  const isOptionSelected = (prefix: string, name: string) =>
    selectedFeatures.some(f => f.feature_key === `${prefix}${name}`);

  const toggleOption = (prefix: string, name: string) => {
    const key = `${prefix}${name}`;
    const existing = selectedFeatures.findIndex(f => f.feature_key === key);
    if (existing >= 0) {
      const clone = [...selectedFeatures];
      clone.splice(existing, 1);
      onFeaturesChange(clone);
    } else {
      onFeaturesChange([...selectedFeatures, {
        feature_key: key,
        operator: 'eq',
        value: 'true',
        requirement: 'MUST_HAVE',
        weight: 1,
      }]);
    }
  };

  return {
    toggleBrand,
    toggleTrim,
    toggleBodyType,
    isFeatureSelected,
    toggleFeature,
    updateRangeFeature,
    isOptionSelected,
    toggleOption
  };
};
