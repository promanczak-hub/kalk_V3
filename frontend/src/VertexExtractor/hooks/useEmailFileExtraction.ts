import { useState, useCallback } from "react";
import { API_BASE_URL } from "../../config/env";
import { apiClient } from "../../lib/apiClient";
import type { CatalogCategory } from "../types";
import { applyExtractionResult, type ExtractionResponse, type ExtractionSuccessHandler } from "./useVertexExtraction";

export function useEmailFileExtraction(
  catalog: CatalogCategory[],
  onExtractionSuccess: ExtractionSuccessHandler,
  setExtractionText: (text: string) => void
) {
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractFromFile = useCallback(
    async (file: File) => {
      setExtracting(true);
      setError(null);

      const formData = new FormData();
      formData.append("email_file", file);

      try {
        const res = await apiClient.fetch(
          `${API_BASE_URL}/api/features/extract-email-file`,
          { method: "POST", body: formData }
        );

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data: ExtractionResponse & { email_subject?: string } = await res.json();

        if (data.email_subject) {
          setExtractionText(`Temat: ${data.email_subject}`);
        }

        const applied = applyExtractionResult(data, catalog, onExtractionSuccess);
        if (!applied) {
          setError("Nie znalazłem zapytania o samochód w tym mailu. Sprawdź treść i spróbuj ponownie.");
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Nieznany błąd";
        setError(`Nie udało się przetworzyć pliku: ${msg}`);
      } finally {
        setExtracting(false);
      }
    },
    [catalog, onExtractionSuccess, setExtractionText]
  );

  return { extracting, error, extractFromFile };
}
