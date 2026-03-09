import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  GitMerge,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileText,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

interface CatalogItem {
  id: string;
  brand: string;
  model_family: string;
  document_type: string;
  display_name: string;
  extraction_status: string;
  variant_count: number;
}

interface CrossRefResult {
  status: string;
  matched_variant?: string;
  confidence?: number;
  reasoning?: string;
  evidence_created?: number;
  body_params_created?: number;
  features_extracted?: number;
  error?: string;
}

interface CatalogCrossRefPanelProps {
  vehicleId: string;
  vehicleBrand?: string;
  vehicleModel?: string;
  onFeaturesChanged?: () => void;
}

export function CatalogCrossRefPanel({
  vehicleId,
  vehicleBrand,
  vehicleModel,
  onFeaturesChanged,
}: CatalogCrossRefPanelProps) {
  const [catalogs, setCatalogs] = useState<CatalogItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [crossRefLoading, setCrossRefLoading] = useState(false);
  const [wipeLoading, setWipeLoading] = useState(false);
  const [result, setResult] = useState<CrossRefResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch catalogs matching this vehicle's brand/model
  const fetchCatalogs = useCallback(async () => {
    setLoading(true);
    try {
      let url = `${API}/api/catalogs?`;
      if (vehicleBrand) url += `brand=${encodeURIComponent(vehicleBrand)}&`;
      if (vehicleModel) url += `model_family=${encodeURIComponent(vehicleModel)}&`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Only show catalogs with extracted variants
      const ready = (data as CatalogItem[]).filter(
        (c) => c.extraction_status === "ready" && c.variant_count > 0
      );
      setCatalogs(ready);
    } catch (err) {
      console.error("Catalog fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [vehicleBrand, vehicleModel]);

  useEffect(() => {
    fetchCatalogs();
  }, [fetchCatalogs]);

  const toggleCatalog = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Cross-reference with selected catalogs
  const handleCrossRef = async () => {
    if (selectedIds.size === 0) return;
    setCrossRefLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await fetch(
        `${API}/api/features/vehicle/${vehicleId}/cross-reference`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ catalog_ids: Array.from(selectedIds) }),
        }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: CrossRefResult = await res.json();
      setResult(data);
      if (data.status === "matched" && onFeaturesChanged) {
        onFeaturesChanged();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd cross-reference");
    } finally {
      setCrossRefLoading(false);
    }
  };

  // Wipe all features
  const handleWipe = async () => {
    if (!confirm("Na pewno chcesz usunąć wszystkie cechy tego pojazdu? Będziesz mógł je zbudować od nowa.")) {
      return;
    }
    setWipeLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await fetch(
        `${API}/api/features/vehicle/${vehicleId}/evidence`,
        { method: "DELETE" }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult({
        status: "wiped",
        evidence_created: 0,
        features_extracted: data.evidence_deleted || 0,
      });
      if (onFeaturesChanged) onFeaturesChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd wymazywania");
    } finally {
      setWipeLoading(false);
    }
  };

  // Also do enrichment from spec
  const handleEnrichFromSpec = async () => {
    setCrossRefLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await fetch(
        `${API}/api/features/vehicle/${vehicleId}/enrich`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult({
        status: "enriched",
        evidence_created: data.evidence_created || 0,
        features_extracted: data.evidence_created || 0,
      });
      if (onFeaturesChanged) onFeaturesChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd enrichmentu");
    } finally {
      setCrossRefLoading(false);
    }
  };

  return (
    <div className="border border-slate-200 rounded bg-white mt-3">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-2">
          <GitMerge className="w-3.5 h-3.5" />
          Cross-reference z katalogami
        </h4>
        <div className="flex gap-2">
          <button
            onClick={handleEnrichFromSpec}
            disabled={crossRefLoading}
            className="text-[10px] px-2.5 py-1 bg-sky-50 text-sky-700 border border-sky-200 rounded hover:bg-sky-100 transition-colors disabled:opacity-50"
            title="Enrichment z konfiguracji (card_summary)"
          >
            📋 Z konfiguracji
          </button>
          <button
            onClick={handleWipe}
            disabled={wipeLoading}
            className="text-[10px] px-2.5 py-1 bg-red-50 text-red-600 border border-red-200 rounded hover:bg-red-100 transition-colors disabled:opacity-50 flex items-center gap-1"
          >
            {wipeLoading ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Trash2 className="w-3 h-3" />
            )}
            Wyczyść cechy
          </button>
        </div>
      </div>

      {/* Catalog list */}
      <div className="p-4">
        {loading && (
          <div className="flex items-center justify-center py-4 text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            <span className="text-xs">Ładowanie katalogów...</span>
          </div>
        )}

        {!loading && catalogs.length === 0 && (
          <div className="text-xs text-slate-400 py-3 text-center">
            Brak gotowych katalogów{vehicleBrand ? ` dla ${vehicleBrand}` : ""}.
            Wgraj katalog w zakładce &quot;Biblioteka Cenników&quot;.
          </div>
        )}

        {!loading && catalogs.length > 0 && (
          <>
            <div className="text-xs text-slate-500 mb-2">
              Wybierz katalogi do cross-reference:
            </div>
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {catalogs.map((cat) => (
                <label
                  key={cat.id}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded border text-xs cursor-pointer transition-colors ${
                    selectedIds.has(cat.id)
                      ? "bg-indigo-50 border-indigo-300 text-indigo-800"
                      : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(cat.id)}
                    onChange={() => toggleCatalog(cat.id)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="font-medium">{cat.display_name}</span>
                  <span className="text-[10px] text-slate-400 ml-auto">
                    {cat.document_type} · {cat.variant_count} wariantów
                  </span>
                </label>
              ))}
            </div>

            {/* Action button */}
            <button
              onClick={handleCrossRef}
              disabled={selectedIds.size === 0 || crossRefLoading}
              className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-xs font-medium rounded hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {crossRefLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Dopasowywanie wariantu...
                </>
              ) : (
                <>
                  <GitMerge className="w-4 h-4" />
                  Uruchom cross-reference ({selectedIds.size} katalogów)
                </>
              )}
            </button>
          </>
        )}

        {/* Result display */}
        {result && (
          <div
            className={`mt-3 p-3 rounded border text-xs ${
              result.status === "matched"
                ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                : result.status === "wiped"
                ? "bg-amber-50 border-amber-200 text-amber-800"
                : result.status === "enriched"
                ? "bg-sky-50 border-sky-200 text-sky-800"
                : "bg-slate-50 border-slate-200 text-slate-600"
            }`}
          >
            {result.status === "matched" && (
              <>
                <div className="flex items-center gap-1.5 font-semibold mb-1">
                  <CheckCircle2 className="w-4 h-4" />
                  Dopasowano: {result.matched_variant}
                </div>
                <div className="text-[11px] space-y-0.5">
                  <div>Pewność: {Math.round((result.confidence || 0) * 100)}%</div>
                  <div>Cechy wyekstrahowane: {result.features_extracted}</div>
                  <div>Evidence: {result.evidence_created} · Body params: {result.body_params_created}</div>
                  {result.reasoning && (
                    <div className="mt-1 italic opacity-80">{result.reasoning}</div>
                  )}
                </div>
              </>
            )}
            {result.status === "wiped" && (
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" />
                Wyczyszczono {result.features_extracted} rekordów evidence. Możesz teraz zbudować cechy od nowa.
              </div>
            )}
            {result.status === "enriched" && (
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                Enrichment z konfiguracji: {result.evidence_created} evidence records.
              </div>
            )}
            {result.status === "no_match" && (
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" />
                {result.error || "Nie znaleziono pasującego wariantu w katalogach."}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-3 p-3 rounded border bg-red-50 border-red-200 text-red-700 text-xs">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
