import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  GitMerge,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Plus,
  X,
  Star
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";

interface CatalogItem {
  id: string;
  brand: string;
  model_family: string;
  document_type: string;
  display_name: string;
  extraction_status: string;
  variant_count: number;
  _ranking?: { score: number; reasoning: string };
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

  // Suggest Modal State
  const [showSuggestModal, setShowSuggestModal] = useState(false);
  const [suggestedCatalogs, setSuggestedCatalogs] = useState<CatalogItem[]>([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [modalSelectedIds, setModalSelectedIds] = useState<Set<string>>(new Set());

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

  // Open Suggest Modal and fetch /api/catalogs/suggest
  const handleOpenSuggestModal = async () => {
    setShowSuggestModal(true);
    setSuggestLoading(true);
    try {
      const res = await fetch(`${API}/api/catalogs/suggest?vehicle_id=${vehicleId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSuggestedCatalogs(data.catalogs || []);
      // Pre-select already selected ones OR currently shown catalogs?
      // Let's keep modalSelectedIds empty so user can pick NEW ones to add.
      setModalSelectedIds(new Set());
    } catch (err) {
      console.error("Suggest fetch error:", err);
    } finally {
      setSuggestLoading(false);
    }
  };

  const toggleModalCatalog = (id: string) => {
    setModalSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleApplySuggested = () => {
    // Add selected suggested catalogs to the main catalogs list if not there
    const toAdd = suggestedCatalogs.filter((c) => modalSelectedIds.has(c.id));
    setCatalogs((prev) => {
      const existingIds = new Set(prev.map((c) => c.id));
      const newList = [...prev];
      for (const cat of toAdd) {
        if (!existingIds.has(cat.id)) {
          newList.unshift(cat); // put suggested at top
        }
      }
      return newList;
    });
    // Also auto-check them
    setSelectedIds((prev) => {
      const next = new Set(prev);
      for (const id of modalSelectedIds) next.add(id);
      return next;
    });
    setShowSuggestModal(false);
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
            className="text-[10px] px-2.5 py-1 bg-sky-50 text-sky-700 border border-sky-200 rounded hover:bg-sky-100 transition-colors disabled:opacity-50 flex items-center gap-1"
            title="Enrichment z konfiguracji (card_summary)"
          >
            📋 Z konfiguracji
          </button>
          <button
            onClick={handleOpenSuggestModal}
            disabled={crossRefLoading}
            className="text-[10px] px-2.5 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded hover:bg-indigo-100 transition-colors disabled:opacity-50 flex items-center gap-1 font-medium"
          >
            <Plus className="w-3 h-3" />
            Dodaj dokument
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
                  {cat._ranking && cat._ranking.score >= 0.8 && (
                    <span className="flex items-center gap-1 px-1.5 py-0.5 bg-yellow-100 text-yellow-800 rounded text-[9px] font-bold uppercase tracking-wider ml-2">
                       <Star className="w-2.5 h-2.5" /> LLM Match
                    </span>
                  )}
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

      {/* Suggest Modal */}
      {showSuggestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="px-5 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-600" />
                Dodaj dokument z biblioteki
              </h3>
              <button
                onClick={() => setShowSuggestModal(false)}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto flex-1 bg-slate-50/50">
              {suggestLoading ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                  <Loader2 className="w-8 h-8 animate-spin mb-3 text-indigo-500" />
                  <span className="text-sm">LLM analizuje bibliotekę i sortuje najlepsze dopasowania...</span>
                </div>
              ) : suggestedCatalogs.length === 0 ? (
                <div className="text-sm text-slate-500 text-center py-8">
                  Brak dostępnych dokumentów w bibliotece.
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-xs text-slate-500 mb-4 bg-indigo-50 text-indigo-800 p-3 rounded border border-indigo-100 flex gap-2">
                    <Star className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                    Dokumenty zostały posortowane przez AI pod kątem najlepszego dopasowania do tego pojazdu.
                  </div>
                  {suggestedCatalogs.map((cat, idx) => {
                    const score = cat._ranking?.score || 0;
                    const isHighMatch = score >= 0.7;
                    return (
                      <label
                        key={cat.id}
                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                          modalSelectedIds.has(cat.id)
                            ? "bg-indigo-50 border-indigo-300 ring-1 ring-indigo-200"
                            : "bg-white border-slate-200 hover:border-indigo-200 hover:shadow-sm"
                        }`}
                      >
                        <div className="mt-0.5">
                          <input
                            type="checkbox"
                            checked={modalSelectedIds.has(cat.id)}
                            onChange={() => toggleModalCatalog(cat.id)}
                            className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-slate-900 truncate">
                              {cat.display_name}
                            </span>
                            {isHighMatch && (
                              <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded uppercase tracking-wider whitespace-nowrap">
                                {Math.round(score * 100)}% Match
                              </span>
                            )}
                            {idx === 0 && isHighMatch && (
                              <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-800 text-[10px] font-bold rounded uppercase tracking-wider whitespace-nowrap flex items-center gap-1">
                                <Star className="w-3 h-3" /> Najlepsze dopasowanie
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-slate-500 flex items-center gap-3">
                            <span>{cat.brand} {cat.model_family}</span>
                            <span>·</span>
                            <span>{cat.document_type === "price_list" ? "Cennik" : "Katalog"}</span>
                            <span>·</span>
                            <span>Wariantów: {cat.variant_count}</span>
                          </div>
                          {cat._ranking?.reasoning && (
                            <div className="mt-2 text-[11px] text-slate-600 bg-slate-50 p-2 rounded border border-slate-100 italic">
                              "{cat._ranking.reasoning}"
                            </div>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="px-5 py-4 border-t border-slate-200 bg-white flex justify-end gap-2">
              <button
                onClick={() => setShowSuggestModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded transition-colors"
              >
                Anuluj
              </button>
              <button
                onClick={handleApplySuggested}
                disabled={suggestLoading || modalSelectedIds.size === 0}
                className="px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                Dodaj zaznaczone ({modalSelectedIds.size})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
