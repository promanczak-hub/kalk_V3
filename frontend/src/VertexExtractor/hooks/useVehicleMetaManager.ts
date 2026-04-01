import { useState } from "react";
import { supabase } from "../../lib/supabaseClient";
import { apiClient } from '../../lib/apiClient';
import type { FleetVehicleView } from "../types";
import type { MappedData } from "../components/VehicleTableParts/VehicleBaseInfo";

export function useVehicleMetaManager(
  vehicle: FleetVehicleView,
  serverMappedData: MappedData | undefined,
     
    _localMappedData: MappedData | null,
  setLocalMappedData: React.Dispatch<React.SetStateAction<MappedData | null>>
) {
  const [isMapping, setIsMapping] = useState(false);

  // Trigger Celery background task to rebuild matrix cache (0% margin) after semantic changes
  const triggerMatrixCacheRefresh = () => {
    apiClient.fetch(`/api/kalkulacje/matrix-cache/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vehicle_ids: [vehicle.id] }),
    }).catch(err => console.error("Matrix cache refresh failed:", err));
  };

  const handleSamarCategoryChange = async (newCategory: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.samar_category = newCategory;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      // Update local state so UI reflects immediately
      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        samar_category: newCategory,
      }));

      triggerMatrixCacheRefresh();
    } catch (err) {
      console.error("Error updating SAMAR category", err);
      alert("Błąd zapisu kategorii SAMAR: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleEngineCategoryChange = async (newCategory: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.fuel = newCategory;

      // Optimistically fetch category for immediate UI update
      const enginesResp = await supabase.from('engines').select('category').eq('name', newCategory);
      const newCategoryClass = enginesResp.data?.[0]?.category;
      if (newCategoryClass) {
         updatedJson.mapped_ai_data.engine_class = newCategoryClass;
      }

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      // Update local state so UI reflects immediately
      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        fuel: newCategory,
        engine_class: newCategoryClass || prev?.engine_class || serverMappedData?.engine_class,
      }));

      triggerMatrixCacheRefresh();
    } catch (err) {
      console.error("Error updating Engine category", err);
      alert("Błąd zapisu kategorii Silnika: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleDriveTypeChange = async (newDriveType: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.drive_type = newDriveType;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        drive_type: newDriveType,
      }));

      triggerMatrixCacheRefresh();
    } catch (err) {
      console.error("Error updating drive type", err);
      alert("Błąd zapisu napędu: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleBodyTypeChange = async (newBodyType: string) => {
    const rawCandidate = (newBodyType || "").trim();
    if (!rawCandidate) return;

    try {
      let canonicalBodyType = rawCandidate;

      const matchResp = await apiClient.fetch(`/api/match-body-type?body_style_raw=${encodeURIComponent(rawCandidate)}`);
      if (matchResp.ok) {
        const match = await matchResp.json();
        if (match?.matched_name) {
          canonicalBodyType = match.matched_name;
        } else {
          console.warn("Body type not found in dictionary, keeping manual value:", rawCandidate);
        }
      }

      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.body_type = canonicalBodyType;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        body_type: canonicalBodyType,
      }));

      triggerMatrixCacheRefresh();
    } catch (err) {
      console.error("Error updating body type", err);
      alert("Błąd zapisu nadwozia: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleConfigurationCodeChange = async (newCode: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.configuration_code = newCode;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        configuration_code: newCode,
      }));

      // No need for matrix refresh on config code change (usually)
    } catch (err) {
      console.error("Error updating configuration code", err);
      alert("Błąd zapisu kodu konfiguracji: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handlePaintCategoryIdChange = async (newId: number) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.paint_category_id = newId;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        paint_category_id: newId,
      }));

      triggerMatrixCacheRefresh();
    } catch (err) {
      console.error("Error updating paint category", err);
    }
  };

  const handleVehicleTypeChange = async (newType: string) => {
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));

      if (!updatedJson.mapped_ai_data) updatedJson.mapped_ai_data = {};
      updatedJson.mapped_ai_data.vehicle_type = newType;

      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;

      setLocalMappedData((prev) => ({
        ...(prev || serverMappedData || { brand: "", model: "", fuel: "", vehicle_type: "", trim_level: "", transmission: "" }),
        vehicle_type: newType,
      }));

      triggerMatrixCacheRefresh();
    } catch (err) {
      console.error("Error updating vehicle type", err);
      alert("Błąd zapisu kategorii: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    }
  };

  const handleMapDataSilent = async () => {
    if (!vehicle.synthesis_data) return;
    setIsMapping(true);
    try {
      const response = await apiClient.fetch(`/api/extract/map-vehicle-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_json: vehicle.synthesis_data,
        }),
      });

      if (!response.ok) {
        throw new Error("Błąd podczas wywołania API mapowania danych.");
      }

      const data = await response.json();
      setLocalMappedData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsMapping(false);
    }
  };

  return {
    isMapping,
    handleSamarCategoryChange,
    handleEngineCategoryChange,
    handleDriveTypeChange,
    handleBodyTypeChange,
    handleConfigurationCodeChange,
    handlePaintCategoryIdChange,
    handleVehicleTypeChange,
    handleMapDataSilent,
  };


}
