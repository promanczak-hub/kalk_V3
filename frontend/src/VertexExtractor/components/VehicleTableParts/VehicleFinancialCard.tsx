import type { FleetVehicleView, PriceValidation } from "../../types";
import { parsePriceToNumber } from "./PriceDualFormat";
import { PriceValidationBanner } from "./PriceValidationBanner";

interface VehicleFinancialCardProps {
  vehicle: FleetVehicleView;
}

function fmtPLN(value: number): string {
  if (value === 0) return "—";
  return (
    value.toLocaleString("pl-PL", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }) + " PLN"
  );
}

function detectSuffix(priceStr?: string | null): string {
  if (!priceStr) return "";
  const lower = priceStr.toLowerCase();
  if (lower.includes("netto")) return " netto";
  if (lower.includes("brutto")) return " brutto";
  return "";
}

interface MetricProps {
  label: string;
  value: string;
  accent?: boolean;
}

function MetricTile({ label, value, accent }: MetricProps) {
  return (
    <div className="border border-slate-200 rounded p-4 flex flex-col">
      <span className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">
        {label}
      </span>
      <span
        className={`text-lg font-semibold tabular-nums ${
          accent ? "text-slate-900" : "text-slate-700"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

export function VehicleFinancialCard({ vehicle }: VehicleFinancialCardProps) {
  const basePrice = parsePriceToNumber(vehicle.base_price);
  const optionsPrice = parsePriceToNumber(vehicle.options_price);
  const finalPrice = parsePriceToNumber(vehicle.final_price_pln);
  const suffix = detectSuffix(vehicle.base_price);

  const catalogPrice = basePrice + optionsPrice;
  const discountPct = vehicle.suggested_discount_pct ?? 0;

  const effectiveFinal =
    finalPrice > 0
      ? finalPrice
      : discountPct > 0
        ? catalogPrice * (1 - discountPct / 100)
        : catalogPrice;

  const discountAmount = catalogPrice - effectiveFinal;

  // Check if we have any financial data at all
  if (basePrice === 0 && finalPrice === 0) {
    return null;
  }

  // Extract validation flags from synthesis_data.card_summary._validation
  const cardSummary = vehicle.synthesis_data?.card_summary as
    | Record<string, unknown>
    | undefined;
  const validation = cardSummary?._validation as PriceValidation | undefined;

  const breakdownRows: { label: string; value: string; bold?: boolean; negative?: boolean }[] = [
    {
      label: "Cena bazowa",
      value: basePrice > 0 ? fmtPLN(basePrice) + suffix : "—",
    },
    {
      label: "Opcje fabryczne",
      value: optionsPrice > 0 ? fmtPLN(optionsPrice) + suffix : "—",
    },
  ];

  if (discountAmount > 0) {
    breakdownRows.push({
      label: "Rabat",
      value: `(${fmtPLN(discountAmount)}${suffix})`,
      negative: true,
    });
  }

  breakdownRows.push({
    label: "Cena końcowa",
    value: fmtPLN(effectiveFinal) + suffix,
    bold: true,
  });

  return (
    <div className="border border-slate-200 rounded bg-white">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Analiza finansowa
        </h4>
      </div>

      <div className="p-5 space-y-5">
        {/* Price validation warnings */}
        {validation && !validation.is_valid && (
          <PriceValidationBanner validation={validation} />
        )}

        {/* Metric tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <MetricTile
            label="Cena katalogowa"
            value={catalogPrice > 0 ? fmtPLN(catalogPrice) + suffix : "—"}
            accent
          />
          <MetricTile
            label="Rabat flotowy"
            value={discountPct > 0 ? `${discountPct}%` : "Brak"}
          />
          <MetricTile
            label="Cena po rabacie"
            value={effectiveFinal > 0 ? fmtPLN(effectiveFinal) + suffix : "—"}
            accent
          />
        </div>

        {/* Breakdown table */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
            Rozkład ceny
          </h5>
          <table className="w-full text-sm">
            <tbody>
              {breakdownRows.map((row, idx) => (
                <tr
                  key={row.label}
                  className={
                    row.bold
                      ? "border-t-2 border-slate-300"
                      : idx < breakdownRows.length - 1
                        ? "border-b border-slate-100"
                        : ""
                  }
                >
                  <td
                    className={`py-2.5 ${
                      row.bold
                        ? "text-sm font-semibold text-slate-900"
                        : "text-xs text-slate-500"
                    }`}
                  >
                    {row.label}
                  </td>
                  <td
                    className={`py-2.5 text-right tabular-nums ${
                      row.bold
                        ? "text-sm font-semibold text-slate-900"
                        : row.negative
                          ? "text-sm text-slate-500"
                          : "text-sm font-medium text-slate-700"
                    }`}
                  >
                    {row.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
