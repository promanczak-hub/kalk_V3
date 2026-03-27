import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "../../lib/apiClient";

interface ParamPreviewResponse {
  service: {
    found: boolean;
    rate_per_km: number;
    base_rate: number;
    m_brand: number;
    m_fuel: number;
    m_drive: number;
    m_gearbox: number;
    total_multiplier: number;
    type: string;
  };
  tires: { found: boolean; set_price_net: number; rim_diameter: number; tire_class: string };
  vintage: { found: boolean; correction_pct: number; label: string };
  color: { found: boolean; correction_pct: number; label: string };
  replacement_car: { found: boolean; daily_rate_net: number; avg_days_year: number };
}

export function useVehicleParamPreview(
  classId: number | null,
  engineId: number | null,
  brand?: string,
  fuel?: string,
  drive?: string,
  transmission?: string,
  serviceCostType?: string,
  targetMileage?: number,
  tireClass?: string,
  rimDiameter?: number | null,
  vehicleVintage?: "current" | "previous",
  isMetalic?: boolean,
  replacementCar?: boolean
) {
  const [paramPreview, setParamPreview] = useState<ParamPreviewResponse | null>(null);

  const fetchParamPreview = useCallback(async (signal?: AbortSignal) => {
    if (!classId) return;

    try {
      const tire_class_for_api = tireClass || "Premium";

      const params = new URLSearchParams({
        samar_class_id: classId.toString(),
        brand_normalized: brand || "",
        fuel_type: fuel || "",
        drive_type: drive || "",
        gearbox_type: transmission || "",
        service_type: serviceCostType || "ASO",
        target_mileage: targetMileage?.toString() || "20000",
        tire_class: tire_class_for_api,
        rim_diameter: rimDiameter?.toString() || "",
        vehicle_vintage: vehicleVintage || "current",
        is_metalic: isMetalic ? "true" : "false"
      });

      const data = await apiClient.get<ParamPreviewResponse>(`/api/param-preview?${params.toString()}`, { signal });
      setParamPreview(data);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      console.error("Failed to fetch parameter preview:", err);
    }
  }, [classId, brand, fuel, drive, transmission, serviceCostType, targetMileage, tireClass, rimDiameter, vehicleVintage, isMetalic]);

  const fetchRef = useRef(fetchParamPreview);
  
  useEffect(() => {
    fetchRef.current = fetchParamPreview;
  }, [fetchParamPreview]);

  useEffect(() => {
    const controller = new AbortController();
    
    // Call the current version of the fetch function
    fetchRef.current(controller.signal);

    return () => {
      controller.abort();
    };
  }, [
    classId,
    engineId,
    brand,
    fuel,
    drive,
    transmission,
    targetMileage,
    tireClass,
    rimDiameter,
    vehicleVintage,
    isMetalic,
    serviceCostType,
    replacementCar
  ]);

  return { paramPreview, controlCenter: null };
}
