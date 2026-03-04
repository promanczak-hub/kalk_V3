import type { FleetVehicleView } from "../../types";

interface VehicleEquipmentCardProps {
  vehicle: FleetVehicleView;
}

const EMPTY = "—";

function formatPrice(priceStr: string): string {
  if (!priceStr || priceStr === "Brak" || priceStr === "-") return EMPTY;
  return priceStr;
}

export function VehicleEquipmentCard({ vehicle }: VehicleEquipmentCardProps) {
  const paidOptions = vehicle.paid_options ?? [];
  const standardEquipment = vehicle.standard_equipment ?? [];

  const hasPaidOptions = paidOptions.length > 0;
  const hasStandardEquipment = standardEquipment.length > 0;

  if (!hasPaidOptions && !hasStandardEquipment) {
    return null;
  }

  return (
    <div className="border border-slate-200 rounded bg-white">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Wyposażenie i opcje
        </h4>
      </div>

      <div className="p-5 space-y-6">
        {/* Paid options table */}
        {hasPaidOptions && (
          <div>
            <h5 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
              Opcje płatne ({paidOptions.length})
            </h5>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-slate-200">
                    <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400 py-2 pr-4">
                      Nazwa
                    </th>
                    <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400 py-2 pr-4">
                      Kategoria
                    </th>
                    <th className="text-right text-[10px] font-semibold uppercase tracking-wider text-slate-400 py-2">
                      Cena
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paidOptions.map((opt, idx) => (
                    <tr
                      key={`${opt.name}-${idx}`}
                      className={`border-b border-slate-100 last:border-b-0 ${
                        idx % 2 === 1 ? "bg-slate-50/50" : ""
                      }`}
                    >
                      <td className="py-2 pr-4 text-slate-700">{opt.name}</td>
                      <td className="py-2 pr-4 text-slate-500 text-xs">
                        {opt.category ?? EMPTY}
                      </td>
                      <td className="py-2 text-right text-slate-800 font-medium tabular-nums">
                        {formatPrice(opt.price)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Options total */}
            {vehicle.options_price &&
              vehicle.options_price !== "Brak" && (
                <div className="mt-3 pt-3 border-t border-slate-200 flex justify-between items-baseline">
                  <span className="text-xs text-slate-400">
                    Suma opcji dodatkowych
                  </span>
                  <span className="text-sm font-semibold text-slate-800 tabular-nums">
                    {vehicle.options_price}
                  </span>
                </div>
              )}
          </div>
        )}

        {/* Standard equipment */}
        {hasStandardEquipment && (
          <div>
            <h5 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
              Wyposażenie standardowe ({standardEquipment.length})
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
              {standardEquipment.map((item, idx) => (
                <div
                  key={`${item}-${idx}`}
                  className="py-1 text-xs text-slate-600 border-b border-slate-50"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
