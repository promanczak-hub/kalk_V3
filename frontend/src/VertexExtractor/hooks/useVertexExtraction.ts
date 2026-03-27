import { useState } from "react";
import { API_BASE_URL } from "../../config/env";
import type { CatalogCategory, SearchFilter } from "../types";
import { apiClient } from "../../lib/apiClient";

export function useVertexExtraction(
  catalog: CatalogCategory[],
  onExtractionSuccess: (
    extractedFilters: SearchFilter[], 
    newExpandedCats: Set<string>,
    financials?: { price_max?: number | null; duration_months?: number | null; annual_mileage?: number | null }
  ) => void
) {
  const [extractionText, setExtractionText] = useState("");
  const [extracting, setExtracting] = useState(false);

  const handleExtraction = async () => {
    if (!extractionText.trim()) return;
    setExtracting(true);
    try {
      const res = await apiClient.fetch(`${API_BASE_URL}/api/features/extract-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query_text: extractionText })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      
      if (data.status === "success" && data.extracted_filters) {
         const newExpanded = new Set<string>();
         data.extracted_filters.forEach((f: { feature_key: string }) => {
             const cat = catalog.find(c => c.features.some((cf: any) => cf.feature_key === f.feature_key));
             if (cat) newExpanded.add(cat.id);
         });

         const mappedFilters = data.extracted_filters.map((f: { feature_key: string; value_bool?: boolean }) => ({
            feature_key: f.feature_key,
            display_name: catalog.flatMap(c => c.features).find(cf => cf.feature_key === f.feature_key)?.display_name || f.feature_key,
            value_bool: f.value_bool
         }));

         onExtractionSuccess(mappedFilters, newExpanded, data.extracted_financials);
      }
    } catch (err) {
      console.error("Extraction failed:", err);
      // eslint-disable-next-line no-alert
      alert("Nie udało się przeanalizować zapytania. Spróbuj ponownie.");
    } finally {
      setExtracting(false);
    }
  };

  return {
    extractionText,
    setExtractionText,
    extracting,
    handleExtraction
  };
}
