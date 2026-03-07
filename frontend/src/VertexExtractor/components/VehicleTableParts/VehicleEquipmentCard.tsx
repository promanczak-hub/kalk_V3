import type { FleetVehicleView } from "../../types";
import { NetGrossInput } from "./NetGrossInput";

interface VehicleEquipmentCardProps {
  vehicle: FleetVehicleView;
  // Factory options CRUD
  customFactoryOptions: { id: string; name: string; price_net: number; category: string; no_discount: boolean }[];
  handleUpdateFactoryOptionName: (id: string, newName: string) => void;
  handleUpdateFactoryOptionPrice: (id: string, newVal: number) => void;
  handleUpdateFactoryOptionNoDiscount: (id: string, noDiscount: boolean) => void;
  handleRemoveFactoryOption: (id: string) => void;
  handleAddManualFactoryOption: () => void;
  activeDiscountPct: number;
}

const EMPTY = "—";

const VAT = 1.23;

function fmtPLN(value: number): string {
  if (value === 0) return EMPTY;
  return new Intl.NumberFormat("pl-PL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function VehicleEquipmentCard({
  vehicle,
  customFactoryOptions,
  handleUpdateFactoryOptionName,
  handleUpdateFactoryOptionPrice,
  handleUpdateFactoryOptionNoDiscount,
  handleRemoveFactoryOption,
  handleAddManualFactoryOption,
  activeDiscountPct,
}: VehicleEquipmentCardProps) {
  const standardEquipment = vehicle.standard_equipment ?? [];
  const hasStandardEquipment = standardEquipment.length > 0;

  // Calculate total — options are always stored as netto (price_net),
  // so brutto is always netto × VAT regardless of base_price domain
  const totalNet = customFactoryOptions.reduce((sum, opt) => sum + opt.price_net, 0);
  const totalBrutto = totalNet * VAT;

  return (
    <div id="factory-options-section" className="border border-slate-200 rounded bg-white">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Opcje fabryczne
          {customFactoryOptions.length > 0 && (
            <span className="ml-2 text-slate-400">({customFactoryOptions.length})</span>
          )}
        </h4>
      </div>

      <div className="p-5 space-y-4">
        {/* Editable options list */}
        {customFactoryOptions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left text-xs font-semibold uppercase tracking-wider text-slate-400 py-2 pr-4">
                    Nazwa
                  </th>
                  <th className="text-right text-xs font-semibold uppercase tracking-wider text-slate-400 py-2 pr-2 w-40">
                    Netto
                  </th>
                  <th className="text-center text-xs font-semibold uppercase tracking-wider text-slate-400 py-2 w-6">
                  </th>
                  <th className="text-right text-xs font-semibold uppercase tracking-wider text-slate-400 py-2 pr-2 w-40">
                    Brutto
                  </th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody>
                {customFactoryOptions.map((opt, idx) => (
                  <tr
                    key={opt.id}
                    className={`border-b border-slate-100 last:border-b-0 ${
                      idx % 2 === 1 ? "bg-slate-50/50" : ""
                    }`}
                  >
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          className="flex-1 px-2 py-1.5 border border-slate-200 rounded text-slate-700 font-medium text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                          value={opt.name}
                          onChange={(e) => handleUpdateFactoryOptionName(opt.id, e.target.value)}
                          placeholder="Nazwa opcji"
                        />
                        {opt.no_discount && (
                          <span className="shrink-0 px-1.5 py-0.5 text-[9px] font-bold uppercase rounded bg-amber-50 text-amber-700 border border-amber-200">
                            Nierabatowana
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2" colSpan={3}>
                      <NetGrossInput
                        netValue={opt.price_net}
                        onChangeNet={(newVal) => handleUpdateFactoryOptionPrice(opt.id, newVal)}
                      />
                    </td>
                    <td className="py-2 text-center">
                      <div className="flex items-center gap-1">
                        <label
                          className="relative inline-flex items-center cursor-pointer"
                          title={opt.no_discount ? "Opcja nierabatowana — kliknij aby zmienić" : "Kliknij aby oznaczyć jako nierabatowaną"}
                        >
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={opt.no_discount}
                            onChange={(e) => handleUpdateFactoryOptionNoDiscount(opt.id, e.target.checked)}
                          />
                          <div className="w-7 h-4 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-amber-500"></div>
                        </label>
                        <button
                          onClick={() => handleRemoveFactoryOption(opt.id)}
                          className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          title="Usuń opcję"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-4 text-center text-slate-400 text-sm">
            Brak opcji fabrycznych — kliknij „Dodaj ręcznie" poniżej.
          </div>
        )}

        {/* Totals */}
        {customFactoryOptions.length > 0 && (
          <div className="pt-3 border-t border-slate-200 flex flex-wrap justify-between items-baseline gap-2">
            <span className="text-xs text-slate-400">
              Suma opcji fabrycznych
              {activeDiscountPct > 0 && (
                <span className="ml-2 px-1.5 py-0.5 text-[9px] font-bold uppercase rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Rabatowany ({activeDiscountPct}%)
                </span>
              )}
              {activeDiscountPct === 0 && (
                <span className="ml-2 px-1.5 py-0.5 text-[9px] font-bold uppercase rounded bg-slate-50 text-slate-500 border border-slate-200">
                  Nierabatowany
                </span>
              )}
            </span>
            <div className="text-right">
              <span className="text-sm font-semibold text-slate-800 tabular-nums">
                {fmtPLN(totalBrutto)} PLN
              </span>
              <span className="text-xs text-slate-400 ml-2 tabular-nums">
                ({fmtPLN(totalNet)} netto)
              </span>
            </div>
          </div>
        )}

        {/* Add button */}
        <div className="flex items-center justify-between pt-1">
          <button
            onClick={handleAddManualFactoryOption}
            className="flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 transition-all shadow-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            Dodaj ręcznie
          </button>
        </div>

        {/* Standard Equipment (collapsed) */}
        {hasStandardEquipment && (
          <details className="group">
            <summary className="flex items-center justify-between cursor-pointer hover:bg-slate-50 p-2 -mx-2 rounded transition-colors text-xs font-bold uppercase tracking-widest text-slate-400 select-none">
              <span>Wyposażenie standardowe ({standardEquipment.length})</span>
              <svg className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
            </summary>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 mt-2">
              {standardEquipment.map((item, idx) => (
                <div
                  key={`${item}-${idx}`}
                  className="py-1 text-xs text-slate-600 border-b border-slate-50"
                >
                  {item}
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
