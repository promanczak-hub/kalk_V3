import { useState, useEffect, useMemo } from "react";
import { Loader2, Package, Settings, Sparkles } from "lucide-react";
import VehicleFeaturesCrud from "../VehicleFeaturesCrud";
import { AccordionCard } from "./AccordionCard";
import {
  type FeatureItem,
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
  present_confirmed_primary: "bg-emerald-50 text-emerald-700 border-emerald-200",
  present_crossmatched: "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200",
  present_confirmed_secondary: "bg-green-50 text-green-700 border-green-200",
  present_inferred: "bg-blue-50 text-blue-700 border-blue-200",
  absent_confirmed_primary: "bg-red-50 text-red-700 border-red-200",
  absent_confirmed_secondary: "bg-rose-50 text-rose-700 border-rose-200",
  absent_inferred: "bg-orange-50 text-orange-700 border-orange-200",
  unknown: "bg-slate-50 text-slate-600 border-slate-200",
  conflict: "bg-amber-100 text-amber-800 border-amber-300 font-semibold",
};

const NORMALIZED_STATUS_STYLES: Record<string, string> = {
  ...STATUS_STYLES,
  present_confirmed_primary: "bg-violet-50 text-violet-700 border-violet-200",
  present_confirmed_secondary: "bg-purple-50 text-purple-700 border-purple-200",
  present_inferred: "bg-indigo-50 text-indigo-700 border-indigo-200",
};

const DEFAULT_STYLE = "bg-slate-50 text-slate-500 border-slate-200";

function getStatusIcon(status: string): string {
  if (status.startsWith("present")) return "✓";
  if (status.startsWith("absent")) return "✗";
  if (status === "conflict") return "⚠";
  return "?";
}

const CARGO_CATEGORY_HINTS = [
  "ładunk", "ladunk", "cargo", "zabudow", "załad", "zalad",
  "furgon", "chłod", "chlod", "izoter", "winda", "tachograf",
];

function normalizePolish(text: string): string {
  return text
    .toLowerCase()
    .replace(/ą/g, "a").replace(/ć/g, "c").replace(/ę/g, "e")
    .replace(/ł/g, "l").replace(/ń/g, "n").replace(/ó/g, "o")
    .replace(/ś/g, "s").replace(/ź/g, "z").replace(/ż/g, "z");
}

function isPassengerVehicleType(vehicleTypeHint?: string | null): boolean {
  const normalized = normalizePolish(String(vehicleTypeHint || ""));
  return normalized.includes("osob") || normalized.includes("passenger");
}

function isCargoCategory(categoryName: string): boolean {
  const normalized = normalizePolish(categoryName || "");
  return CARGO_CATEGORY_HINTS.some((hint) => normalized.includes(hint));
}

function sortFeatures(features: FeatureItem[]): FeatureItem[] {
  return [...features].sort((a, b) => {
    const aPresent = a.resolved_status?.startsWith("present") ? 0 : 1;
    const bPresent = b.resolved_status?.startsWith("present") ? 0 : 1;
    return aPresent - bPresent;
  });
}

function FeatureChip({ f }: { f: FeatureItem }) {
  const isNormalized = !f.feature_key?.startsWith("config_");
  const style = isNormalized
    ? (NORMALIZED_STATUS_STYLES[f.resolved_status] || DEFAULT_STYLE)
    : (STATUS_STYLES[f.resolved_status] || DEFAULT_STYLE);
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
        <span className="opacity-60 ml-0.5">{f.resolved_value_text}</span>
      )}
      {f.resolved_value_num !== null && (
        <span className="opacity-60 ml-0.5">{f.resolved_value_num}</span>
      )}
    </span>
  );
}

