import { useState, useEffect } from "react";
import { apiFetch } from "../../../lib/api";
import { ChevronDown, ChevronRight, Loader2, Package, Settings } from "lucide-react";
import VehicleFeaturesCrud from "../VehicleFeaturesCrud";

interface FeatureItem {
  feature_key: string;
  display_name: string;
  resolved_status: string;
  resolved_value_bool: boolean | null;
  resolved_value_text: string | null;
  resolved_value_num: number | null;
  confidence_score: number | null;
  category_name: string;
}

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
  const [configFeatures, setConfigFeatures] = useState<FeatureItem[]>([]);

  const fetchFeatures = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch from Synthesis Data (Local instant fallback)
      const vehicleResp = await apiFetch(`/api/kalkulator/pojazd/${vehicleId}`);
      let instantFeatures: FeatureItem[] = [];
      if (vehicleResp.ok) {
        const vehicleData = await vehicleResp.json();
        const synthData = vehicleData.synthesis_data?.card_summary || {};
        
        const stdEq = (synthData.standard_equipment || []).map((name: string, i: number) => ({
          feature_key: `config_std_${name}_${i}`,
          display_name: name,
          resolved_status: "present_confirmed_primary", // Will map to green
          resolved_value_bool: true,
          resolved_value_text: null,
          resolved_value_num: null,
          confidence_score: 1.0,
          category_name: "⭐ Konfiguracja (PDF)"
        }));

        const paidEq = (synthData.paid_options || []).map((opt: any, i: number) => ({
          feature_key: `config_paid_${opt.name}_${i}`,
          display_name: opt.name,
          resolved_status: "present_confirmed_primary", // Will map to green
          resolved_value_bool: true,
          resolved_value_text: opt.price,
          resolved_value_num: null,
          confidence_score: 1.0,
          category_name: "⭐ Konfiguracja (PDF)"
        }));
        
        instantFeatures = [...stdEq, ...paidEq];
        setConfigFeatures(instantFeatures);
      }

      // 2. Fetch from API (Async cross-referenced)
      const response = await apiFetch(`/api/features/vehicle/${vehicleId}/state`);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

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
    setConfigFeatures([]);
    setError(null);
    fetchFeatures();
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
        fetchFeatures();
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
    </div>
  );
}
