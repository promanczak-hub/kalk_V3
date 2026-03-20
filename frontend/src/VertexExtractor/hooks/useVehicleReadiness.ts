import { useState, useEffect, useCallback } from "react";
import { apiClient } from '../../lib/apiClient';
import type { FleetVehicleView } from "../types";
import type { MappedData } from "../components/VehicleTableParts/VehicleBaseInfo";

export interface ReadinessCheck {
  param: string;
  status: string;
  value: string;
}

export interface ReadinessResult {
  overall_status: "ready" | "partial" | "not_ready";
  samar_class_id: number | null;
  fuel_type_id: number | null;
  checks: ReadinessCheck[];
  critical_count: number;
  warning_count: number;
  resolve_error?: string;
  body_match?: {
    matched_name: string | null;
    vehicle_class: string | null;
    score: number;
    match_method: string;
    raw_input: string;
  };
}

export function useVehicleReadiness(
  vehicle: FleetVehicleView,
  mappedData: MappedData | undefined,
  isMetalic: boolean
) {
  const [readinessResult, setReadinessResult] = useState<ReadinessResult | null>(null);

  const fetchReadiness = useCallback(async () => {
    const samarName = mappedData?.samar_category;
    const engineName = mappedData?.fuel;
    
    if (!samarName || !engineName) {
      setReadinessResult(null);
      return;
    }

    try {
      const params = new URLSearchParams({
        samar_class_name: samarName,
        engine_name: engineName,
        brand_name: vehicle.brand || "",
        vehicle_id: vehicle.id || "",
      });

      if (vehicle.body_style) {
        params.set("body_type_name", vehicle.body_style);
      }
      
      const paintTypeName = isMetalic ? "Metalizowany" : "Niemetalizowany";
      params.set("paint_type_name", paintTypeName);

      const res = await apiClient.fetch(`/api/readiness-check?${params}`);
      if (!res.ok) throw new Error("Readiness check failed");
      
      const data: ReadinessResult = await res.json();
      setReadinessResult(data);
    } catch (err) {
      console.error("Readiness check error:", err);
      setReadinessResult(null);
    }
  }, [mappedData?.samar_category, mappedData?.fuel, vehicle.brand, vehicle.body_style, vehicle.id, isMetalic]);

  useEffect(() => {
    fetchReadiness();
  }, [fetchReadiness]);

  return { readinessResult, fetchReadiness };
}


