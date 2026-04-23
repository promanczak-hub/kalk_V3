import type { SearchContext } from '../types';
import { MATRIX_LIMITS } from '../../config/matrixLimits';

export interface SearchRanges {
  searchDurationMin: number;
  searchDurationMax: number;
  searchAnnualMin: number;
  searchAnnualMax: number;
  targetDuration: number;
  targetAnnualMileage: number;
}

export function computeSearchRanges(searchContext: SearchContext): SearchRanges {
  let searchDurationMin = searchContext.duration_months_range[0];
  let searchDurationMax = searchContext.duration_months_range[1];
  
  if (searchContext.exact_mode) {
    const d = searchContext.exact_duration_months;
    searchDurationMin = d;
    searchDurationMax = d;
    
    const annual = Math.round((searchContext.exact_total_mileage * 12) / d);
    const bucket = Math.round(annual / 2500) * 2500;
    const searchAnnualMinObj = Math.max(MATRIX_LIMITS.KM_MIN_ANNUAL, Math.min(MATRIX_LIMITS.KM_MAX_ANNUAL, bucket));
    
    return {
      searchDurationMin: d,
      searchDurationMax: d,
      searchAnnualMin: searchAnnualMinObj,
      searchAnnualMax: searchAnnualMinObj,
      targetDuration: d,
      targetAnnualMileage: Math.round((searchContext.exact_total_mileage * 12) / d)
    };
  }

  const targetDurationForAnnualMin = searchDurationMax; // To get minimum annual, divide by max duration
  const targetDurationForAnnualMax = searchDurationMin; // To get maximum annual, divide by min duration
  const searchAnnualMinObj = Math.max(10000, Math.round((searchContext.total_mileage_range[0] * 12) / targetDurationForAnnualMin));
  const searchAnnualMaxObj = Math.min(MATRIX_LIMITS.KM_MAX_ANNUAL, Math.round((searchContext.total_mileage_range[1] * 12) / targetDurationForAnnualMax));

  const targetDuration = Math.round((searchDurationMin + searchDurationMax) / 2);
  const selectedMileage = Math.round((searchContext.total_mileage_range[0] + searchContext.total_mileage_range[1]) / 2);
  const targetAnnualMileage = Math.round((selectedMileage * 12) / targetDuration);

  return {
    searchDurationMin,
    searchDurationMax,
    searchAnnualMin: searchAnnualMinObj,
    searchAnnualMax: searchAnnualMaxObj,
    targetDuration,
    targetAnnualMileage
  };
}
