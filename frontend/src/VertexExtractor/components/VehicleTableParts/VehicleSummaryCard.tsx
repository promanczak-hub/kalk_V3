import { useState } from "react";
import type { FleetVehicleView } from "../../types";
import { PipelineDebugger } from "../PipelineDebugger";
import { Pencil, Check, X, Loader2, Wand2 } from "lucide-react";

interface VehicleSummaryCardProps {
  vehicle: FleetVehicleView;
  onOverride?: (prompt: string) => Promise<void>;
  isOverriding?: boolean;
}

const EMPTY = "—";

function val(v: string | null | undefined): string {
  if (!v || v === "Brak" || v === "-") return EMPTY;
  return v;
}

interface RowProps {
  label: string;
  value: string;
  isEditing?: boolean;
  editValue?: string;
  onEditChange?: (newVal: string) => void;
}

function Row({ label, value, isEditing, editValue, onEditChange }: RowProps) {
  return (
    <tr className="border-b border-slate-100 last:border-b-0">
      <td className="py-2 pr-6 text-xs text-slate-400 whitespace-nowrap align-middle">
        {label}
      </td>
      <td className="py-2 text-sm text-slate-800 font-medium align-middle">
        {isEditing ? (
          <input
            type="text"
            className="w-full text-sm border border-slate-300 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
            value={editValue ?? ""}
            onChange={(e) => onEditChange?.(e.target.value)}
          />
        ) : (
          value
        )}
      </td>
    </tr>
  );
}

