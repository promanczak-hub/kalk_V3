import { useCallback } from 'react';
import type { SearchContext, SelectedFeature } from '../types';

export const useScoringFilterActions = (
  searchContext: SearchContext,
  onContextChange: (ctx: SearchContext) => void,
  selectedFeatures: SelectedFeature[],
  onFeaturesChange: (features: SelectedFeature[]) => void
) => {
  const toggleBrand = useCallback((brand: string) => {
    const current = searchContext.brands;
    const next = current.includes(brand)
      ? current.filter((b: string) => b !== brand)
      : [...current, brand];
    onContextChange({ ...searchContext, brands: next, models: [], trims: [] });
  }, [searchContext, onContextChange]);

  const toggleTrim = useCallback((trim: string) => {
    const current = searchContext.trims || [];
    const next = current.includes(trim)
      ? current.filter((t: string) => t !== trim)
      : [...current, trim];
    onContextChange({ ...searchContext, trims: next });
  }, [searchContext, onContextChange]);

  const toggleBodyType = useCallback((name: string) => {
    const current = searchContext.bodyTypes || [];
    const next = current.includes(name) ? current.filter((b: string) => b !== name) : [...current, name];
    onContextChange({ ...searchContext, bodyTypes: next });
  }, [searchContext, onContextChange]);

  const toggleFuelType = useCallback((fuel: string) => {
    const current = searchContext.fuelTypes || [];
    const next = current.includes(fuel) ? current.filter(f => f !== fuel) : [...current, fuel];
    onContextChange({ ...searchContext, fuelTypes: next });
  }, [searchContext, onContextChange]);

  const toggleTransmission = useCallback((transmission: string) => {
    const current = searchContext.transmissions || [];
    const next = current.includes(transmission) ? current.filter(t => t !== transmission) : [...current, transmission];
    onContextChange({ ...searchContext, transmissions: next });
  }, [searchContext, onContextChange]);

  const toggleDriveType = useCallback((drive: string) => {
    const current = searchContext.driveTypes || [];
    const next = current.includes(drive) ? current.filter(d => d !== drive) : [...current, drive];
    onContextChange({ ...searchContext, driveTypes: next });
  }, [searchContext, onContextChange]);

  const toggleSamarClassId = useCallback((id: number) => {
    const current = searchContext.samarClassIds || [];
    const next = current.includes(id) ? current.filter(i => i !== id) : [...current, id];
    onContextChange({ ...searchContext, samarClassIds: next });
  }, [searchContext, onContextChange]);

  const isFeatureSelected = useCallback((key: string, value: string) =>
    selectedFeatures.some(f => f.feature_key === key && f.value === value),
  [selectedFeatures]);

  const toggleFeature = useCallback((key: string, value: string, weight = 1, isMustHave = false) => {
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
  }, [selectedFeatures, onFeaturesChange]);

  const updateRangeFeature = useCallback((key: string, val: [number, number], minLimit: number, maxLimit: number) => {
    const clone = [...selectedFeatures].filter(f => !(f.feature_key === key && (f.operator === 'gte' || f.operator === 'lte')));
    
    if (val[0] > minLimit) {
      clone.push({ feature_key: key, operator: 'gte', value: val[0], requirement: 'MUST_HAVE', weight: 1 });
    }
    if (val[1] < maxLimit) {
      clone.push({ feature_key: key, operator: 'lte', value: val[1], requirement: 'MUST_HAVE', weight: 1 });
    }
    
    onFeaturesChange(clone);
  }, [selectedFeatures, onFeaturesChange]);

  const isOptionSelected = useCallback((prefix: string, name: string) =>
    selectedFeatures.some(f => f.feature_key === `${prefix}${name}`),
  [selectedFeatures]);

  const toggleOption = useCallback((prefix: string, name: string) => {
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
  }, [selectedFeatures, onFeaturesChange]);

  return {
    toggleBrand,
    toggleTrim,
    toggleBodyType,
    toggleFuelType,
    toggleTransmission,
    toggleDriveType,
    toggleSamarClassId,
    isFeatureSelected,
    toggleFeature,
    updateRangeFeature,
    isOptionSelected,
    toggleOption
  };
};
