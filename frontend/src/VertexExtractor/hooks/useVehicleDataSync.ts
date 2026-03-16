import { useState } from "react";
import { supabase } from "../../lib/supabaseClient";
import { apiFetch } from "../../lib/api";
import type { FleetVehicleView } from "../types";
import type { MappedData } from "../components/VehicleTableParts/VehicleBaseInfo";

export function useVehicleDataSync(
  vehicle: FleetVehicleView,
  onRefresh: () => void,
  setLocalMappedData: React.Dispatch<React.SetStateAction<MappedData | null>>
) {
  const [isSavingFields, setIsSavingFields] = useState(false);
  const [isRemappingClassification, setIsRemappingClassification] = useState(false);

  // Direct save: patch card_summary JSON + top-level columns
  const handleDirectSave = async (fields: Record<string, string>) => {
    setIsSavingFields(true);
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      if (!updatedJson.card_summary) updatedJson.card_summary = {};

      const cardSummaryKeys = new Set([
        "trim_level", "body_style", "vehicle_class", "powertrain",
        "fuel", "transmission", "wheels", "emissions", "exterior_color",
        "configuration_code", "number_of_seats", "power_hp", "power_kw"
      ]);

      const columnUpdates: Record<string, unknown> = {};

      const normalizedFields: Record<string, string> = { ...fields };
      const rawBodyStyle = (normalizedFields.body_style || "").trim();
      if (rawBodyStyle) {
        try {
          const resp = await apiFetch(`/api/match-body-type?body_style_raw=${encodeURIComponent(rawBodyStyle)}`);
          if (resp.ok) {
            const match = await resp.json();
            if (match?.matched_name) {
              normalizedFields.body_style = match.matched_name;
            } else {
              console.warn("Body type not found in dictionary, keeping manual value:", rawBodyStyle);
            }
          }
        } catch (matchErr) {
          console.warn("Body type normalization failed, keeping manual value:", matchErr);
        }
      }
      for (const [key, value] of Object.entries(normalizedFields)) {
        if (cardSummaryKeys.has(key)) {
          updatedJson.card_summary[key] = value;
        }
        if (key === "brand" || key === "model" || key === "offer_number") {
          columnUpdates[key] = value;
        }
        if (key === "configuration_code") {
          updatedJson.configuration_code = value;
        }
      }

      columnUpdates.synthesis_data = updatedJson;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update(columnUpdates)
        .eq("id", vehicle.id);

      if (error) throw error;
      onRefresh();
    } catch (err) {
      console.error("Error saving vehicle fields", err);
      alert("Błąd zapisu: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    } finally {
      setIsSavingFields(false);
    }
  };

  // Re-run Flash classification (SAMAR, engine, service class)
  const handleRemapClassification = async () => {
    if (!vehicle.synthesis_data) return;
    setIsRemappingClassification(true);
    try {
      const response = await apiFetch(`/api/extract/remap-classification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ original_json: vehicle.synthesis_data }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Błąd klasyfikacji HTTP ${response.status}: ${errText}`);
      }
      
      const data = await response.json();

      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      updatedJson.mapped_ai_data = data;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData(data);
      onRefresh();
    } catch (err) {
      console.error("Remap classification error details:", err);
      alert("Błąd przeliczania klasyfikacji: " + (err instanceof Error ? err.message : JSON.stringify(err)));
    } finally {
      setIsRemappingClassification(false);
    }
  };

  return {
    isSavingFields,
    handleDirectSave,
    isRemappingClassification,
    handleRemapClassification
  };
}

