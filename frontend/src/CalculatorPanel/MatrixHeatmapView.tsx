import { useMemo, useState } from "react";
import { Star, Grid3X3, List, FileCode2, Loader2, RotateCcw, Settings } from "lucide-react";
import type { MiniMatrixCell } from "../VertexExtractor/components/VehicleTableParts/decision-center/decision-center.types";
import type { CellOverrides } from "../VertexExtractor/components/VehicleTableParts/calculations/useVehicleCalculations";

/* ── Types ───────────────────────────────────────────────────────────── */

interface MatrixHeatmapViewProps {
  cells: MiniMatrixCell[];
  mileageMode?: "annual" | "contract";
  onCellClick?: (cell: MiniMatrixCell) => void;
  onShowTrace?: (cell: MiniMatrixCell) => void;
  isFetchingTrace?: boolean;
  getOverrides?: (months: number) => CellOverrides;
  onOverridesChange?: (months: number, overrides: Partial<CellOverrides>) => void;
  onRecalculate?: (months: number) => void;
  onReset?: (months: number) => void;
  modifiedCells?: Set<number>;
  recalculatingCell?: number | null;
  onTargetPriceRecalculate?: (cell: MiniMatrixCell, targetPriceNet: number) => void;
  onAddToCart?: (cell: MiniMatrixCell) => void;
}

/* ── Margin Tier System ─────────────────────────────────────────────── */

interface MarginTier {
  label: string;
  heatBg: string;
  heatColor: string;
  badgeBg: string;
  badgeText: string;
}

function getMarginTier(pct: number): MarginTier {
  if (pct < 0) return {
    label: "< 0%", heatBg: "#ffffff", heatColor: "#dc2626",
    badgeBg: "bg-red-100", badgeText: "text-red-800"
  };
  if (pct < 8) return {
    label: "0–8%", heatBg: "#ffffff", heatColor: "#ea580c",
    badgeBg: "bg-orange-100", badgeText: "text-orange-800"
  };
  if (pct < 12) return {
    label: "8–12%", heatBg: "#ffffff", heatColor: "#ca8a04",
    badgeBg: "bg-yellow-100", badgeText: "text-yellow-800"
  };
  if (pct < 15) return {
    label: "12–15%", heatBg: "#ffffff", heatColor: "#16a34a",
    badgeBg: "bg-green-100", badgeText: "text-green-800"
  };
  if (pct < 20) return {
    label: "15–20%", heatBg: "#ffffff", heatColor: "#059669",
    badgeBg: "bg-emerald-100", badgeText: "text-emerald-800"
  };
  return {
    label: "> 20%", heatBg: "#ffffff", heatColor: "#0891b2",
    badgeBg: "bg-cyan-100", badgeText: "text-cyan-800"
  };
}

