import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../lib/apiClient";
import { API_BASE_URL } from "../config/env";

export interface MileageAdjustment {
  id: string; // uuid
  samar_class_id: number;
  max_mileage_target: number;
  correction_below_threshold: number;
  correction_above_threshold: number;
  samar_class_name?: string | null;
}

export function useMileageAdjustments() {
  const [data, setData] = useState<MileageAdjustment[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchMileageAdjustments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await apiClient.fetch(`${API_BASE_URL}/api/mileage-adjustments`);
      if (!resp.ok) {
        throw new Error("Failed to fetch mileage adjustments");
      }
      const json = await resp.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMileageAdjustments();
  }, [fetchMileageAdjustments]);

  const updateAdjustment = async (payload: { id: string; update: Omit<MileageAdjustment, 'id' | 'samar_class_id' | 'samar_class_name'> }) => {
    const resp = await apiClient.fetch(`${API_BASE_URL}/api/mileage-adjustments/${payload.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload.update),
    });
    if (!resp.ok) {
      throw new Error("Failed to update adjustment");
    }
    // Refresh data after update
    await fetchMileageAdjustments();
    return await resp.json();
  };

  return {
    data,
    isLoading,
    error,
    updateAdjustment,
    refresh: fetchMileageAdjustments
  };
}
