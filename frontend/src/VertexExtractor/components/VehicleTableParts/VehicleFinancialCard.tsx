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

  // Calculate sum of individual options to compare with optionsPrice
  const factoryOpts =
    (vehicle.synthesis_data?.factory_options as Array<{
      price_net?: number;
    }>) || [];
  const serviceOpts =
    (vehicle.synthesis_data?.service_options as Array<{
      price_net?: number;
    }>) || [];
  const extractedOptionsSum =
    factoryOpts.reduce((acc, opt) => acc + (Number(opt?.price_net) || 0), 0) +
    serviceOpts.reduce((acc, opt) => acc + (Number(opt?.price_net) || 0), 0);

  // We consider a discrepancy if the difference is greater than 10 PLN (to account for minor rounding)
  const hasOptionsDiscrepancy =
    optionsPrice > 0 &&
    extractedOptionsSum > 0 &&
    Math.abs(optionsPrice - extractedOptionsSum) > 10;

  const breakdownRows: {
    id: string;
    label: React.ReactNode;
    value: string;
    bold?: boolean;
    negative?: boolean;
  }[] = [
    {
      id: "base",
      label: "Cena bazowa",
      value: basePrice > 0 ? fmtPLN(basePrice) + suffix : "—",
    },
    {
      id: "options",
      label: (
        <div className="flex flex-col">
          <span>Opcje fabryczne (Wyrzynarka)</span>
          {hasOptionsDiscrepancy && (
            <span className="text-[10px] text-amber-600 font-medium leading-tight mt-0.5">
              Twarda suma opcji na liście wynosi {fmtPLN(extractedOptionsSum)}. Silnik użyje tej wartości!
            </span>
          )}
        </div>
      ),
      value: optionsPrice > 0 ? fmtPLN(optionsPrice) + suffix : "—",
    },
  ];

  if (discountAmount > 0) {
    breakdownRows.push({
      id: "discount",
      label: "Rabat",
      value: `(${fmtPLN(discountAmount)}${suffix})`,
      negative: true,
    });
  }

  breakdownRows.push({
    id: "final",
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
        {/* Price validation summary & warnings */}
        {validation && (!validation.is_valid || validation.summary) && (
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
                  key={row.id}
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
