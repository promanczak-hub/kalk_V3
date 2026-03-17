import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";

export function useVehicleParamPreview(
  classId: number | null | undefined,
  engineId: number | null | undefined,
  serviceCostType: "ASO" | "nonASO",
  tireClass: string,
  rimDiameter: number | null,
  vehicleVintage: "current" | "previous",
  isMetalic: boolean
) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [paramPreview, setParamPreview] = useState<any>(null);

  const fetchParamPreview = useCallback(async (signal?: AbortSignal) => {
    if (!classId || !engineId) {
      setParamPreview(null);
      return;
    }
    try {
      const params = new URLSearchParams({
        samar_class_id: String(classId),
        engine_type_id: String(engineId),
        power_band: "MID",
        service_type: serviceCostType,
        tire_class: tireClass,
        vehicle_vintage: vehicleVintage,
        is_metalic: String(isMetalic),
      });
      if (rimDiameter) params.set("rim_diameter", String(rimDiameter));
      
      const res = await apiFetch(`/api/param-preview?${params}`, { signal });
      if (res.ok) {
        setParamPreview(await res.json());
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        // silently fail
      }
    }
  }, [classId, engineId, serviceCostType, tireClass, rimDiameter, vehicleVintage, isMetalic]);

  useEffect(() => {
    const controller = new AbortController();
    fetchParamPreview(controller.signal);
    return () => {
      controller.abort();
    };
  }, [fetchParamPreview]);

  return { paramPreview, controlCenter: null };
}