function fmtPLN(v: number): string {
  return v.toLocaleString("pl-PL", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

const VAT_MULTIPLIER = 1.23;

function fmtPLN2(v: number): string {
  return v.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface V1SummaryRow {
  label: string;
  kind: "money" | "percent" | "plain";
  net: number | string;
  gross?: number | string;
  emphasize?: boolean;
}

function buildV1SummaryRows(cell: MiniMatrixCell): V1SummaryRow[] {
  const wrPctBase =
    cell.CenaKatalogowaNetto > 0
      ? (cell.WR / cell.CenaKatalogowaNetto) * 100
      : 0;

  return [
    { label: "Stawka laczna", kind: "money", net: cell.LacznaStawka, emphasize: true },
    { label: "Czynsz inicjalny (%)", kind: "percent", net: cell.CzynszInicjalnyProcent ?? 0 },
    { label: "Czynsz inicjalny (kwota)", kind: "money", net: cell.CzynszInicjalnyNetto ?? 0 },
    { label: "Czynsz finansowy", kind: "money", net: cell.CzynszFinansowy },
    { label: "Czynsz techniczny", kind: "money", net: cell.CzynszTechniczny },
    { label: "Ubezpieczenie", kind: "money", net: cell.Ubezpieczenie },
    { label: "Serwis", kind: "money", net: cell.Serwis },
    { label: "Opony", kind: "money", net: cell.Opony },
    { label: "Samochod zastepczy", kind: "money", net: cell.SamochodZastepczy },
    { label: "Koszty dodatkowe (admin.: rej, sprzedaz, GSM)", kind: "money", net: cell.Admin },
    { label: "Ilosc opon na kontrakt", kind: "plain", net: Number(cell.IloscOpon || 0).toFixed(2) },
    { label: "Cena zakupu (BUDZET)", kind: "money", net: cell.CenaZakupu, emphasize: true },
    { label: "Cena jednego kompletu opon", kind: "money", net: cell.Koszt1KplOpon || cell.Cena1KompletOpon },
    { label: "Cena zakupu bez opon", kind: "money", net: cell.CenaZakupuBezOpon },
    { label: "  - Opcje serwisowe (CAPEX)", kind: "money", net: cell.OpcjeSerwisoweSumaNetto },
    { label: "  - Urzadzenia i instalacja GSM (CAPEX)", kind: "money", net: cell.GsmCapexNetto },
    { label: "Cena zakupu opcji fabrycznych", kind: "money", net: cell.CenaZakupuBezOponIOpcjiSerwisowych },
    {
      label: "Cena zakupu opcji fabrycznych bez p. serwisowego",
      kind: "money",
      net: cell.CenaZakupuBezOponIOpcjiSerwisowychIPakietu,
    },
    { label: "WR", kind: "money", net: cell.WR, emphasize: true },
    { label: "WR % (od ceny zakupu z opcjami fabrycznymi)", kind: "percent", net: wrPctBase },
    { label: "WR dla LO", kind: "money", net: cell.WRdlaLO },
    { label: "Koszt dzienny", kind: "money", net: cell.KosztDzienny, emphasize: true },
    { label: "Przychod", kind: "money", net: cell.Przychod },
    { label: "Koszty ogolem", kind: "money", net: cell.KosztyOgolem },
    { label: "Marza na kontrakcie", kind: "money", net: cell.MarzaNaKontrakcie, emphasize: true },
  ];
}

function renderV1CellValue(
  row: V1SummaryRow,
  mode: "net" | "gross",
): string {
  if (row.kind === "plain") {
    return mode === "net" ? String(row.net) : "-";
  }

  if (row.kind === "percent") {
    if (mode === "gross") return "-";
    const val = typeof row.net === "number" ? row.net : parseFloat(String(row.net));
    return `${Number.isFinite(val) ? val.toFixed(2) : "0.00"}%`;
  }

  const numericNet =
    typeof row.net === "number" ? row.net : parseFloat(String(row.net).replace(",", "."));
  const netVal = Number.isFinite(numericNet) ? numericNet : 0;
  const out = mode === "gross" ? netVal * VAT_MULTIPLIER : netVal;
  return `${fmtPLN2(out)} PLN`;
}

/* ── Legend tiers ──────────────────────────────────────────────────── */

const LEGEND_TIERS = [
  { pct: -1, label: "< 0%" },
  { pct: 4, label: "0–8%" },
  { pct: 10, label: "8–12%" },
  { pct: 13, label: "12–15%" },
  { pct: 17, label: "15–20%" },
  { pct: 25, label: "> 20%" },
];

/* ── Main Component ────────────────────────────────────────────────── */

export function MatrixHeatmapView({
  cells,
  mileageMode = "annual",
  onCellClick,
  onShowTrace,
  isFetchingTrace,
  getOverrides,
  onOverridesChange,
  onRecalculate,
  onReset,
  modifiedCells,
  recalculatingCell,
  onTargetPriceRecalculate,
  onAddToCart
}: MatrixHeatmapViewProps) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [targetPriceInputs, setTargetPriceInputs] = useState<Record<number, string>>({});
  const [addedToCartCells, setAddedToCartCells] = useState<Set<string>>(new Set());

  const getContractKm = (c: MiniMatrixCell): number => c.PrzebiegKontrakt ?? Math.round((c.Okres / 12) * c.Przebieg);

  // Build axes from actual cell data
  const { months, kmValues, cellMap, bestKey } = useMemo(() => {
    const monthsSet = new Set<number>();
    const kmSet = new Set<number>();
    const map = new Map<string, MiniMatrixCell>();


    const axisKmForCell = (c: MiniMatrixCell): number => {
      if (mileageMode === "contract") {
        return getContractKm(c);
      }
      return c.Przebieg;
    };

    for (const c of cells) {
      const axisKm = axisKmForCell(c);
      monthsSet.add(c.Okres);
      kmSet.add(axisKm);
      map.set(`${c.Okres}_${axisKm}`, c);
    }

    const sortedMonths = [...monthsSet].sort((a, b) => a - b);
    const sortedKm = [...kmSet].sort((a, b) => a - b);

    // Find best cell (highest margin)
    let best: MiniMatrixCell | null = null;
    let bestMargin = -Infinity;
    for (const c of cells) {
      const m = c.KosztyLaczneMC > 0 ? ((c.LacznaStawka - c.KosztyLaczneMC) / c.LacznaStawka) * 100 : 0;
      if (m > bestMargin) {
        bestMargin = m;
        best = c;
      }
    }
    const bk = best ? `${best.Okres}_${axisKmForCell(best)}` : null;

    return { months: sortedMonths, kmValues: sortedKm, cellMap: map, bestKey: bk };
  }, [cells, mileageMode]);

  if (cells.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-slate-400">
        Brak danych do wyświetlenia
      </div>
    );
  }

  return (
    <div>
      {/* Matrix table */}
      <div className="overflow-x-auto border border-slate-200 bg-white rounded-lg shadow-sm">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {/* Corner cell */}
              <th className="py-2.5 px-3 text-left w-24">
                <div className="text-[9px] font-bold uppercase text-slate-400 tracking-wider">
                  Okres / km
                </div>
              </th>
              {kmValues.map((km) => (
                <th key={km} className="py-2.5 text-center">
                  <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                    {(km / 1000).toFixed(0)}k
                  </div>
                  <div className="text-[8px] text-slate-300 font-medium">{mileageMode === "contract" ? "km/kontrakt" : "km/rok"}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {months.map((m) => (
              <tr key={m}>
                {/* Row header */}
                <td className="py-2 px-3 border-b border-r border-slate-100 align-middle">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <div className="text-xs font-bold text-slate-600">{m} mc</div>
                    {modifiedCells?.has(m) && <span title="Zmodyfikowane parametry"><Settings className="w-3 h-3 text-blue-500" /></span>}
                  </div>
                  <div className="text-[9px] text-slate-400">
                    {m === 12 ? "1 rok" : m === 24 ? "2 lata" : m === 36 ? "3 lata" : m === 48 ? "4 lata" : m === 60 ? "5 lat" : m === 72 ? "6 lat" : m === 84 ? "7 lat" : `${(m / 12).toFixed(1)} lat`}
                  </div>
                </td>

                {/* Data cells */}
                {kmValues.map((km) => {
                  const key = `${m}_${km}`;
                  const cell = cellMap.get(key);

                  if (!cell) {
                    return (
                      <td key={km} className="text-center p-2 border-b border-slate-100">
                        <div className="p-3 bg-slate-50 border border-dashed border-slate-300 rounded-md">
                          <span className="text-xs text-slate-300">—</span>
                        </div>
                      </td>
                    );
                  }

                  const marginPct = cell.KosztyLaczneMC > 0
                    ? ((cell.LacznaStawka - cell.KosztyLaczneMC) / cell.LacznaStawka) * 100
                    : 0;
                  const tier = getMarginTier(marginPct);
                  const isSelected = selectedKey === key;
                  const isBest = bestKey === key;
                  const totalKmK = (getContractKm(cell) / 1000).toFixed(0);
                  const annualKmK = (cell.Przebieg / 1000).toFixed(0);
                  const kmCaption = mileageMode === "contract"
                    ? `${totalKmK}k km/kontrakt`
                    : `${annualKmK}k km/rok`;

                  return (
                    <td key={km} className="text-center p-2 border-b border-slate-100">
                      <button
                        onClick={() => {
                          setSelectedKey(isSelected ? null : key);
                          if (onCellClick && !isSelected) onCellClick(cell);
                        }}
                        className={`
                          relative w-full rounded-md p-3 transition-all duration-150
                          cursor-pointer group min-w-[100px] bg-white
                          ${isSelected
                            ? "shadow-md ring-2 ring-blue-500/30"
                            : "shadow-sm hover:shadow-md hover:-translate-y-0.5"
                          }
                        `}
                        style={{
                          borderWidth: "1px",
                          borderStyle: "solid",
                          borderColor: isSelected ? tier.heatColor : `${tier.heatColor}40`,
                        }}
                      >
                        {/* Best cell star */}
                        {isBest && (
                          <div className="absolute top-1 right-1 z-10">
                            <Star className="w-3 h-3" style={{ color: tier.heatColor, fill: tier.heatColor }} />
                          </div>
                        )}

                        {/* Price */}
                        <div className="text-[13px] font-bold tabular-nums leading-tight text-slate-800">
                          {fmtPLN(cell.LacznaStawka)}
                        </div>

                        {/* Total km */}
                        <div className="text-[9px] text-slate-500 mt-1">
                          {kmCaption}
                        </div>

                        {/* Margin badge removed for cleaner heatmap view */}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3 ml-1">
        <span className="text-[9px] text-slate-400 font-semibold mr-1 uppercase">Marża:</span>
        {LEGEND_TIERS.map((t) => {
          const tier = getMarginTier(t.pct);
          return (
            <span
              key={t.label}
              className={`text-[9px] font-semibold px-2 py-0.5 rounded-sm ${tier.badgeBg} ${tier.badgeText}`}
            >
              {t.label}
            </span>
          );
        })}
      </div>

      {/* Selected cell detail */}
      {selectedKey && (() => {
        const cell = cellMap.get(selectedKey);
        if (!cell) return null;
        const marginPct = cell.KosztyLaczneMC > 0
          ? ((cell.LacznaStawka - cell.KosztyLaczneMC) / cell.LacznaStawka) * 100
          : 0;
        const tier = getMarginTier(marginPct);
        const v1Rows = buildV1SummaryRows(cell);

        return (
          <div
            className="mt-3 p-4 rounded-lg border bg-white shadow-md animate-in fade-in slide-in-from-top-2 duration-200"
            style={{ borderColor: tier.heatColor, borderLeftWidth: "4px" }}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full ${tier.badgeBg} ${tier.badgeText}`}
                >
                  {mileageMode === "contract" ? `${cell.Okres} mc / ${(getContractKm(cell) / 1000).toFixed(0)}k km/kontrakt` : `${cell.Okres} mc / ${(cell.Przebieg / 1000).toFixed(0)}k km/rok`}
                </span>
                <span className="text-[10px] text-slate-400">
                  {mileageMode === "contract"
                    ? `${(cell.Przebieg / 1000).toFixed(0)}k km/rok`
                    : `${(getContractKm(cell) / 1000).toFixed(0)}k km lacznie`}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {/* Korekta WR (per-cell) — dwa powiązane inputy: netto + brutto */}
                {getOverrides && onOverridesChange && onRecalculate && (() => {
                  const ov = getOverrides(cell.Okres);
                  const netto = ov.manual_wr_correction ?? 0;
                  const brutto = netto * VAT_MULTIPLIER;
                  const isThisRecalcing = recalculatingCell === cell.Okres;
                  const showReset = netto !== 0 || modifiedCells?.has(cell.Okres);
                  return (
                    <div className="inline-flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-md px-2 py-1">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Korekta WR:</span>
                      <input
                        type="number"
                        step={500}
                        value={netto === 0 ? "" : netto}
                        onChange={(e) => {
                          const v = parseFloat(e.target.value);
                          onOverridesChange(cell.Okres, { manual_wr_correction: isNaN(v) ? 0 : v });
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") onRecalculate(cell.Okres);
                        }}
                        className="w-20 text-xs p-1 border border-slate-300 rounded text-right outline-none focus:ring-1 focus:ring-blue-400 bg-white tabular-nums font-mono"
                        placeholder="0"
                      />
                      <span className="text-[9px] text-slate-400">PLN netto</span>
                      <input
                        type="number"
                        step={500}
                        value={brutto === 0 ? "" : brutto.toFixed(2)}
                        onChange={(e) => {
                          const v = parseFloat(e.target.value);
                          const nettoFromBrutto = isNaN(v) ? 0 : parseFloat((v / VAT_MULTIPLIER).toFixed(2));
                          onOverridesChange(cell.Okres, { manual_wr_correction: nettoFromBrutto });
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") onRecalculate(cell.Okres);
                        }}
                        className="w-20 text-xs p-1 border border-slate-300 rounded text-right outline-none focus:ring-1 focus:ring-blue-400 bg-white tabular-nums font-mono"
                        placeholder="0"
                      />
                      <span className="text-[9px] text-slate-400">PLN brutto</span>
                      <button
                        onClick={() => onRecalculate(cell.Okres)}
                        disabled={isThisRecalcing}
                        className="ml-1 px-2.5 py-1 text-[11px] font-bold bg-blue-600 text-white rounded hover:bg-blue-700 shadow-sm transition-all disabled:opacity-50"
                      >
                        {isThisRecalcing ? "..." : "Przelicz"}
                      </button>
                      {showReset && onReset && (
                        <button
                          onClick={() => onReset(cell.Okres)}
                          className="p-1 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
                          title="Resetuj korektę"
                        >
                          <RotateCcw className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  );
                })()}
                {/* Dostosuj stawkę (Goal Seek per-cell) */}
                {onTargetPriceRecalculate && (() => {
                  const isThisRecalcing = recalculatingCell === cell.Okres;
                  const inputVal = targetPriceInputs[cell.Okres] ?? "";
                  return (
                    <div className="inline-flex items-center gap-1.5 bg-violet-50 border border-violet-200 rounded-md px-2 py-1">
                      <span className="text-[10px] font-bold text-violet-700 uppercase tracking-wider">Dostosuj stawkę:</span>
                      <input
                        type="number"
                        step={50}
                        value={inputVal}
                        onChange={(e) => setTargetPriceInputs(prev => ({ ...prev, [cell.Okres]: e.target.value }))}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            const v = parseFloat(inputVal);
                            if (!isNaN(v) && v > 0) onTargetPriceRecalculate(cell, v);
                          }
                        }}
                        placeholder={`np. ${Math.round(cell.LacznaStawka)}`}
                        className="w-24 text-xs p-1 border border-violet-300 rounded text-right outline-none focus:ring-1 focus:ring-violet-400 bg-white tabular-nums font-mono"
                      />
                      <span className="text-[9px] text-violet-400">PLN netto</span>
                      <button
                        onClick={() => {
                          const v = parseFloat(inputVal);
                          if (!isNaN(v) && v > 0) onTargetPriceRecalculate(cell, v);
                        }}
                        disabled={isThisRecalcing || !inputVal}
                        className="ml-1 px-2.5 py-1 text-[11px] font-bold bg-violet-600 text-white rounded hover:bg-violet-700 shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                        title="Wylicz wymaganą marżę dla docelowej raty (Goal Seek)"
                      >
                        {isThisRecalcing ? "..." : "⚡ Goal Seek"}
                      </button>
                    </div>
                  );
                })()}
                {onShowTrace && (
                  <button
                    onClick={() => onShowTrace(cell)}
                    disabled={isFetchingTrace}
                    className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-colors bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 disabled:opacity-50"
                  >
                    {isFetchingTrace ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileCode2 className="w-3 h-3" />}
                    Ślad Przeliczeń
                  </button>
                )}
                {onAddToCart && (() => {
                  const cartKey = `${cell.Okres}_${getContractKm(cell)}`;
                  const added = addedToCartCells.has(cartKey);
                  return (
                    <button
                      onClick={() => {
                        onAddToCart(cell);
                        setAddedToCartCells(prev => new Set([...prev, cartKey]));
                        setTimeout(() => {
                          setAddedToCartCells(prev => {
                            const next = new Set(prev);
                            next.delete(cartKey);
                            return next;
                          });
                        }, 2000);
                      }}
                      className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-md border transition-all ${
                        added
                          ? "bg-emerald-500 text-white border-emerald-500 shadow-md"
                          : "bg-orange-500 text-white border-orange-500 hover:bg-orange-600 shadow-sm hover:shadow"
                      }`}
                      title="Dodaj ten wariant do koszyka ofertowego"
                    >
                      {added ? "✓ Dodano!" : "+ Do koszyka"}
                    </button>
                  );
                })()}
                <button
                  onClick={() => setSelectedKey(null)}
                  className="text-[10px] text-slate-400 hover:text-slate-600 transition-colors"
                >
                  ✕ Zamknij
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <DetailItem label="Rata netto/mc" value={`${fmtPLN(cell.LacznaStawka)} PLN`} highlight />
              <DetailItem label="Koszt bazowy" value={`${fmtPLN(cell.KosztyLaczneMC)} PLN`} />
              <DetailItem label="Marża %"
                value={`${marginPct.toFixed(1)}%`}
                color={tier.heatColor}
              />
              <DetailItem label="Marża PLN/mc"
                value={`${fmtPLN(cell.LacznaStawka - cell.KosztyLaczneMC)} PLN`}
              />
            </div>

            {/* Breakdown */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3 pt-3 border-t border-slate-200">
              <BreakdownItem label="Finanse" value={cell.CzynszFinansowy} />
              <BreakdownItem label="Serwis" value={cell.Serwis} />
              <BreakdownItem label="Opony" value={cell.Opony} />
              <BreakdownItem label="Ubezp." value={cell.Ubezpieczenie} />
              <BreakdownItem label="Inne" value={cell.SamochodZastepczy + cell.Admin} />
            </div>

            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Podsumowanie V1 (netto/brutto)
              </div>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-[11px] border border-slate-200 rounded-md overflow-hidden">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="text-left px-2 py-1.5 font-bold text-slate-500 uppercase tracking-wider">Pozycja</th>
                      <th className="text-right px-2 py-1.5 font-bold text-slate-500 uppercase tracking-wider">Netto</th>
                      <th className="text-right px-2 py-1.5 font-bold text-slate-500 uppercase tracking-wider">Brutto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {v1Rows.map((row) => (
                      <tr key={row.label} className="border-t border-slate-100">
                        <td className={`px-2 py-1.5 ${row.emphasize ? "font-bold text-slate-800" : "text-slate-600"}`}>{row.label}</td>
                        <td className={`px-2 py-1.5 text-right tabular-nums ${row.emphasize ? "font-bold text-slate-900" : "text-slate-700"}`}>
                          {renderV1CellValue(row, "net")}
                        </td>
                        <td className={`px-2 py-1.5 text-right tabular-nums ${row.emphasize ? "font-bold text-slate-900" : "text-slate-700"}`}>
                          {renderV1CellValue(row, "gross")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}

/* ── Sub-components ─────────────────────────────────────────────────── */

function DetailItem({ label, value, highlight, color }: {
  label: string; value: string; highlight?: boolean; color?: string;
}) {
  return (
    <div>
      <div className="text-[9px] font-bold uppercase text-slate-400 tracking-wider">{label}</div>
      <div
        className={`text-sm font-bold tabular-nums ${highlight ? "text-blue-700" : ""}`}
        style={color ? { color } : undefined}
      >
        {value}
      </div>
    </div>
  );
}

function BreakdownItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center p-2 rounded-md bg-slate-50 border border-slate-200">
      <div className="text-[8px] font-bold uppercase text-slate-400 tracking-wider">{label}</div>
      <div className="text-[11px] font-bold text-slate-700 tabular-nums">{fmtPLN(value)}</div>
    </div>
  );
}

/* ── View Toggle Button ────────────────────────────────────────────── */

export function MatrixViewToggle({
  view,
  onViewChange,
}: {
  view: "cards" | "heatmap";
  onViewChange: (v: "cards" | "heatmap") => void;
}) {
  return (
    <div className="inline-flex items-center rounded-md border border-slate-300 bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => onViewChange("cards")}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
          view === "cards"
            ? "bg-blue-600 text-white"
            : "text-slate-600 hover:bg-slate-50"
        }`}
      >
        <List className="w-3.5 h-3.5" />
        Karty
      </button>
      <button
        onClick={() => onViewChange("heatmap")}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
          view === "heatmap"
            ? "bg-blue-600 text-white"
            : "text-slate-600 hover:bg-slate-50"
        }`}
      >
        <Grid3X3 className="w-3.5 h-3.5" />
        Matryca
      </button>
    </div>
  );
}
