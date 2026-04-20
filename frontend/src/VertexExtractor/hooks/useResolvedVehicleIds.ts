import { useState, useEffect } from "react";
import { apiClient } from "../../lib/apiClient";

interface ResolvedIds {
  samar_class_id: number | null;
  fuel_type_id: number | null;
}

/**
 * Lightweight hook that resolves SAMAR class name and engine name to numeric DB IDs.
 * Replaces the heavy useVehicleReadiness hook.
 */
export function useResolvedVehicleIds(
  samarCategoryName: string | undefined,
  engineName: string | undefined
): ResolvedIds | null {
  const [resolved, setResolved] = useState<ResolvedIds | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    if (!samarCategoryName || !engineName) {
      setResolved(null);
      return;
    }

    const jitterDelay = Math.floor(Math.random() * 500) + 100;
    const timeoutId = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          samar_class_name: samarCategoryName,
          engine_name: engineName,
        });

        const data = await apiClient.get<ResolvedIds>(
          `/api/resolve-vehicle-ids?${params}`,
          { signal: controller.signal }
        );
        setResolved(data);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        console.error("Failed to resolve vehicle IDs:", err);
        setResolved(null);
      }
    }, jitterDelay);

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [samarCategoryName, engineName]);

  return resolved;
}