function EdgeSection({ features }: { features: FeatureItem[] }) {
  const [isOpen, setIsOpen] = useState(false);

  if (features.length === 0) return null;

  return (
    <div className="rounded-md bg-purple-50/20 border border-purple-100/60">
      <button
        onClick={() => setIsOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2 hover:bg-white/40 transition-colors"
      >
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-[11px] font-semibold uppercase tracking-wide text-purple-400">
            Szczegółowe / Edge
          </span>
        </div>
        <span className="text-[10px] text-purple-300">{features.length} cech {isOpen ? '▲' : '▼'}</span>
      </button>
      {isOpen && (
        <div className="px-4 pb-3 pt-1 flex flex-wrap gap-1.5">
          {sortFeatures(features).map(f => <FeatureChip key={f.feature_key} f={f} />)}
        </div>
      )}
    </div>
  );
}

export function VehicleFeaturesCard({ vehicleId, vehicleTypeHint }: VehicleFeaturesCardProps) {
  const [rawCategories, setRawCategories] = useState<CategoryGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPanelCollapsed] = useState(true);
  const [showCrudPanel, setShowCrudPanel] = useState(false);

  const fetchFeatures = async (forceRefetch = false) => {
    const hasCache = !forceRefetch && featuresCache.has(vehicleId);
    if (!hasCache) setLoading(true);
    setError(null);
    try {
      if (!hasCache) {
        await fetchFeaturesForCache(vehicleId);
      }
      const cached = featuresCache.get(vehicleId)!;
      const instantFeatures = cached.instantFeatures;
      const data = cached.data;

      let grouped: CategoryGroup[] = [];

      if (instantFeatures.length > 0) {
        grouped.push({
          name: "Konfiguracja",
          features: instantFeatures,
          presentCount: instantFeatures.length,
        });
      }

      const apiGroups = Object.entries(data.categories as Record<string, FeatureItem[]>)
        .map(([name, apiFeatures]) => {
          const processedFeatures = apiFeatures.map(f => ({ ...f }));
          return {
            name,
            features: processedFeatures,
            presentCount: processedFeatures.filter(f => f.resolved_status?.startsWith("present")).length,
          };
        })
        .filter((g) => g.features.length > 0)
        .sort((a, b) => b.presentCount - a.presentCount);

      grouped = [...grouped, ...apiGroups];
      setRawCategories(grouped);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd pobierania cech");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!featuresCache.has(vehicleId)) {
      setRawCategories([]);
    }
    setError(null);
    fetchFeatures();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleId]);

  const categories = isPassengerVehicleType(vehicleTypeHint)
    ? rawCategories.filter((group) => !isCargoCategory(group.name))
    : rawCategories;

  const allFeatures = useMemo(() => categories.flatMap(cat => cat.features), [categories]);

  // Main features: CORE + EXTENDED (flat, no section headers)
  const mainFeatures = useMemo(
    () => allFeatures.filter(f => f.feature_tier !== 'EDGE'),
    [allFeatures]
  );
  // Edge: niche/specialized features shown separately
  const edgeFeatures = useMemo(
    () => allFeatures.filter(f => f.feature_tier === 'EDGE'),
    [allFeatures]
  );

  const totalFeatures = allFeatures.length;
  const totalPresent = allFeatures.filter(f => f.resolved_status?.startsWith("present")).length;
  const totalEdge = edgeFeatures.length;

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

  const titleNode = (
    <div className="flex items-center gap-2">
      <Package className="w-3.5 h-3.5" />
      Cechy użytkowe pojazdu
    </div>
  );

  const headerRightNodes = (
    <div className="flex items-center gap-3">
      {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />}
      {!loading && totalFeatures > 0 && (
        <div className="flex items-center gap-2">
          {totalEdge > 0 && (
            <span className="text-[9px] font-bold bg-purple-100 text-purple-500 px-1.5 py-0.5 rounded-full" title="EDGE">
              ✨ {totalEdge}
            </span>
          )}
          <span className="text-xs text-slate-400">{totalPresent} / {totalFeatures}</span>
        </div>
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
  );

  return (
    <AccordionCard
      title={titleNode}
      headerRight={headerRightNodes}
      defaultOpen={!isPanelCollapsed}
    >
      {showCrudPanel && (
        <div className="p-2">
          <VehicleFeaturesCrud
            vehicleId={vehicleId}
            onClose={() => setShowCrudPanel(false)}
          />
        </div>
      )}

      {!showCrudPanel && (
        <div className="p-5">
          {loading && (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              <span className="text-sm">Ładowanie cech...</span>
            </div>
          )}

          {error && (
            <div className="text-sm text-red-500 py-4 text-center">{error}</div>
          )}

          {!loading && !error && categories.length === 0 && (
            <div className="text-sm text-slate-400 py-6 text-center">
              Brak danych o cechach użytkowych dla tego pojazdu.
            </div>
          )}

          {!loading && !error && categories.length > 0 && (
            <div className="space-y-3">
              {/* Flat list — all CORE + EXTENDED features without section headers */}
              {mainFeatures.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {sortFeatures(mainFeatures).map(f => (
                    <FeatureChip key={f.feature_key} f={f} />
                  ))}
                </div>
              )}

              {/* EDGE — collapsible, only when present */}
              <EdgeSection features={edgeFeatures} />
            </div>
          )}
        </div>
      )}
    </AccordionCard>
  );
}