export function VehicleSummaryCard({ vehicle, onOverride, isOverriding }: VehicleSummaryCardProps) {
  const [showDebugger, setShowDebugger] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  const startEditing = () => {
    setEditValues({
      "Marka": val(vehicle.brand),
      "Model": val(vehicle.model),
      "Wersja": val(vehicle.trim_level),
      "Typ nadwozia": val(vehicle.body_style),
      "Kategoria": val(vehicle.vehicle_class ?? vehicle.document_category),
      "Napęd": val(vehicle.powertrain),
      "Paliwo": val(vehicle.fuel),
      "Skrzynia biegów": val(vehicle.transmission),
      "Koła": vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY,
      "Emisja WLTP": val(vehicle.emissions),
      "Kolor nadwozia": val(vehicle.exterior_color),
      "Numer oferty": val(vehicle.offer_number),
      "Kod konfiguracji": val(vehicle.configuration_code),
    });
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setEditValues({});
  };

  const handleSave = async () => {
    if (!onOverride) return;
    
    const changedFields: string[] = [];
    const checkChange = (label: string, original: string, formattedLabel: string = label) => {
      if (editValues[label] !== original) {
        changedFields.push(`${formattedLabel}: ${editValues[label]}`);
      }
    };

    checkChange("Marka", val(vehicle.brand));
    checkChange("Model", val(vehicle.model));
    checkChange("Wersja", val(vehicle.trim_level));
    checkChange("Typ nadwozia", val(vehicle.body_style));
    checkChange("Kategoria", val(vehicle.vehicle_class ?? vehicle.document_category));
    checkChange("Napęd", val(vehicle.powertrain));
    checkChange("Paliwo", val(vehicle.fuel));
    checkChange("Skrzynia biegów", val(vehicle.transmission));
    
    const currentWheels = vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY;
    if (editValues["Koła"] !== currentWheels) {
      changedFields.push(`Koła (średnica): ${editValues["Koła"].replace('"', '')}`);
    }
    
    checkChange("Emisja WLTP", val(vehicle.emissions), "Emisja (CO2/WLTP)");
    checkChange("Kolor nadwozia", val(vehicle.exterior_color));
    checkChange("Numer oferty", val(vehicle.offer_number));
    checkChange("Kod konfiguracji", val(vehicle.configuration_code));

    if (changedFields.length === 0) {
      setIsEditing(false);
      return;
    }

    const prompt = `Zaktualizuj w 'card_summary' następujące pola: \n${changedFields.join("\n")}\nZastosuj tylko te zmiany, resztę wartości pozostaw bez zmian.`;
    await onOverride(prompt);
    setIsEditing(false);
  };

  const handleEditChange = (label: string, newVal: string) => {
    setEditValues(prev => ({ ...prev, [label]: newVal }));
  };

  const renderRows = (config: {label: string, value: string}[]) => {
    return config.map((r) => (
      <Row 
        key={r.label} 
        label={r.label}
        value={r.value}
        isEditing={isEditing}
        editValue={editValues[r.label]}
        onEditChange={(newVal) => handleEditChange(r.label, newVal)}
      />
    ));
  };

  const identityRows = [
    { label: "Marka", value: val(vehicle.brand) },
    { label: "Model", value: val(vehicle.model) },
    { label: "Wersja", value: val(vehicle.trim_level) },
    { label: "Typ nadwozia", value: val(vehicle.body_style) },
    { label: "Kategoria", value: val(vehicle.vehicle_class ?? vehicle.document_category) },
  ];

  const techRows = [
    { label: "Napęd", value: val(vehicle.powertrain) },
    { label: "Paliwo", value: val(vehicle.fuel) },
    { label: "Skrzynia biegów", value: val(vehicle.transmission) },
    { label: "Koła", value: vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY },
    { label: "Emisja WLTP", value: val(vehicle.emissions) },
    { label: "Kolor nadwozia", value: val(vehicle.exterior_color) },
  ];

  const metaRows = [
    { label: "Numer oferty", value: val(vehicle.offer_number) },
    { label: "Kod konfiguracji", value: val(vehicle.configuration_code) },
  ];

  return (
    <div className="border border-slate-200 rounded bg-white relative">
      {isOverriding && (
        <div className="absolute inset-0 bg-white/50 backdrop-blur-[1px] z-10 flex items-center justify-center rounded">
          <div className="flex items-center text-indigo-600 bg-white px-4 py-2 rounded-full shadow-sm border border-indigo-100">
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            <span className="text-sm font-medium">Trwa aktualizacja przez AI...</span>
          </div>
        </div>
      )}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center flex-wrap gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center">
          Karta podsumowania pojazdu
          {isEditing && (
            <span className="ml-2 bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-[10px] font-bold">
              TRYB EDYCJI AI
            </span>
          )}
        </h4>
        <div className="flex items-center space-x-2">
          {isEditing ? (
            <>
              <button
                onClick={cancelEditing}
                className="text-xs px-3 py-1.5 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 rounded-md font-medium transition-colors flex items-center border border-slate-200"
              >
                <X className="w-3.5 h-3.5 mr-1.5" />
                Anuluj
              </button>
              <button
                onClick={handleSave}
                disabled={isOverriding}
                className="text-xs px-3 py-1.5 bg-indigo-600 text-white hover:bg-indigo-700 rounded-md font-medium transition-colors flex items-center shadow-sm disabled:opacity-50"
              >
                {isOverriding ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5 mr-1.5" />}
                Zapisz i przelicz AI
              </button>
            </>
          ) : (
            <>
              <button
                onClick={startEditing}
                disabled={isOverriding || !onOverride}
                className="text-xs px-3 py-1.5 bg-white text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-md font-medium transition-colors flex items-center shadow-sm border border-slate-200 disabled:opacity-50"
              >
                <Pencil className="w-3.5 h-3.5 mr-1.5" />
                Edytuj AI
              </button>
              <button
                onClick={() => setShowDebugger(true)}
                className="text-xs px-3 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-md font-medium transition-colors flex items-center shadow-sm border border-indigo-100"
              >
                <svg className="w-3.5 h-3.5 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                Debugger Pipeline
              </button>
            </>
          )}
        </div>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Identyfikacja */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
            Identyfikacja
          </h5>
          <table className="w-full">
            <tbody>
              {renderRows(identityRows)}
            </tbody>
          </table>
        </div>

        {/* Specyfikacja techniczna */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 flex items-center">
            Specyfikacja techniczna
          </h5>
          <table className="w-full">
            <tbody>
              {renderRows(techRows)}
            </tbody>
          </table>
        </div>

        {/* Metadane */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
            Metadane oferty
          </h5>
          <table className="w-full">
            <tbody>
              {renderRows(metaRows)}
            </tbody>
          </table>
        </div>
      </div>

      {showDebugger && (
        <PipelineDebugger
          vehicle={vehicle}
          onClose={() => setShowDebugger(false)}
        />
      )}
    </div>
  );
}
