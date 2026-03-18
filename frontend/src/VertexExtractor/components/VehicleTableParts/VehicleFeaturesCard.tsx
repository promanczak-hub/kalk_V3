import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../../../lib/api";
import { ChevronDown, ChevronRight, Loader2, Package, Settings, FileText, AlertTriangle, ExternalLink } from "lucide-react";
import VehicleFeaturesCrud from "../VehicleFeaturesCrud";
import { CatalogFeatureSelectorModal } from "./CatalogFeatureSelectorModal";
import {
  type FeatureItem,
  type SuggestedCatalog,
  featuresCache,
  fetchFeaturesForCache
} from "../../hooks/useVehicleFeaturesCache";

interface CategoryGroup {
  name: string;
  features: FeatureItem[];
  presentCount: number;
}

interface VehicleFeaturesCardProps {
  vehicleId: string;
  vehicleTypeHint?: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  present_confirmed_primary: "bg-emerald-50 text-emerald-700 border-emerald-200", // Green for Config PDF
  present_crossmatched: "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200", // Purple for Cenniki crossmatch
  present_confirmed_secondary: "bg-green-50 text-green-700 border-green-200",
  present_inferred: "bg-blue-50 text-blue-700 border-blue-200",
  absent_confirmed_primary: "bg-red-50 text-red-700 border-red-200",
  absent_confirmed_secondary: "bg-rose-50 text-rose-700 border-rose-200",
  absent_inferred: "bg-orange-50 text-orange-700 border-orange-200",
  unknown: "bg-slate-50 text-slate-600 border-slate-200",
  conflict: "bg-amber-100 text-amber-800 border-amber-300 font-semibold",
};

const DEFAULT_STYLE = "bg-slate-50 text-slate-500 border-slate-200";

function getStatusIcon(status: string): string {
  if (status.startsWith("present")) return "✓";
  if (status.startsWith("absent")) return "✗";
  if (status === "conflict") return "⚠";
  return "?";
}

const CARGO_CATEGORY_HINTS = [
  "ładunk",
  "ladunk",
  "cargo",
  "zabudow",
  "załad",
  "zalad",
  "furgon",
  "chłod",
  "chlod",
  "izoter",
  "winda",
  "tachograf",
];

function normalizePolish(text: string): string {
  return text
    .toLowerCase()
    .replace(/ą/g, "a")
    .replace(/ć/g, "c")
    .replace(/ę/g, "e")
    .replace(/ł/g, "l")
    .replace(/ń/g, "n")
    .replace(/ó/g, "o")
    .replace(/ś/g, "s")
    .replace(/ź/g, "z")
    .replace(/ż/g, "z");
}

function isPassengerVehicleType(vehicleTypeHint?: string | null): boolean {
  const normalized = normalizePolish(String(vehicleTypeHint || ""));
  return normalized.includes("osob") || normalized.includes("passenger");
}

function isCargoCategory(categoryName: string): boolean {
  const normalized = normalizePolish(categoryName || "");
  return CARGO_CATEGORY_HINTS.some((hint) => normalized.includes(hint));
}

