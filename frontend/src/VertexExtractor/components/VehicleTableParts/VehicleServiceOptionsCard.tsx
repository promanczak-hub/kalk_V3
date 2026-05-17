import { Database, Loader2, Wrench } from "lucide-react";
import type { FleetVehicleView } from "../../types";
import { NetGrossInput } from "./NetGrossInput";
import { AccordionCard } from "./AccordionCard";

const VAT = 1.23;

function fmtPLN(value: number): string {
  if (value === 0) return "—";
  return new Intl.NumberFormat("pl-PL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

interface VehicleServiceOptionsCardProps {
  vehicle: FleetVehicleView;
  customServiceOptions: { id: string; name: string; price_net: number; category: string; include_in_wr?: boolean }[];
  handleUpdateServiceOptionName: (id: string, newName: string) => void;
  handleUpdateServiceOptionPrice: (id: string, newPrice: number) => void;
  handleUpdateServiceOptionIncludeInWr: (id: string, include: boolean) => void;
  handleRemoveServiceOption: (id: string) => void;
  handleAddManualServiceOption: () => void;
  handleRestoreAllOptions: () => void;
  handleSaveAllOptions: () => Promise<void>;
  isSavingServices: boolean;
}

export function VehicleServiceOptionsCard({
  vehicle,
  customServiceOptions,
  handleUpdateServiceOptionName,
  handleUpdateServiceOptionPrice,
  handleUpdateServiceOptionIncludeInWr,
  handleRemoveServiceOption,
  handleAddManualServiceOption,
  handleRestoreAllOptions,
  handleSaveAllOptions,
  isSavingServices,
}: VehicleServiceOptionsCardProps) {
  const totalNet = customServiceOptions.reduce((sum, opt) => sum + opt.price_net, 0);
  const totalBrutto = totalNet * VAT;

  return (
    <AccordionCard
      id={`service-options-${vehicle.id}`}
      title="Opcje serwisowe"
      icon={<Wrench className="w-4 h-4 text-slate-500" />}
      defaultOpen={true}
      className="mb-4"
    >
      <div className="space-y-4">
        {customServiceOptions.length > 0 ? (
          <ul className="space-y-1">
            {customServiceOptions.map((opt) => (
              <li key={opt.id} className="flex flex-col xl:flex-row xl:items-center justify-between gap-2 text-[11px] pb-1 border-b border-slate-50 last:border-0 last:pb-0">
                <input type="text" className="flex-1 px-3 py-1 border border-slate-200 rounded text-slate-700 font-medium text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500" value={opt.name} onChange={(e) => handleUpdateServiceOptionName(opt.id, e.target.value)} placeholder="Nazwa Usługi" />
                <div className="flex items-center gap-2 mt-2 xl:mt-0 xl:w-auto w-full justify-between xl:justify-end">
                  <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-500 hover:text-slate-700 mr-2 border border-slate-100 px-2 py-1 rounded bg-slate-50/50">
                    <input type="checkbox" checked={opt.include_in_wr || false} onChange={(e) => handleUpdateServiceOptionIncludeInWr(opt.id, e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3 w-3" />
                    Dolicz do WR
                  </label>
                  <NetGrossInput netValue={opt.price_net} onChangeNet={(newVal) => handleUpdateServiceOptionPrice(opt.id, newVal)} />
                  <button onClick={() => handleRemoveServiceOption(opt.id)} className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors" title="Usuń pozycję">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="py-6 text-center text-slate-400 text-sm">
            Brak zdefiniowanych operacji serwisowych dla tego pojazdu.
          </div>
        )}
        {customServiceOptions.length > 0 && (
          <div className="pt-3 border-t border-slate-200 flex flex-wrap justify-between items-baseline gap-2">
            <span className="text-xs text-slate-400">Suma opcji serwisowych</span>
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
        <div className={`flex flex-col gap-4 pt-2 ${customServiceOptions.length === 0 ? "border-t border-slate-100" : ""}`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <button onClick={handleAddManualServiceOption} className="flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 transition-all shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              Dodaj ręcznie
            </button>
            <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto mt-2 sm:mt-0">
              <button onClick={handleRestoreAllOptions} className="w-full sm:w-auto flex items-center justify-center text-[11px] font-semibold px-4 py-2 rounded border border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors" title="Odrzuć zmiany i przywróć opcje domyślne">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                Cofnij zmiany
              </button>
              <button onClick={handleSaveAllOptions} disabled={isSavingServices} className="w-full sm:w-auto flex items-center justify-center text-xs font-semibold px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-all shadow-sm">
                {isSavingServices ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Database className="w-4 h-4 mr-2" />}
                {isSavingServices ? "Zapisywanie..." : "Zapisz zmiany"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </AccordionCard>
  );
}
