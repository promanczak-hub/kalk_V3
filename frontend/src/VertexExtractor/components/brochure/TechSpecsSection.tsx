import { Hand } from "lucide-react";

interface TechSpecsSectionProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  vehicleData: any;
  onChange: (field: string, value: string) => void;
}

export function TechSpecsSection({ vehicleData, onChange }: TechSpecsSectionProps) {
  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="font-semibold text-slate-800 flex items-center mb-4">
        <Hand className="w-4 h-4 mr-2 text-blue-500" /> Dane Pojazdu
      </h3>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-xs text-slate-500 font-medium">Nagłówek (Marka Model)</label>
          <input 
            type="text" 
            value={vehicleData?.brand || ""} 
            onChange={(e) => onChange("brand", e.target.value)}
            className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none" 
            placeholder="Marka pojazdu"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500 font-medium">Model</label>
          <input 
            type="text" 
            value={vehicleData?.model || ""} 
            onChange={(e) => onChange("model", e.target.value)}
            className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none" 
            placeholder="Model pojazdu"
          />
        </div>
        <div className="space-y-1 col-span-2">
          <label className="text-xs text-slate-500 font-medium">Wersja | Edycja | Linia</label>
          <input 
            type="text" 
            value={vehicleData?.edition || ""} 
            onChange={(e) => onChange("edition", e.target.value)}
            className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none" 
          />
        </div>
        <div className="space-y-1 col-span-2">
          <label className="text-xs text-slate-500 font-medium">Silnik / Napęd</label>
          <input 
            type="text" 
            value={vehicleData?.engine || ""} 
            onChange={(e) => onChange("engine", e.target.value)}
            className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none" 
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500 font-medium">Segment / Typ nadwozia</label>
          <input 
            type="text" 
            value={vehicleData?.body_type || ""} 
            onChange={(e) => onChange("body_type", e.target.value)}
            className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none" 
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500 font-medium">Moc (KM)</label>
          <input 
            type="text" 
            value={vehicleData?.horsepower || ""} 
            onChange={(e) => onChange("horsepower", e.target.value)}
            className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none" 
          />
        </div>
      </div>
    </div>
  );
}
