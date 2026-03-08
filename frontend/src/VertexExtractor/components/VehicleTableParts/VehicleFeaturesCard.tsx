import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Loader2, Package } from "lucide-react";

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    const fetchFeatures = async () => {
      setLoading(true);
      setError(null);
      try {
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${baseUrl}/api/features/vehicle/${vehicleId}/state`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // data.categories is { "CategoryName": [...features] }
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

        if (!cancelled) {
          setCategories(grouped);
          // Auto-expand categories with present features
          const autoExpand = new Set(
            grouped.filter((g) => g.presentCount > 0).map((g) => g.name)
          );
          setExpandedCats(autoExpand);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Błąd pobierania cech");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchFeatures();
    return () => { cancelled = true; };
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
        {!loading && totalFeatures > 0 && (
          <span className="text-xs text-slate-400">
            {totalPresent} / {totalFeatures} potwierdzonych
          </span>
        )}
      </div>

      {/* Content */}
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
    </div>
  );
}
