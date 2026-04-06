import { useState } from "react";
import { Search, TrendingUp, Loader2, Info } from "lucide-react";
import { API_BASE_URL } from "../config/env";
import { apiClient } from "../lib/apiClient";

/* ── Types ──────────────────────────────────────────────────────────── */

interface ReversePriceLookupProps {
  basePayload: Record<string, unknown> | null;
  vehicleId?: string;
}

interface SimilarVehicle {
  vehicle_id: string;
  brand: string;
  model: string;
  version?: string;
  version_name?: string;
  engine_name?: string;
  body_type?: string;
  fuel?: string;
  transmission?: string;
  samar_category?: string;
  monthly_price_net: number;
  best_monthly_price?: number;
  score?: number;
  match_score_pct?: number;
  similarity_score_pct?: number;
  match_reason: string;
}

interface LookupResult {
  priceMin: number;
  priceMax: number;
  months: number;
  totalKm: number;
  baseCostNet: number;
  impliedMarginMin: number;
  impliedMarginMax: number;
  priceAtMargins: { margin: number; price: number }[];
}

/* ── Helpers ─────────────────────────────────────────────────────────── */

function fmtPLN(v: number): string {
  return v.toLocaleString("pl-PL", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function getMarginColor(pct: number): string {
  if (pct < 0) return "#ef4444";
  if (pct < 8) return "#f97316";
  if (pct < 12) return "#eab308";
  if (pct < 15) return "#84cc16";
  if (pct < 20) return "#22c55e";
  return "#06b6d4";
}

function getMarginLabel(pct: number): string {
  if (pct < 0) return "Ujemna";
  if (pct < 8) return "Poniżej min.";
  if (pct < 12) return "Minimalna";
  if (pct < 15) return "Dobra";
  if (pct < 20) return "Bardzo dobra";
  return "Wysoka";
}

/* ── Main Component ────────────────────────────────────────────────── */

export function ReversePriceLookup({ basePayload, vehicleId }: ReversePriceLookupProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [priceMinInput, setPriceMinInput] = useState<string>("");
  const [priceMaxInput, setPriceMaxInput] = useState<string>("");
  const [months, setMonths] = useState<string>("42");
  const [totalKm, setTotalKm] = useState<string>("82000");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LookupResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [similarCars, setSimilarCars] = useState<SimilarVehicle[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  const handleSearch = async () => {
    if (!basePayload) {
      setError("Brak danych bazowych — wróć do kalkulacji.");
      return;
    }

    const pMin = parseFloat(priceMinInput);
    const pMax = parseFloat(priceMaxInput);

    if (!pMin || pMin <= 0 || !pMax || pMax <= 0) {
      setError("Podaj prawidłowy zakres cen.");
      return;
    }
    if (pMin > pMax) {
      setError("Cena minimalna nie może być wyższa od maksymalnej.");
      return;
    }
    const mc = parseInt(months);
    const km = parseInt(totalKm);
    if (!mc || mc < 6) {
      setError("Okres musi wynosić co najmniej 6 miesięcy.");
      return;
    }
    if (!km || km < 1000) {
      setError("Podaj prawidłowy przebieg (min. 1 000 km).");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const baseUrl = API_BASE_URL;

      // Send a request with margin = 0% to get pure base_cost_net
      const zeroMarginPayload = {
        ...basePayload,
        okres_bazowy: mc,
        przebieg_bazowy: km,
        pricing_margin_pct: 0.001, // near-zero to avoid division issues
      };

      const resp = await apiClient.fetch(`${baseUrl}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(zeroMarginPayload),
      });

      if (!resp.ok) {
        throw new Error("Błąd odpowiedzi z API");
      }

      const data = await resp.json();
      const cells = data.cells || [];

      // Find the cell closest to our requested months
      const targetCell = cells.reduce(
        (closest: Record<string, number> | null, c: Record<string, number>) => {
          if (!closest) return c;
          return Math.abs(c.Okres - mc) < Math.abs(closest.Okres - mc) ? c : closest;
        },
        null,
      );

      if (!targetCell) {
        throw new Error("Brak wyników kalkulacji.");
      }

      const baseCostNet = targetCell.KosztyLaczneMC;

      // Calculate implied margin range:
      // price = base / (1 - m) → m = 1 - base/price
      const impliedMarginMax = (1 - baseCostNet / pMax) * 100;
      const impliedMarginMin = (1 - baseCostNet / pMin) * 100;

      // Generate price-at-margin table
      const marginSteps = [0, 5, 8, 10, 12, 15, 18, 20, 25, 30];
      const priceAtMargins = marginSteps.map((m) => ({
        margin: m,
        price: Math.round(baseCostNet / (1 - m / 100)),
      }));

      setResult({
        priceMin: pMin,
        priceMax: pMax,
        months: mc,
        totalKm: km,
        baseCostNet,
        impliedMarginMin,
        impliedMarginMax,
        priceAtMargins,
      });

      // After successful calculation, trigger discovery of similar cars if vehicleId exists
      if (vehicleId) {
        fetchSimilarCars(vehicleId, mc, km, "semantic");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nieznany błąd");
    } finally {
      setLoading(false);
    }
  };

  const fetchSimilarCars = async (id: string, mc: number, km: number, mode: string = "semantic") => {
    setLoadingSimilar(true);
    setSimilarCars([]);
    try {
      const resp = await apiClient.fetch(
        `${API_BASE_URL}/api/scoring-search/vehicle/${id}/similar?duration_months=${mc}&annual_mileage=${Math.round(
          (km / mc) * 12,
        )}&limit=5&mode=${mode}`,
      );
      if (resp.ok) {
        const data = await resp.json();
        // Normalize fields for display
        const normalized = data.map((v: SimilarVehicle) => ({
          ...v,
          monthly_price_net: v.monthly_price_net || v.best_monthly_price || 0,
          version_name: v.version || v.version_name || "N/A",
          body_type: v.body_type || v.samar_category || "N/A",
          score: v.similarity_score_pct || v.match_score_pct || (v.score ? v.score * 100 : 0)
        }));
        setSimilarCars(normalized);
      }
    } catch (err) {
      console.error("Discovery error:", err);
    } finally {
      setLoadingSimilar(false);
    }
  };

  return (
    <div className="mb-4 rounded-2xl border border-slate-200/80 bg-gradient-to-br from-white via-purple-50/20 to-indigo-50/30 shadow-sm overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-purple-100">
            <Search className="w-4 h-4 text-purple-600" />
          </div>
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Odwrotne wyszukiwanie ceny
          </span>
        </div>
        <span className="text-[9px] font-bold text-slate-400 uppercase">
          {isOpen ? "Zwiń ▲" : "Rozwiń ▼"}
        </span>
      </button>

      {isOpen && (
        <div className="px-5 pb-5 pt-2 border-t border-slate-100 animate-in fade-in slide-in-from-top-1 duration-200">
          {/* Hint */}
          <div className="flex items-start gap-2 mb-4 p-2.5 rounded-lg bg-indigo-50/60 border border-indigo-100">
            <Info className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
            <p className="text-[10px] text-indigo-600 leading-relaxed">
              Wpisz cenę oczekiwaną, okres i przebieg — system wyliczy, przy jakiej marży ta
              stawka jest osiągalna.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                Cena minimalna
              </label>
              <div className="relative">
                <input
                  type="number"
                  placeholder="np. 2500"
                  value={priceMinInput}
                  onChange={(e) => setPriceMinInput(e.target.value)}
                  className="w-full text-sm font-semibold p-2.5 pr-12 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-purple-300 focus:border-purple-400 bg-white tabular-nums"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-medium">
                  PLN/mc
                </span>
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                Cena maksymalna
              </label>
              <div className="relative">
                <input
                  type="number"
                  placeholder="np. 3500"
                  value={priceMaxInput}
                  onChange={(e) => setPriceMaxInput(e.target.value)}
                  className="w-full text-sm font-semibold p-2.5 pr-12 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-purple-300 focus:border-purple-400 bg-white tabular-nums"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-medium">
                  PLN/mc
                </span>
              </div>
            </div>
          </div>

          {/* Period and mileage */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                Okres
              </label>
              <div className="relative">
                <input
                  type="number"
                  placeholder="np. 42"
                  value={months}
                  onChange={(e) => setMonths(e.target.value)}
                  className="w-full text-sm font-semibold p-2.5 pr-8 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-purple-300 focus:border-purple-400 bg-white tabular-nums"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-medium">
                  mc
                </span>
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                Przebieg
              </label>
              <div className="relative">
                <input
                  type="number"
                  placeholder="np. 82000"
                  value={totalKm}
                  onChange={(e) => setTotalKm(e.target.value)}
                  className="w-full text-sm font-semibold p-2.5 pr-8 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-purple-300 focus:border-purple-400 bg-white tabular-nums"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-medium">
                  km
                </span>
              </div>
            </div>
          </div>

          {/* Search button */}
          <button
            onClick={handleSearch}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 text-xs font-bold px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-700 hover:to-indigo-700 transition-all shadow-md shadow-purple-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Szukam…
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Wylicz zakres marży
              </>
            )}
          </button>

          {/* Error */}
          {error && (
            <div className="mt-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 font-medium text-center">
              {error}
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="mt-4 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
              {/* Main result card */}
              <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
                <div className="text-center mb-3">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">
                    Zakres cen: {fmtPLN(result.priceMin)} – {fmtPLN(result.priceMax)} PLN netto/mc
                  </div>
                  <div className="text-[10px] text-slate-400">
                    ({result.months} mc / {result.totalKm.toLocaleString("pl-PL")} km)
                  </div>
                </div>

                {/* Implied margin range */}
                <div className="flex items-center justify-center gap-4 p-3 rounded-xl"
                  style={{
                    backgroundImage: `linear-gradient(to right, ${getMarginColor(result.impliedMarginMin)}15, ${getMarginColor(result.impliedMarginMax)}15)`,
                  }}
                >
                  <TrendingUp
                    className="w-5 h-5"
                    style={{ color: getMarginColor((result.impliedMarginMin + result.impliedMarginMax) / 2) }}
                  />
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-2">
                      <span
                        className="text-xl font-black tabular-nums"
                        style={{ color: getMarginColor(result.impliedMarginMin) }}
                      >
                        {result.impliedMarginMin.toFixed(1)}%
                      </span>
                      <span className="text-slate-400 font-bold">—</span>
                      <span
                        className="text-xl font-black tabular-nums"
                        style={{ color: getMarginColor(result.impliedMarginMax) }}
                      >
                        {result.impliedMarginMax.toFixed(1)}%
                      </span>
                    </div>
                    <div className="text-[10px] font-bold text-slate-500 mt-0.5">
                      Zakres marży — {getMarginLabel(result.impliedMarginMin)} → {getMarginLabel(result.impliedMarginMax)}
                    </div>
                  </div>
                </div>

                <div className="mt-2 text-center">
                  <span className="text-[10px] text-slate-400">
                    Koszt bazowy (0% marży): <span className="font-bold text-slate-600">{fmtPLN(result.baseCostNet)} PLN</span>
                  </span>
                </div>
              </div>

              {/* Price-at-margin table */}
              <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
                <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">
                  Tabela stawek dla różnych poziomów marży
                </h4>
                <div className="grid grid-cols-5 gap-1.5">
                  {result.priceAtMargins.map(({ margin, price }) => {
                    const isInTargetRange =
                      margin >= result.impliedMarginMin - 1 &&
                      margin <= result.impliedMarginMax + 1;
                    return (
                      <div
                        key={margin}
                        className={`p-2 rounded-lg text-center transition-all ${
                          isInTargetRange
                            ? "ring-2 ring-purple-400 shadow-sm"
                            : ""
                        }`}
                        style={{
                          backgroundColor: `${getMarginColor(margin)}12`,
                          borderWidth: "1px",
                          borderStyle: "solid",
                          borderColor: `${getMarginColor(margin)}30`,
                        }}
                      >
                        <div
                          className="text-[10px] font-bold"
                          style={{ color: getMarginColor(margin) }}
                        >
                          {margin}%
                        </div>
                        <div className="text-xs font-black text-slate-700 tabular-nums mt-0.5">
                          {fmtPLN(price)}
                        </div>
                        <div className="text-[8px] text-slate-400 font-medium">
                          PLN/mc
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Similar Cars Discovery Results */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50/50 to-purple-50/50 border border-indigo-100 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider flex items-center gap-2">
                      Podobne pojazdy w tym budżecie
                      <span className="px-1.5 py-0.5 text-[8px] font-bold bg-purple-600 text-white rounded shadow-sm">
                        GŁĘBOKIE (AI CECHY)
                      </span>
                    </h4>
                    {loadingSimilar && <Loader2 className="w-3 h-3 animate-spin text-indigo-400" />}
                  </div>

                {similarCars.length > 0 ? (
                  <div className="space-y-2">
                    {similarCars.map((car) => (
                      <div
                        key={car.vehicle_id}
                        className="p-3 bg-white/80 border border-white rounded-lg flex items-center justify-between shadow-sm hover:shadow transition-all"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold text-slate-700 uppercase bg-slate-100 px-1.5 py-0.5 rounded">
                              {car.brand}
                            </span>
                            <span className="text-xs font-bold text-slate-800 truncate">
                              {car.model}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-400 truncate mt-0.5">
                            {car.version_name} • {car.body_type}
                          </div>
                          <div className="flex items-center gap-1.5 mt-1">
                            <span className="text-[9px] font-medium px-1.5 py-0.5 rounded text-purple-600 bg-purple-50">
                              Zgodność cech: {Math.round(car.score || 0)}%
                            </span>
                            <span className="text-[9px] text-slate-400 font-medium italic">
                              AI Similarity Search
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-1 text-[9px] text-slate-500 font-medium">
                            <span className="px-1.5 py-0.5 bg-slate-100 rounded">
                              {result?.months || months} mc / {(result?.totalKm || Number(totalKm)).toLocaleString("pl-PL")} km
                            </span>
                            <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded whitespace-nowrap">
                              Marża: 0%
                            </span>
                          </div>
                        </div>
                        <div className="text-right ml-4">
                          <div className="text-xs font-black text-indigo-600 tabular-nums">
                            {fmtPLN(car.monthly_price_net)}
                          </div>
                          <div className="text-[8px] text-slate-400 font-bold uppercase tracking-tighter">
                            PLN/mc
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : !loadingSimilar ? (
                  <div className="text-center py-4 bg-white/40 rounded-lg border border-dashed border-indigo-200">
                    <p className="text-[10px] text-slate-400">
                      Brak sklasyfikowanych alternatyw w tym przedziale cenowym.
                    </p>
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-6">
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-300" />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

