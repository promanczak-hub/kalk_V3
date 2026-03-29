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
  isMetalic: boolean,
  currentBodyType?: string
) {
  const [readinessResult, setReadinessResult] = useState<ReadinessResult | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    
    const fetchReadiness = async () => {
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

        if (currentBodyType) {
          params.set("body_type_name", currentBodyType);
        }
        
        const paintTypeName = isMetalic ? "Metalizowany" : "Niemetalizowany";
        params.set("paint_type_name", paintTypeName);

        // Extract zabudowa_type_id if present (useful for Monolith 5)
        interface SynthData {
          calculator_setup?: { zabudowa_type_id?: number };
          card_summary?: { zabudowa_type_id?: number };
        }
        const synthData = vehicle.synthesis_data as unknown as SynthData | undefined;
        if (synthData) {
          const zabudowaId = synthData.calculator_setup?.zabudowa_type_id 
            ?? synthData.card_summary?.zabudowa_type_id;
          if (typeof zabudowaId === "number") {
            params.set("zabudowa_type_id", zabudowaId.toString());
          }
        }

        const res = await apiClient.fetch(`/api/readiness-check?${params}`, {
          signal: controller.signal,
          skipGlobalError: true
        });
        
        if (!res.ok) throw new Error("Readiness check failed");
        
        const data: ReadinessResult = await res.json();
        setReadinessResult(data);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        console.error("Readiness check error:", err);
        setReadinessResult(null);
      }
    };

    // Add a random jitter (100ms - 800ms) to stagger requests when 40+ vehicles load at once
    const jitterDelay = Math.floor(Math.random() * 700) + 100;
    const timeoutId = setTimeout(() => {
      fetchReadiness();
    }, jitterDelay);

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [
    mappedData?.samar_category,
    mappedData?.fuel,
    vehicle.brand,
    currentBodyType,
    vehicle.id,
    vehicle.synthesis_data,
    isMetalic,
  ]);

  // We provide a manual fetchReadiness callback so we don't break the component interface
  const fetchReadiness = useCallback(() => { 
    // Usually won't be called directly since useEffect handles it, but kept for compatibility
  }, []);

  return { readinessResult, fetchReadiness };
}



