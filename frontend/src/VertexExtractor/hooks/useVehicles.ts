import { useState, useCallback, useEffect } from "react";
import { supabase } from "../lib/supabaseClient";
import type { FleetVehicleView } from "../types";

export function useVehicles() {
  const [savedVehicles, setSavedVehicles] = useState<FleetVehicleView[]>([]);
  const [isLoadingSaved, setIsLoadingSaved] = useState(true);
  const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [activeEdit, setActiveEdit] = useState<{
    vehicleId: string;
    field: string;
  } | null>(null);

  const fetchSavedVehicles = useCallback(async () => {
    setIsLoadingSaved(true);
    try {
      const { data, error } = await supabase
        .from("fleet_management_view")
        .select("*")
        .order("created_at", { ascending: false });

      if (error) throw error;
      setSavedVehicles(data || []);
      setGlobalSearchQuery(""); // reset search state when fetching all
    } catch (err) {
      console.error("Failed to fetch saved vehicles:", err);
    } finally {
      setIsLoadingSaved(false);
    }
  }, []);

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
    [fetchSavedVehicles],
  );

  useEffect(() => {
    fetchSavedVehicles();

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
          console.log(`[Realtime] ${eventType} on vehicle_synthesis`, payload);

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
            };

            // For intermediate status updates, just patch the status inline
            // (avoids full view query for every progress tick)
            if (
              newData.verification_status &&
              newData.verification_status !== "completed" &&
              newData.verification_status !== "error"
            ) {
              setSavedVehicles((prev) =>
                prev.map((v) =>
                  v.id === newData.id
                    ? {
                        ...v,
                        verification_status: newData.verification_status!,
                      }
                    : v,
                ),
              );
            } else {
              // Status "completed" or other field change — fetch full row from view
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
      const response = await fetch("http://127.0.0.1:8000/api/query-vehicle", {
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
      const response = await fetch("http://127.0.0.1:8000/api/clone-vehicle", {
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
    console.log("handleDeleteVehicle called with", vehicleId);
    const confirmed = window.confirm(
      "Czy na pewno chcesz usunąć ten rekord? Tej operacji nie można cofnąć.",
    );
    console.log("window.confirm result:", confirmed);
    if (!confirmed) {
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/api/delete-vehicle", {
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
      const response = await fetch("http://127.0.0.1:8000/api/search-fleet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: globalSearchQuery }),
      });

      if (!response.ok) throw new Error("Failed to search fleet");

      const data = await response.json();
      const ids = data.matching_ids || [];

      if (ids.length === 0) {
        setSavedVehicles([]);
      } else {
        const { data: searchData, error } = await supabase
          .from("fleet_management_view")
          .select("*")
          .in("id", ids)
          .order("created_at", { ascending: false });

        if (error) throw error;
        setSavedVehicles(searchData || []);
      }
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
    activeEdit,
    setActiveEdit,
    fetchSavedVehicles,
    handleUpdateBadge,
    handleUpdateNotes,
    handleCloneVehicle,
    handleDeleteVehicle,
    handleGlobalSearch,
  };
}
