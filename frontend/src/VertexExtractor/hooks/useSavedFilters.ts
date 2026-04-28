import { useCallback, useEffect, useState } from "react";
import { API_BASE_URL } from "../../config/env";
import { apiClient } from "../../lib/apiClient";
import type { SearchFilter } from "../types";

export type ReverseSearchFilterState = {
  globalSearchQuery?: string;
  activeFilters?: SearchFilter[];
  bodyTypes?: string[];
  vehicleScope?: "all" | "passenger" | "commercial";
  priceMin?: number | "";
  priceMax?: number | "";
  priceMonths?: number;
  priceMileage?: number;
  priceDepositPct?: number;
  priceMarginPct?: number | "";
};

export type SavedFilter = {
  id: string;
  user_email: string | null;
  name: string;
  description: string | null;
  filter_state: ReverseSearchFilterState;
  created_at: string;
  updated_at: string;
};

export function useSavedFilters(userEmail?: string | null) {
  const [items, setItems] = useState<SavedFilter[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = new URL(`${API_BASE_URL}/api/reverse-search/saved-filters`);
      if (userEmail) url.searchParams.set("user_email", userEmail);
      const res = await apiClient.fetch(url.toString(), { skipGlobalError: true });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load saved filters:", err);
      setError(err instanceof Error ? err.message : "Nieznany błąd");
    } finally {
      setLoading(false);
    }
  }, [userEmail]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const save = useCallback(
    async (
      name: string,
      filterState: ReverseSearchFilterState,
      description?: string
    ): Promise<SavedFilter | null> => {
      const trimmed = name.trim();
      if (!trimmed) {
        setError("Nazwa nie może być pusta.");
        return null;
      }
      try {
        const res = await apiClient.fetch(
          `${API_BASE_URL}/api/reverse-search/saved-filters`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: trimmed,
              description: description || null,
              filter_state: filterState,
              user_email: userEmail || null,
            }),
            skipGlobalError: true,
          }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const item: SavedFilter = await res.json();
        await refresh();
        return item;
      } catch (err) {
        console.error("Failed to save filter:", err);
        setError(err instanceof Error ? err.message : "Nie udało się zapisać.");
        return null;
      }
    },
    [userEmail, refresh]
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        const res = await apiClient.fetch(
          `${API_BASE_URL}/api/reverse-search/saved-filters/${id}`,
          { method: "DELETE", skipGlobalError: true }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setItems((prev) => prev.filter((f) => f.id !== id));
        return true;
      } catch (err) {
        console.error("Failed to delete saved filter:", err);
        setError(err instanceof Error ? err.message : "Nie udało się usunąć.");
        return false;
      }
    },
    []
  );

  return { items, loading, error, refresh, save, remove };
}
