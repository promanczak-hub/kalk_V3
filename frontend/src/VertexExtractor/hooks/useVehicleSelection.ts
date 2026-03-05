import { useState, useCallback } from "react";
import type { FleetVehicleView } from "../types";

export function useVehicleSelection(vehicles: FleetVehicleView[]) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(
    (ids: string[]) => {
      setSelectedIds((prev) => {
        const allVisible = new Set(ids);
        const allSelected = ids.every((id) => prev.has(id));
        if (allSelected) {
          // Deselect all visible
          const next = new Set(prev);
          for (const id of ids) next.delete(id);
          return next;
        }
        // Select all visible
        return new Set([...prev, ...allVisible]);
      });
    },
    [],
  );

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback(
    (id: string) => selectedIds.has(id),
    [selectedIds],
  );

  const getSelectedVehicles = useCallback((): FleetVehicleView[] => {
    return vehicles.filter((v) => selectedIds.has(v.id));
  }, [vehicles, selectedIds]);

  const selectedCount = selectedIds.size;

  return {
    selectedIds,
    selectedCount,
    toggleSelect,
    selectAll,
    deselectAll,
    isSelected,
    getSelectedVehicles,
  };
}
