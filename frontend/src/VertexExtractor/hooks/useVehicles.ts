import { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient } from '../../lib/apiClient';
import { supabase } from "../lib/supabaseClient";
import type { FleetVehicleView } from "../types";

export function useVehicles() {
  const [searchParams] = useSearchParams();
  const initialId = searchParams.get("highlight");

  const [savedVehicles, setSavedVehicles] = useState<FleetVehicleView[]>([]);
  const [isLoadingSaved, setIsLoadingSaved] = useState(true);
  const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [liveSearchText, setLiveSearchText] = useState("");
  const [activeEdit, setActiveEdit] = useState<{
    vehicleId: string;
    field: string;
  } | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalCount, setTotalCount] = useState(0);
  const [searchMatchingIds, setSearchMatchingIds] = useState<string[] | null>(
    initialId ? [initialId] : null
  );
  const [liveSearchMatchingIds, setLiveSearchMatchingIds] = useState<string[] | null>(null);

  useEffect(() => {
    if (!liveSearchText.trim()) {
      setLiveSearchMatchingIds(null);
      return;
    }
    const fetchMatching = async () => {
      const tokens = liveSearchText
        .trim()
        .split(/\s+/)
        .filter((t) => t.length > 0);
        
      if (tokens.length === 0) {
        setLiveSearchMatchingIds(null);
        return;
      }
      try {
        const { data, error } = await supabase.rpc("rpc_search_fleet_text", {
          search_terms: tokens,
        });
        if (error) throw error;
        setLiveSearchMatchingIds(data?.map((r: { id: string }) => r.id) || []);
      } catch (e) {
        console.error("Live search failed:", e);
      }
    };

    const timeoutId = setTimeout(() => {
      fetchMatching();
      setPage(1); // Reset page on new search
    }, 400);

    return () => clearTimeout(timeoutId);
  }, [liveSearchText]);

  useEffect(() => {
    if (initialId) {
      setSearchMatchingIds([initialId]);
      setPage(1);
    }
  }, [initialId]);

  const loadData = useCallback(async () => {
    setIsLoadingSaved(true);
    try {
      const from = (page - 1) * pageSize;
      const to = from + pageSize - 1;

      let q = supabase
        .from("fleet_management_view")
        .select("*", { count: "exact" })
        .order("created_at", { ascending: false })
        .range(from, to);

      if (searchMatchingIds !== null || liveSearchMatchingIds !== null) {
        let combined: string[] = [];
        if (searchMatchingIds !== null && liveSearchMatchingIds !== null) {
          combined = searchMatchingIds.filter((id) =>
            liveSearchMatchingIds.includes(id),
          );
        } else if (searchMatchingIds !== null) {
          combined = searchMatchingIds;
        } else {
          combined = liveSearchMatchingIds!;
        }

        if (combined.length === 0) {
          setSavedVehicles([]);
          setTotalCount(0);
          return;
        }
        q = q.in("id", combined);
      } else {
        // Hide library vehicles from the general list
        q = q.neq("verification_status", "moved_to_library");
      }

      const { data, count, error } = await q;

      if (error) throw error;
      setSavedVehicles(data || []);
      setTotalCount(count || 0);
    } catch (err) {
      console.error("Failed to fetch vehicles:", err);
    } finally {
      setIsLoadingSaved(false);
    }
  }, [page, pageSize, searchMatchingIds, liveSearchMatchingIds]);

  const fetchSavedVehicles = useCallback(() => {
    setGlobalSearchQuery("");
    setSearchMatchingIds(null);
    setLiveSearchText("");
    setLiveSearchMatchingIds(null);
    if (page === 1) {
      loadData();
    } else {
      setPage(1);
    }
  }, [page, loadData]);

  // Fetch a single vehicle from the view and merge it into state
  const fetchSingleVehicle = useCallback(
    async (vehicleId: string) => {
      try {
        const { data, error } = await supabase
          .from("fleet_management_view")
          .select("*")
          .eq("id", vehicleId)
          .single();

        if (error) throw error;
        if (!data) return;

        const isHighlighted = searchMatchingIds?.includes(vehicleId) || liveSearchMatchingIds?.includes(vehicleId);

        if (data.verification_status === "moved_to_library" && !isHighlighted) {
          setSavedVehicles((prev) => prev.filter((v) => v.id !== vehicleId));
          return;
        }

        setSavedVehicles((prev) => {
          const exists = prev.some((v) => v.id === vehicleId);
          if (exists) {
            return prev.map((v) => (v.id === vehicleId ? data : v));
          }
          return [data, ...prev]; // new vehicle at the top
        });
      } catch (err) {
        console.error("Failed to fetch single vehicle, falling back to full refetch:", err);
        fetchSavedVehicles();
      }
    },
    [fetchSavedVehicles, searchMatchingIds, liveSearchMatchingIds],
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const channel = supabase
      .channel("vehicle_synthesis_changes")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "vehicle_synthesis",
        },
        (payload) => {
          const eventType = payload.eventType;


          if (eventType === "DELETE") {
            // Remove locally — no need to refetch
            const oldId = (payload.old as { id?: string })?.id;
            if (oldId) {
              setSavedVehicles((prev) => prev.filter((v) => v.id !== oldId));
            }
          } else if (eventType === "UPDATE") {
            const newData = payload.new as {
              id: string;
              verification_status?: string;
              synthesis_data?: Record<string, unknown>; // Added synthesis_data to newData type for potential update
            };

            // For intermediate status updates, just patch the status inline
            // (avoids full view query for every progress tick)
            if (
              newData.verification_status &&
              newData.verification_status !== "completed" &&
              newData.verification_status !== "error" &&
              newData.verification_status !== "moved_to_library" &&
              newData.verification_status !== "needs_review"
            ) {
              setSavedVehicles((prev) =>
                prev.map((v) =>
                  v.id === newData.id
                    ? {
                        ...v,
                        verification_status: newData.verification_status!,
                        synthesis_data:
                          newData.synthesis_data || v.synthesis_data,
                      }
                    : v,
                ),
              );
            } else {
              // Status "completed", "error", "moved_to_library" or other field change — fetch full row from view
              fetchSingleVehicle(newData.id);
            }
          } else if (eventType === "INSERT") {
            // New row inserted — fetch full data from view
            const newId = (payload.new as { id?: string })?.id;
            if (newId) {
              fetchSingleVehicle(newId);
            }
          }
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchSavedVehicles, fetchSingleVehicle]);

  const handleUpdateNotes = async (vehicleId: string, newNotes: string) => {
    try {
      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ notes: newNotes })
        .eq("id", vehicleId);

      if (error) {
        throw error;
      }

      setSavedVehicles((prev) =>
        prev.map((v) => {
          if (v.id === vehicleId) {
            return {
              ...v,
              notes: newNotes,
            };
          }
          return v;
        }),
      );
    } catch (err) {
      console.error("Error updating notes:", err);
      alert("Wystąpił błąd podczas zapisywania komentarza.");
    }
  };

  const handleUpdateBadge = async (
    vehicleId: string,
    field: string,
    query: string,
  ) => {
    try {
      const response = await apiClient.fetch(`/api/query-vehicle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_id: vehicleId,
          field_to_update: field,
          query,
        }),
      });

      if (!response.ok) throw new Error("Failed to query vehicle");

      const resData = await response.json();
      const updatedValue = resData.value;

      if (updatedValue && updatedValue !== "Brak") {
        setSavedVehicles((prev) =>
          prev.map((v) => {
            if (v.id === vehicleId) {
              return {
                ...v,
                [field === "total_price" ? "final_price_pln" : field]:
                  updatedValue,
              };
            }
            return v;
          }),
        );
      }
    } catch (err) {
      console.error("Error updating badge via Gemini:", err);
      alert("Wystąpił błąd podczas komunikacji z AI.");
    }
  };

  const handleCloneVehicle = async (vehicleId: string) => {
    try {
      const response = await apiClient.fetch(`/api/clone-vehicle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vehicle_id: vehicleId }),
      });

      if (!response.ok) throw new Error("Failed to clone vehicle");

      // Refresh the list after cloning
      await fetchSavedVehicles();
    } catch (err) {
      console.error("Error cloning vehicle:", err);
      alert("Wystąpił błąd podczas klonowania oferty.");
    }
  };

  const handleDeleteVehicle = async (vehicleId: string) => {

    // Potwierdzenie jest już w VehicleActionButtons.tsx przed dispatchem CustomEvent.
    // Nie pokazuj drugiego confirm - wywołuj delete bezpośrednio.

    try {
      const response = await apiClient.fetch(`/api/delete-vehicle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vehicle_id: vehicleId }),
      });

      if (!response.ok) throw new Error("Failed to delete vehicle");

      // Update state immediately without refetching everything
      setSavedVehicles((prev) => prev.filter((v) => v.id !== vehicleId));
    } catch (err) {
      console.error("Error deleting vehicle:", err);
      alert("Wystąpił błąd podczas usuwania rekordu.");
    }
  };

  const handleGlobalSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!globalSearchQuery.trim()) {
      fetchSavedVehicles();
      return;
    }

    setIsSearching(true);
    try {
      const response = await apiClient.fetch(`/api/search-fleet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: globalSearchQuery }),
      });

      if (!response.ok) throw new Error("Failed to search fleet");

      const data = await response.json();
      setSearchMatchingIds(data.matching_ids || []);
      setPage(1); // jump to first page of search results
    } catch (err) {
      console.error("Search error via Gemini:", err);
      alert("Wystąpił błąd podczas wyszukiwania AI.");
    } finally {
      setIsSearching(false);
    }
  };

  return {
    savedVehicles,
    isLoadingSaved,
    globalSearchQuery,
    setGlobalSearchQuery,
    isSearching,
    liveSearchText,
    setLiveSearchText,
    activeEdit,
    setActiveEdit,
    fetchSavedVehicles,
    handleUpdateBadge,
    handleUpdateNotes,
    handleCloneVehicle,
    handleDeleteVehicle,
    handleGlobalSearch,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalCount,
  };
}
