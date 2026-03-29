import { useState, useEffect } from "react";
import { API_BASE_URL } from "../../config/env";
import { apiClient } from "../../lib/apiClient";

export interface SamarClassRef {
  id: number;
  name: string;
  category?: string;
  size_class?: string;
  example_models?: string;
}

export interface EngineTypeRef {
  id: number;
  name: string;
  category: string;
  description?: string;
}

export interface BodyTypeRef {
  id: number;
  name: string;
  vehicle_class: string;
  description?: string;
}

interface ReferenceData {
  samarClasses: SamarClassRef[];
  engineTypes: EngineTypeRef[];
  bodyTypes: BodyTypeRef[];
  loading: boolean;
  error: string | null;
}

let cachedSamar: SamarClassRef[] | null = null;
let cachedEngines: EngineTypeRef[] | null = null;
let cachedBodyTypes: BodyTypeRef[] | null = null;

export function useReferenceData(): ReferenceData {
  const [samarClasses, setSamarClasses] = useState<SamarClassRef[]>(cachedSamar ?? []);
  const [engineTypes, setEngineTypes] = useState<EngineTypeRef[]>(cachedEngines ?? []);
  const [bodyTypes, setBodyTypes] = useState<BodyTypeRef[]>(cachedBodyTypes ?? []);
  const [loading, setLoading] = useState(!cachedSamar || !cachedEngines || !cachedBodyTypes);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cachedSamar && cachedEngines && cachedBodyTypes) return;

    let cancelled = false;

    const fetchAll = async () => {
      try {
        const [samarRes, enginesRes, bodyTypesRes] = await Promise.all([
          apiClient.fetch(`${API_BASE_URL}/api/samar-classes`),
          apiClient.fetch(`${API_BASE_URL}/api/engines`),
          apiClient.fetch(`${API_BASE_URL}/api/body-types`),
        ]);

        if (cancelled) return;

        if (samarRes.ok) {
          const data = await samarRes.json();
          cachedSamar = Array.isArray(data) ? data : [];
          setSamarClasses(cachedSamar);
        }
        if (enginesRes.ok) {
          const data = await enginesRes.json();
          cachedEngines = Array.isArray(data) ? data : [];
          setEngineTypes(cachedEngines);
        }
        if (bodyTypesRes.ok) {
          const data = await bodyTypesRes.json();
          // Map backend fields (nazwa_nadwozia, typ_pojazdu) to frontend fields (name, vehicle_class)
          cachedBodyTypes = Array.isArray(data) ? data.map((item: { id: number; nazwa_nadwozia?: string; name?: string; typ_pojazdu?: string; vehicle_class?: string; description?: string }) => ({
            id: item.id,
            name: item.nazwa_nadwozia || item.name || "",
            vehicle_class: item.typ_pojazdu || item.vehicle_class || "",
            description: item.description
          })) : [];
          setBodyTypes(cachedBodyTypes);
        }
      } catch (fetchError) {
        if (!cancelled) {
          const message = fetchError instanceof Error ? fetchError.message : "Błąd ładowania danych referencyjnych";
          setError(message);
          console.error("useReferenceData fetch error:", fetchError);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchAll();
    return () => { cancelled = true; };
  }, []);

  return { samarClasses, engineTypes, bodyTypes, loading, error };
}
