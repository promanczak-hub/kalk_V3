import { Loader2, Wand2 } from "lucide-react";

interface VehicleManualOverrideModalProps {
  overridePrompt: string;
  setOverridePrompt: (val: string) => void;
  isOverriding: boolean;
  handleManualOverride: () => void;
}

export function VehicleManualOverrideModal({
  overridePrompt,
  setOverridePrompt,
  isOverriding,
  handleManualOverride
}: VehicleManualOverrideModalProps) {
  return (
    <div className="w-full mt-2 p-4 bg-slate-50 border border-slate-200 rounded-lg animate-in fade-in slide-in-from-top-2">
      <h5 className="text-[11px] font-bold text-slate-700 mb-2 flex items-center uppercase tracking-wider">
        <Wand2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" /> Nadpisywanie Danych z użyciem AI (Flash)
      </h5>
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="np. Dodaj hak holowniczy, moc silnika to 300KM, ma napęd AWD..."
          value={overridePrompt}
          onChange={(e) => setOverridePrompt(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-md border border-slate-300 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 shadow-sm"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleManualOverride();
          }}
        />
        <button
          onClick={() => handleManualOverride()}
          disabled={isOverriding || !overridePrompt.trim()}
          className="px-4 py-2 bg-emerald-600 text-white rounded-md font-medium text-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center shadow-sm transition-colors"
        >
          {isOverriding ? <Loader2 className="w-4 h-4 animate-spin mr-1.5" /> : null}
          {isOverriding ? "Korygowanie..." : "Zastosuj"}
        </button>
      </div>
      <p className="text-xs text-slate-500 mt-2">
        Algorytm chirurgicznie zedytuje wyłącznie zlecane parametry w obrębie Cyfrowego Bliźniaka, zachowując 100% spójności reszty dokumentu. Zmiana widoczna będzie po odświeżeniu.
      </p>
    </div>
  );
}