export function VehicleFeaturesCard({ vehicleId, vehicleTypeHint }: VehicleFeaturesCardProps) {
  const [rawCategories, setRawCategories] = useState<CategoryGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set(["⭐ Konfiguracja (PDF)"]));
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);
  const [showCrudPanel, setShowCrudPanel] = useState(false);
  const [suggestedCatalog, setSuggestedCatalog] = useState<SuggestedCatalog | null>(null);
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  const [enriching, setEnriching] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [matchedCatalogs, setMatchedCatalogs] = useState<any[]>([]);
  const [showCatalogDropdown, setShowCatalogDropdown] = useState(false);
  const catalogDropdownRef = useRef<HTMLDivElement>(null);

  // Click-away to close catalog dropdown
  useEffect(() => {
    if (!showCatalogDropdown) return;
    const handler = (e: MouseEvent) => {
      if (catalogDropdownRef.current && !catalogDropdownRef.current.contains(e.target as Node)) {
        setShowCatalogDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showCatalogDropdown]);

  const handleEnrichment = async () => {
    setEnriching(true);
    try {
      const res = await apiFetch(`/api/features/vehicle/${vehicleId}/enrich-background`, { method: "POST" });
      if (!res.ok) throw new Error("Wystąpił błąd podczas zlecania zadania do Celery.");
      alert("Rozpoczęto w pełni zautomatyzowaną analizę dokumentów w tle (100% match). Cechy pojawią się po zakończeniu.");
    } catch (err) {
      alert("Błąd: " + (err instanceof Error ? err.message : "Nieznany błąd"));
    } finally {
      setEnriching(false);
    }
  };

  const fetchFeatures = async (forceRefetch = false) => {
    const hasCache = !forceRefetch && featuresCache.has(vehicleId);
    if (!hasCache) setLoading(true);
    
    setError(null);
    try {
      if (!hasCache) {
          await fetchFeaturesForCache(vehicleId);
      }
      
      const cached = featuresCache.get(vehicleId)!;
      setSuggestedCatalog(cached.suggestedCatalog);
      
      const instantFeatures = cached.instantFeatures;
      const data = cached.data;
      
      let grouped: CategoryGroup[] = [];
      
      // Add local config features as the first category if they exist
      if (instantFeatures.length > 0) {
        grouped.push({
          name: "⭐ Konfiguracja (PDF)",
          features: instantFeatures,
          presentCount: instantFeatures.length,
        });
      }

      // Process API features
      const apiGroups = Object.entries(data.categories as Record<string, any[]>)
        .map(([name, apiFeatures]) => {
          // Filter out features that came from 'spec' because we already show them in the local config group to prevent obvious duplicates
          const processedFeatures = apiFeatures
             .filter(f => f.resolution_source !== 'spec') // Avoid duplicating the PDF features
             .map(f => {
               // If it's from catalog/price_list, force a custom status to make it purple
               // Normally 'catalog' maps to 'present_inferred'.
               let status = f.resolved_status;
               if (f.resolution_source === 'catalog' || f.resolution_source === 'price_list') {
                  status = "present_crossmatched"; // We will add a style for this
               }
               return { ...f, resolved_status: status };
             });

          return {
            name,
            features: processedFeatures,
            presentCount: processedFeatures.filter(
              (f) => f.resolved_status?.startsWith("present")
            ).length,
          };
        })
        .filter((g) => g.features.length > 0)
        .sort((a, b) => b.presentCount - a.presentCount);
      
      grouped = [...grouped, ...apiGroups];

      setRawCategories(grouped);
      const autoExpand = new Set(
        grouped.filter((g) => g.presentCount > 0).map((g) => g.name)
      );
      setExpandedCats(prev => new Set([...prev, "⭐ Konfiguracja (PDF)", ...autoExpand]));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd pobierania cech");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Auto-load cech po zmianie vehicleId
    setRawCategories([]);
    setError(null);
    fetchFeatures();
    // Fetch matched catalogs for this vehicle
    (async () => {
      try {
        const res = await apiFetch(`/api/catalogs/match?vehicle_id=${vehicleId}`);
        if (res.ok) {
          const data = await res.json();
          setMatchedCatalogs(data.catalogs || []);
        }
      } catch {
        // Silent — non-critical
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleId]);

  const categories = isPassengerVehicleType(vehicleTypeHint)
    ? rawCategories.filter((group) => !isCargoCategory(group.name))
    : rawCategories;

  const totalFeatures = categories.reduce((sum, cat) => sum + cat.features.length, 0);
  const totalPresent = categories.reduce((sum, cat) => sum + cat.presentCount, 0);

  // Set up event listener to allow external triggers to refresh features
  useEffect(() => {
    const handleRefresh = (e: CustomEvent) => {
      if (e.detail?.vehicleId === vehicleId) {
        fetchFeatures(true);
      }
    };
    window.addEventListener('refreshVehicleFeatures', handleRefresh as EventListener);
    return () => window.removeEventListener('refreshVehicleFeatures', handleRefresh as EventListener);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleId]);

  const toggleCategory = (name: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  return (
    <div className="border border-slate-200 rounded bg-white">
      {/* Header — klikalny toggle zwijania */}
      <div
        className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center cursor-pointer select-none hover:bg-slate-100 transition-colors"
        onClick={() => setIsPanelCollapsed((prev) => !prev)}
      >
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-2">
          {isPanelCollapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
             <ChevronDown className="w-3.5 h-3.5" />
          )}
          <Package className="w-3.5 h-3.5" />
          Cechy użytkowe pojazdu
        </h4>
        <div className="flex items-center gap-3">
          {loading && (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />
          )}
          {!loading && totalFeatures > 0 && (
            <span className="text-xs text-slate-400">
              {totalPresent} / {totalFeatures} potwierdzonych
            </span>
          )}
          {/* Catalog match badge */}
          {matchedCatalogs.length > 0 && (
            <div className="relative" ref={catalogDropdownRef}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowCatalogDropdown(prev => !prev);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border transition-colors bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200 hover:bg-fuchsia-100"
                title="Dopasowane cenniki"
              >
                <FileText className="w-3 h-3" />
                {matchedCatalogs.length} {matchedCatalogs.length === 1 ? 'cennik' : matchedCatalogs.length < 5 ? 'cenniki' : 'cenników'}
              </button>
              {showCatalogDropdown && (
                <div
                  className="absolute right-0 top-full mt-1 w-80 bg-white border border-slate-200 rounded-lg shadow-xl z-50 overflow-hidden"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Dopasowane cenniki / dokumenty
                  </div>
                  <div className="max-h-60 overflow-y-auto divide-y divide-slate-100">
                    {matchedCatalogs.map((cat: any) => (
                      <div
                        key={cat.id}
                        className="px-3 py-2.5 hover:bg-slate-50 transition-colors flex items-center gap-2.5"
                      >
                        {cat.extraction_status === 'error' ? (
                          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                        ) : (
                          <FileText className="w-4 h-4 text-fuchsia-500 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-slate-700 truncate">
                            {cat.display_name || cat.model_family}
                          </p>
                          <p className="text-[10px] text-slate-400">
                            {cat.brand} · {cat.document_type}
                            {cat.extraction_status === 'error' && ' · ⚠️ Ekstrakcja nieudana'}
                            {cat.variant_count > 0 && ` · ${cat.variant_count} wariantów`}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {cat.score != null && (
                            <span className="text-[10px] font-bold text-fuchsia-600 bg-fuchsia-50 px-1.5 py-0.5 rounded">
                              {Math.round(cat.score * 100)}%
                            </span>
                          )}
                          {cat.extraction_status !== 'error' && (
                            <a
                              href={`/api/catalogs/${cat.id}/file`}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-slate-400 hover:text-fuchsia-600 transition-colors"
                              title="Otwórz PDF"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleEnrichment();
            }}
            disabled={enriching}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border transition-colors bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100 disabled:opacity-50"
            title="Wzbogać cechy w tle z dostępnych dokumentów"
          >
            {enriching ? <Loader2 className="w-3 h-3 animate-spin" /> : "✨"}
            {enriching ? "Analiza w tle..." : "Wzbogać cechy"}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowCrudPanel(prev => !prev);
            }}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border transition-colors"
            style={{
              background: showCrudPanel ? '#3b82f6' : 'white',
              color: showCrudPanel ? 'white' : '#64748b',
              borderColor: showCrudPanel ? '#3b82f6' : '#cbd5e1',
            }}
            title="Edytuj cechy (widok CRUD)"
          >
            <Settings className="w-3 h-3" />
            {showCrudPanel ? 'Zamknij CRUD' : 'Edytuj'}
          </button>
        </div>
      </div>

      {/* Collapsible content */}
      {!isPanelCollapsed && (
        <>
          {/* CRUD Panel (full editing mode) */}
          {showCrudPanel && (
            <div className="p-2">
              <VehicleFeaturesCrud
                vehicleId={vehicleId}
                onClose={() => setShowCrudPanel(false)}
              />
            </div>
          )}

          {/* Content (read-only chips view) */}
          {!showCrudPanel && (
            <div className="p-5">
              {loading && (
                <div className="flex items-center justify-center py-8 text-slate-400">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  <span className="text-sm">Ładowanie cech...</span>
                </div>
              )}

              {error && (
                <div className="text-sm text-red-500 py-4 text-center">
                  {error}
                </div>
              )}

              {suggestedCatalog && !loading && !error && (
                <div className="mb-4 mx-4 mt-2">
                  <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 flex items-center justify-between shadow-sm">
                    <div className="flex items-center gap-3">
                       <span className="text-xl bg-white p-1 rounded shadow-sm border border-indigo-100">✨</span>
                       <div>
                         <p className="text-sm font-semibold text-indigo-900 leading-snug">
                           {suggestedCatalog.display_name}
                         </p>
                         <p className="text-xs text-indigo-700 mt-0.5 font-medium">
                           Dopasowanie do pojazdu: <span className="text-indigo-800 font-bold">{Math.round(suggestedCatalog.score * 100)}%</span>
                         </p>
                       </div>
                    </div>
                    <button
                      onClick={() => setShowCatalogModal(true)}
                      className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded shadow-sm hover:bg-indigo-700 hover:shadow transition-all"
                    >
                      Przejrzyj opcje
                    </button>
                  </div>
                </div>
              )}

              {!loading && !error && categories.length === 0 && (
                <div className="text-sm text-slate-400 py-6 text-center">
                  Brak danych o cechach użytkowych dla tego pojazdu.
                </div>
              )}

              {!loading && !error && categories.length > 0 && (
                <div className="space-y-2">
                  {categories.map((cat) => (
                    <div key={cat.name} className="border border-slate-100 rounded-lg overflow-hidden">
                      {/* Category header */}
                      <button
                        onClick={() => toggleCategory(cat.name)}
                        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors text-left"
                      >
                        <div className="flex items-center gap-2">
                          {expandedCats.has(cat.name) ? (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-slate-400" />
                          )}
                          <span className="text-sm font-medium text-slate-700">{cat.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {cat.presentCount > 0 && (
                            <span className="text-[10px] font-bold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
                              {cat.presentCount}
                            </span>
                          )}
                          <span className="text-[10px] text-slate-400">
                            {cat.features.length} cech
                          </span>
                        </div>
                      </button>

                      {/* Features chips */}
                      {expandedCats.has(cat.name) && (
                        <div className="px-4 pb-3 pt-1 flex flex-wrap gap-1.5">
                          {cat.features
                            .sort((a, b) => {
                              // Present features first
                              const aPresent = a.resolved_status?.startsWith("present") ? 0 : 1;
                              const bPresent = b.resolved_status?.startsWith("present") ? 0 : 1;
                              return aPresent - bPresent;
                            })
                            .map((f) => {
                              const style = STATUS_STYLES[f.resolved_status] || DEFAULT_STYLE;
                              const icon = getStatusIcon(f.resolved_status);
                              return (
                                <span
                                  key={f.feature_key}
                                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border ${style}`}
                                  title={`${f.display_name} — ${f.resolved_status}${f.resolved_value_text ? `: ${f.resolved_value_text}` : ""}${f.confidence_score ? ` (${Math.round(f.confidence_score * 100)}%)` : ""}`}
                                >
                                  <span className="text-[10px]">{icon}</span>
                                  {f.display_name}
                                  {f.resolved_value_text && (
                                    <span className="opacity-60 ml-0.5">
                                      {f.resolved_value_text}
                                    </span>
                                  )}
                                  {f.resolved_value_num !== null && (
                                    <span className="opacity-60 ml-0.5">
                                      {f.resolved_value_num}
                                    </span>
                                  )}
                                </span>
                              );
                            })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
      {/* We will conditionally render the modal if a suggested catalog is present */}
      {showCatalogModal && suggestedCatalog && (
        <CatalogFeatureSelectorModal
          vehicleId={vehicleId}
          catalogId={suggestedCatalog.catalog_id}
          catalogName={suggestedCatalog.display_name}
          onClose={() => setShowCatalogModal(false)}
          onSuccess={() => {
            setShowCatalogModal(false);
            setSuggestedCatalog(null);
            fetchFeatures();
          }}
        />
      )}
    </div>
  );
}
