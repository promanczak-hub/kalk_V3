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
}

const STATUS_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  present_confirmed_primary: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  present_confirmed_secondary: { bg: "bg-emerald-50", text: "text-emerald-600", border: "border-emerald-200" },
  present_inferred: { bg: "bg-sky-50", text: "text-sky-600", border: "border-sky-200" },
  absent_confirmed: { bg: "bg-slate-50", text: "text-slate-400", border: "border-slate-200" },
  absent_inferred: { bg: "bg-slate-50", text: "text-slate-400", border: "border-slate-200" },
  contradicted: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-200" },
};

const DEFAULT_STYLE = { bg: "bg-slate-50", text: "text-slate-500", border: "border-slate-200" };

function getStatusIcon(status: string): string {
  if (status.startsWith("present")) return "✓";
  if (status.startsWith("absent")) return "✗";
  if (status === "contradicted") return "⚠";
  return "?";
}

export function VehicleFeaturesCard({ vehicleId }: VehicleFeaturesCardProps) {
  const [categories, setCategories] = useState<CategoryGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());
  const [hasLoaded, setHasLoaded] = useState(false);
  const [showCrudPanel, setShowCrudPanel] = useState(false);

  const fetchFeatures = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/features/vehicle/${vehicleId}/state`);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      const grouped: CategoryGroup[] = Object.entries(data.categories as Record<string, FeatureItem[]>)
        .map(([name, features]) => ({
          name,
          features,
          presentCount: features.filter(
            (f) => f.resolved_status?.startsWith("present")
          ).length,
        }))
        .filter((g) => g.features.length > 0)
        .sort((a, b) => b.presentCount - a.presentCount);

      setCategories(grouped);
      const autoExpand = new Set(
        grouped.filter((g) => g.presentCount > 0).map((g) => g.name)
      );
      setExpandedCats(autoExpand);
      setHasLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd pobierania cech");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Zresetuj stan, gdy zmieni się vehicleId
    setCategories([]);
    setHasLoaded(false);
    setError(null);
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

  const totalPresent = categories.reduce((s, c) => s + c.presentCount, 0);
  const totalFeatures = categories.reduce((s, c) => s + c.features.length, 0);

  return (
    <div className="border border-slate-200 rounded bg-white">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-2">
          <Package className="w-3.5 h-3.5" />
          Cechy użytkowe pojazdu
        </h4>
        <div className="flex items-center gap-3">
          {!loading && totalFeatures > 0 && (
            <span className="text-xs text-slate-400">
              {totalPresent} / {totalFeatures} potwierdzonych
            </span>
          )}
          <button
            onClick={() => setShowCrudPanel(prev => !prev)}
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
        {!hasLoaded && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-6 text-slate-500">
            <span className="text-sm mb-3">Cechy nie zostały jeszcze wczytane.</span>
            <button
              onClick={fetchFeatures}
              className="px-4 py-2 bg-white border border-slate-300 rounded text-sm font-medium hover:bg-slate-50 transition-colors shadow-sm"
            >
              Wczytaj cechy użytkowe
            </button>
          </div>
        )}

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

        {hasLoaded && !loading && !error && categories.length === 0 && (
          <div className="text-sm text-slate-400 py-6 text-center">
            Brak danych o cechach użytkowych dla tego pojazdu.
          </div>
        )}

        {hasLoaded && !loading && !error && categories.length > 0 && (
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
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border ${style.bg} ${style.text} ${style.border}`}
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
    </div>
  );
}
