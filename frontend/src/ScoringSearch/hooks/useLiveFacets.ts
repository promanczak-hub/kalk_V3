import { useMemo, useRef } from 'react';
import type { ScoredVehicle, SamarClass } from '../types';

export interface LiveFacetItem {
  value: string;
  count: number;
}

export interface SamarFacetItem {
  id: number;
  value: string;
  count: number;
}

export interface LiveFacets {
  fuels: LiveFacetItem[];
  transmissions: LiveFacetItem[];
  driveTypes: LiveFacetItem[];
  samarItems: SamarFacetItem[];
}

export const useLiveFacets = (
  searchResults: ScoredVehicle[],
  samarClasses: SamarClass[]
): LiveFacets => {
  // Accumulate all values ever seen across searches so dimmed options remain visible
  const allSeenRef = useRef<{
    fuels: Set<string>;
    transmissions: Set<string>;
    driveTypes: Set<string>;
  }>({ fuels: new Set(), transmissions: new Set(), driveTypes: new Set() });

  return useMemo(() => {
    const fuelCounts = new Map<string, number>();
    const transmCounts = new Map<string, number>();
    const driveCounts = new Map<string, number>();
    const samarCounts = new Map<string, number>();

    for (const v of searchResults) {
      // Backend returns fuel_type; ScoredVehicle.fuel is a fallback alias
      const fuelVal = (v as unknown as { fuel_type?: string }).fuel_type || v.fuel;
      if (fuelVal) {
        fuelCounts.set(fuelVal, (fuelCounts.get(fuelVal) || 0) + 1);
        allSeenRef.current.fuels.add(fuelVal);
      }
      if (v.transmission) {
        transmCounts.set(v.transmission, (transmCounts.get(v.transmission) || 0) + 1);
        allSeenRef.current.transmissions.add(v.transmission);
      }
      if (v.drive_type) {
        driveCounts.set(v.drive_type, (driveCounts.get(v.drive_type) || 0) + 1);
        allSeenRef.current.driveTypes.add(v.drive_type);
      }
      if (v.vehicle_class) {
        samarCounts.set(v.vehicle_class, (samarCounts.get(v.vehicle_class) || 0) + 1);
      }
    }

    const toItems = (allSeen: Set<string>, counts: Map<string, number>): LiveFacetItem[] =>
      [...allSeen]
        .map(v => ({ value: v, count: counts.get(v) || 0 }))
        .sort((a, b) => b.count - a.count);

    // SAMAR: use initialData classes as canonical list, enrich with live counts
    const samarItems: SamarFacetItem[] = samarClasses
      .map(sc => ({ id: sc.id, value: sc.name, count: samarCounts.get(sc.name) || 0 }))
      .filter(item => item.count > 0 || allSeenRef.current.fuels.size === 0)
      .sort((a, b) => b.count - a.count);

    return {
      fuels: toItems(allSeenRef.current.fuels, fuelCounts),
      transmissions: toItems(allSeenRef.current.transmissions, transmCounts),
      driveTypes: toItems(allSeenRef.current.driveTypes, driveCounts),
      samarItems,
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchResults, samarClasses]);
};
