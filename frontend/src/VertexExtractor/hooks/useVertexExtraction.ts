import { useState } from "react";
import { API_BASE_URL } from "../../config/env";
import type { CatalogCategory, SearchFilter } from "../types";
import { apiClient } from "../../lib/apiClient";

export type ExtractionFinancials = {
  price_max?: number | null;
  duration_months?: number | null;
  annual_mileage?: number | null;
};

export type ExtractedFeatureItem = {
  feature_key: string;
  feature_type?: "boolean" | "numeric" | "text" | "enum";
  op?: "eq" | "gte" | "lte" | "in";
  value_bool?: boolean | null;
  value_num?: number | null;
  value_text?: string | null;
  display_name?: string;
  canonical_unit?: string | null;
};

export type ExtractionResponse = {
  status?: string;
  extracted_features?: ExtractedFeatureItem[];
  extracted_filters?: { feature_key: string; value_bool?: boolean }[];
  extracted_financials?: ExtractionFinancials;
  transcript?: string | null;
  rejected_count?: number;
};

export type ExtractionSuccessHandler = (
  extractedFilters: SearchFilter[],
  newExpandedCats: Set<string>,
  financials?: ExtractionFinancials
) => void;

function lookupDisplayName(feature_key: string, catalog: CatalogCategory[]): string {
  return (
    catalog.flatMap((c) => c.features).find((cf) => cf.feature_key === feature_key)
      ?.display_name || feature_key
  );
}

function mapFeatureToFilter(
  feat: ExtractedFeatureItem,
  catalog: CatalogCategory[]
): SearchFilter | null {
  const display_name = feat.display_name || lookupDisplayName(feat.feature_key, catalog);
  const ftype = feat.feature_type;

  if (ftype === "boolean" || (!ftype && feat.value_bool !== undefined && feat.value_bool !== null)) {
    if (feat.value_bool !== true) return null;
    return { feature_key: feat.feature_key, display_name, value_bool: true };
  }

  if (ftype === "numeric") {
    if (feat.value_num === undefined || feat.value_num === null) return null;
    const op = feat.op || "eq";
    if (op === "gte") {
      return { feature_key: feat.feature_key, display_name, value_num_min: feat.value_num };
    }
    if (op === "lte") {
      return { feature_key: feat.feature_key, display_name, value_num_max: feat.value_num };
    }
    return {
      feature_key: feat.feature_key,
      display_name,
      value_num_min: feat.value_num,
      value_num_max: feat.value_num,
    };
  }

  if (ftype === "text" || ftype === "enum") {
    if (!feat.value_text) return null;
    return { feature_key: feat.feature_key, display_name, value_text: feat.value_text };
  }

  return null;
}

export function applyExtractionResult(
  data: ExtractionResponse,
  catalog: CatalogCategory[],
  onExtractionSuccess: ExtractionSuccessHandler
): boolean {
  if (data.status !== "success") return false;

  const features: ExtractedFeatureItem[] =
    data.extracted_features && data.extracted_features.length > 0
      ? data.extracted_features
      : (data.extracted_filters || []).map((f) => ({
          feature_key: f.feature_key,
          feature_type: "boolean" as const,
          op: "eq" as const,
          value_bool: f.value_bool ?? true,
        }));

  if (features.length === 0 && !data.extracted_financials) return false;

  const newExpanded = new Set<string>();
  features.forEach((f) => {
    const cat = catalog.find((c) => c.features.some((cf) => cf.feature_key === f.feature_key));
    if (cat) newExpanded.add(cat.id);
  });

  const mappedFilters: SearchFilter[] = features
    .map((f) => mapFeatureToFilter(f, catalog))
    .filter((f): f is SearchFilter => f !== null);

  onExtractionSuccess(mappedFilters, newExpanded, data.extracted_financials);
  return true;
}

export function useVertexExtraction(
  catalog: CatalogCategory[],
  onExtractionSuccess: ExtractionSuccessHandler
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
      const data: ExtractionResponse = await res.json();
      applyExtractionResult(data, catalog, onExtractionSuccess);
    } catch (err) {
      console.error("Extraction failed:", err);
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
