import { useState } from "react";
import type { FleetVehicleView } from "../../types";
import { Pencil, X, Loader2, RefreshCw, Save } from "lucide-react";
import type { SamarClassRef, EngineTypeRef, BodyTypeRef } from "../../hooks/useReferenceData";

interface VehicleSummaryCardProps {
  vehicle: FleetVehicleView;
  onDirectSave?: (fields: Record<string, string>) => Promise<void>;
  isSaving?: boolean;
  onRemapClassification?: () => Promise<void>;
  isRemapping?: boolean;
  samarClasses?: SamarClassRef[];
  engineTypes?: EngineTypeRef[];
  bodyTypes?: BodyTypeRef[];
}

const EMPTY = "—";

const DRIVE_TYPE_LABELS: Record<string, string> = {
  "Napęd FWD": "4x2 (FWD)",
  "Napęd RWD": "4x2 (RWD)",
  "Napęd AWD": "4x4 (AWD)",
  "FWD": "4x2 (FWD)",
  "RWD": "4x2 (RWD)",
  "AWD": "4x4 (AWD)",
  "4x2": "4x2",
  "4x4": "4x4",
};

const DRIVE_TYPE_OPTIONS = [
  { value: "FWD", label: "4x2 (FWD)" },
  { value: "RWD", label: "4x2 (RWD)" },
  { value: "AWD", label: "4x4 (AWD)" },
];

function extractDriveType(vehicle: FleetVehicleView): string {
  const raw = vehicle.drive_type;
  if (!raw) return EMPTY;
  return DRIVE_TYPE_LABELS[raw] ?? raw;
}

function extractSeats(vehicle: FleetVehicleView): string {
  if (vehicle.number_of_seats == null) return EMPTY;
  return String(vehicle.number_of_seats);
}

function extractPaintCategory(vehicle: FleetVehicleView): string {
  if (vehicle.is_metalic_paint === true) return "Metalik";
  if (vehicle.is_metalic_paint === false) return "Bazowy";
  return EMPTY;
}

function val(v: string | null | undefined): string {
  if (!v || v === "Brak" || v === "-") return EMPTY;
  return v;
}

// Extract mapped_ai_data field safely
function getMappedField(vehicle: FleetVehicleView, key: string): string {
  const synth = vehicle.synthesis_data as Record<string, unknown> | undefined;
  const mapped = synth?.mapped_ai_data as Record<string, unknown> | undefined;
  const value = mapped?.[key];
  return typeof value === "string" ? value : "";
}

interface RowProps {
  label: string;
  value: string;
  isEditing?: boolean;
  editValue?: string;
  onEditChange?: (newVal: string) => void;
  type?: "text" | "dropdown";
  options?: { value: string; label: string }[];
  highlightNew?: boolean;
}

function Row({ label, value, isEditing, editValue, onEditChange, type = "text", options, highlightNew }: RowProps) {
  return (
    <tr className="border-b border-slate-100 last:border-b-0">
      <td className="py-2 pr-6 text-xs text-slate-400 whitespace-nowrap align-middle">
        {label}
        {highlightNew && (
          <span className="ml-1.5 text-[9px] font-bold px-1 py-0.5 rounded bg-violet-100 text-violet-600 uppercase">
            CRUD
          </span>
        )}
      </td>
      <td className="py-2 text-sm text-slate-800 font-medium align-middle">
        {isEditing ? (
          type === "dropdown" && options ? (
            <select
              className="w-full text-sm border border-slate-300 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white cursor-pointer"
              value={editValue ?? ""}
              onChange={(e) => onEditChange?.(e.target.value)}
            >
              <option value="">— wybierz —</option>
              {options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              className="w-full text-sm border border-slate-300 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
              value={editValue ?? ""}
              onChange={(e) => onEditChange?.(e.target.value)}
            />
          )
        ) : (
          value
        )}
      </td>
    </tr>
  );
}

export function VehicleSummaryCard({
  vehicle,
  onDirectSave,
  isSaving,
  onRemapClassification,
  isRemapping,
  samarClasses = [],
  engineTypes = [],
  bodyTypes = [],
}: VehicleSummaryCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  const startEditing = () => {
    const cardSummary = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;
    setEditValues({
      "Marka": val(vehicle.brand),
      "Model": val(vehicle.model),
      "Wersja": val(vehicle.trim_level),
      "Kategoria": val(vehicle.vehicle_class ?? vehicle.document_category),
      "Klasa SAMAR": getMappedField(vehicle, "samar_category"),
      "Kategoria silnika": getMappedField(vehicle, "fuel"),
      "Oś napędowa (DB)": getMappedField(vehicle, "drive_type") || vehicle.drive_type || "",
      "Typ nadwozia (DB)": getMappedField(vehicle, "body_type") || val(vehicle.body_style),
      "Napęd": val(vehicle.powertrain),
      "Paliwo": val(vehicle.fuel),
      "Moc silnika (KM)": val(cardSummary?.power_hp?.toString()),
      "Moc silnika (kW)": val(cardSummary?.power_kw?.toString()),
      "Skrzynia biegów": val(vehicle.transmission),
      "Koła": vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY,
      "Emisja WLTP": val(vehicle.emissions),
      "Kolor nadwozia": val(vehicle.exterior_color),
      "Ilość miejsc": extractSeats(vehicle),
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
    if (!onDirectSave) return;
    
    const fields: Record<string, string> = {};
    const collectIfChanged = (label: string, original: string, dbKey: string) => {
      const edited = editValues[label] ?? "";
      if (edited !== original && edited !== EMPTY) {
        fields[dbKey] = edited;
      }
    };

    collectIfChanged("Marka", val(vehicle.brand), "brand");
    collectIfChanged("Model", val(vehicle.model), "model");
    collectIfChanged("Wersja", val(vehicle.trim_level), "trim_level");
    collectIfChanged("Kategoria", val(vehicle.vehicle_class ?? vehicle.document_category), "vehicle_class");

    // New mapped_ai_data fields (prefixed with "mapped:" for save handler)
    collectIfChanged("Klasa SAMAR", getMappedField(vehicle, "samar_category"), "mapped:samar_category");
    collectIfChanged("Kategoria silnika", getMappedField(vehicle, "fuel"), "mapped:fuel");
    collectIfChanged("Oś napędowa (DB)", getMappedField(vehicle, "drive_type") || vehicle.drive_type || "", "mapped:drive_type");
    collectIfChanged("Typ nadwozia (DB)", getMappedField(vehicle, "body_type") || val(vehicle.body_style), "mapped:body_type");

    const cardSummary = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;
    collectIfChanged("Napęd", val(vehicle.powertrain), "powertrain");
    collectIfChanged("Paliwo", val(vehicle.fuel), "fuel");
    collectIfChanged("Moc silnika (KM)", val(cardSummary?.power_hp?.toString()), "power_hp");
    collectIfChanged("Moc silnika (kW)", val(cardSummary?.power_kw?.toString()), "power_kw");
    collectIfChanged("Skrzynia biegów", val(vehicle.transmission), "transmission");
    
    const currentWheels = vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY;
    const editedWheels = editValues["Koła"] ?? "";
    if (editedWheels !== currentWheels && editedWheels !== EMPTY) {
      fields["wheels"] = editedWheels.replace('"', '');
    }
    
    collectIfChanged("Emisja WLTP", val(vehicle.emissions), "emissions");
    collectIfChanged("Kolor nadwozia", val(vehicle.exterior_color), "exterior_color");
    collectIfChanged("Ilość miejsc", extractSeats(vehicle), "number_of_seats");
    collectIfChanged("Numer oferty", val(vehicle.offer_number), "offer_number");
    collectIfChanged("Kod konfiguracji", val(vehicle.configuration_code), "configuration_code");

    if (Object.keys(fields).length === 0) {
      setIsEditing(false);
      return;
    }

    await onDirectSave(fields);
    setIsEditing(false);
  };

  const handleEditChange = (label: string, newVal: string) => {
    setEditValues(prev => {
      const next = { ...prev, [label]: newVal };
      if (label === "Moc silnika (KM)") {
        const km = parseFloat(newVal);
        if (!isNaN(km)) {
          next["Moc silnika (kW)"] = Math.round(km * 0.73549875).toString();
        } else if (newVal === "") {
          next["Moc silnika (kW)"] = "";
        }
      } else if (label === "Moc silnika (kW)") {
        const kw = parseFloat(newVal);
        if (!isNaN(kw)) {
          next["Moc silnika (KM)"] = Math.round(kw * 1.35962162).toString();
        } else if (newVal === "") {
          next["Moc silnika (KM)"] = "";
        }
      }
      return next;
    });
  };

  // Build dropdown options from CRUD data
  const samarOptions = samarClasses.map(sc => ({
    value: sc.name,
    label: `${sc.name}${sc.size_class ? ` (${sc.size_class})` : ""}`,
  }));

  const engineOptions = engineTypes.map(et => ({
    value: et.name,
    label: `${et.name} — ${et.category}`,
  }));

  const bodyTypeOptions = bodyTypes.map(bt => ({
    value: bt.name,
    label: `${bt.name} (${bt.vehicle_class})`,
  }));

  const renderRow = (config: { label: string; value: string; type?: "text" | "dropdown"; options?: { value: string; label: string }[]; highlightNew?: boolean }) => (
    <Row
      key={config.label}
      label={config.label}
      value={config.value}
      isEditing={isEditing}
      editValue={editValues[config.label]}
      onEditChange={(newVal) => handleEditChange(config.label, newVal)}
      type={config.type}
      options={config.options}
      highlightNew={config.highlightNew}
    />
  );

  const renderRows = (configs: { label: string; value: string; type?: "text" | "dropdown"; options?: { value: string; label: string }[]; highlightNew?: boolean }[]) => {
    return configs.map(renderRow);
  };

  const identityRows: { label: string; value: string; type?: "text" | "dropdown"; options?: { value: string; label: string }[]; highlightNew?: boolean }[] = [
    { label: "Marka", value: val(vehicle.brand) },
    { label: "Model", value: val(vehicle.model) },
    { label: "Wersja", value: val(vehicle.trim_level) },
    { label: "Kategoria", value: val(vehicle.vehicle_class ?? vehicle.document_category) },
  ];

  // New CRUD-backed classification rows
  const classificationRows: typeof identityRows = [
    { label: "Klasa SAMAR", value: getMappedField(vehicle, "samar_category") || EMPTY, type: "dropdown", options: samarOptions, highlightNew: true },
    { label: "Kategoria silnika", value: getMappedField(vehicle, "fuel") || EMPTY, type: "dropdown", options: engineOptions, highlightNew: true },
    { label: "Oś napędowa (DB)", value: extractDriveType(vehicle), type: "dropdown", options: DRIVE_TYPE_OPTIONS, highlightNew: true },
    { label: "Typ nadwozia (DB)", value: getMappedField(vehicle, "body_type") || val(vehicle.body_style), type: "dropdown", options: bodyTypeOptions, highlightNew: true },
  ];

  const cardSummary = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;

  const techRows: typeof identityRows = [
    { label: "Napęd", value: val(vehicle.powertrain) },
    { label: "Paliwo", value: val(vehicle.fuel) },
    { label: "Moc silnika (KM)", value: val(cardSummary?.power_hp?.toString()) },
    { label: "Moc silnika (kW)", value: val(cardSummary?.power_kw?.toString()) },
    { label: "Skrzynia biegów", value: val(vehicle.transmission) },
    { label: "Koła", value: vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY },
    { label: "Emisja WLTP", value: val(vehicle.emissions) },
    { label: "Kolor nadwozia", value: val(vehicle.exterior_color) },
    { label: "Kategoria lakieru", value: extractPaintCategory(vehicle) },
    { label: "Ilość miejsc", value: extractSeats(vehicle) },
  ];

  const metaRows: typeof identityRows = [
    { label: "Numer oferty", value: val(vehicle.offer_number) },
    { label: "Kod konfiguracji", value: val(vehicle.configuration_code) },
  ];

  return (
    <div className="border border-slate-200 rounded bg-white relative">
      {(isSaving || isRemapping) && (
        <div className="absolute inset-0 bg-white/50 backdrop-blur-[1px] z-10 flex items-center justify-center rounded">
          <div className="flex items-center text-indigo-600 bg-white px-4 py-2 rounded-full shadow-sm border border-indigo-100">
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            <span className="text-sm font-medium">
              {isRemapping ? "Przeliczanie klasyfikacji..." : "Zapisywanie zmian..."}
            </span>
          </div>
        </div>
      )}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center flex-wrap gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center">
          Karta podsumowania pojazdu
          {isEditing && (
            <span className="ml-2 bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-[10px] font-bold">
              TRYB EDYCJI
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
                disabled={isSaving}
                className="text-xs px-3 py-1.5 bg-emerald-600 text-white hover:bg-emerald-700 rounded-md font-medium transition-colors flex items-center shadow-sm disabled:opacity-50"
              >
                {isSaving ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Save className="w-3.5 h-3.5 mr-1.5" />}
                Zapisz zmiany
              </button>
            </>
          ) : (
            <>
              <button
                onClick={startEditing}
                disabled={isSaving || !onDirectSave}
                className="text-xs px-3 py-1.5 bg-white text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-md font-medium transition-colors flex items-center shadow-sm border border-slate-200 disabled:opacity-50"
              >
                <Pencil className="w-3.5 h-3.5 mr-1.5" />
                Edytuj
              </button>
              {onRemapClassification && (
                <button
                  onClick={onRemapClassification}
                  disabled={isRemapping}
                  className="text-xs px-3 py-1.5 bg-violet-50 text-violet-700 hover:bg-violet-100 rounded-md font-medium transition-colors flex items-center shadow-sm border border-violet-100 disabled:opacity-50"
                  title="Przelicz klasyfikację pojazdu (SAMAR, silnik, serwis) na podstawie aktualnych danych"
                >
                  {isRemapping ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5 mr-1.5" />}
                  Przelicz klasyfikację
                </button>
              )}
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

        {/* Klasyfikacja kalkulacyjna + Metadane */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-violet-500 mb-3 flex items-center">
            <span className="w-2 h-2 rounded-full bg-violet-500 mr-2" />
            Klasyfikacja kalkulacyjna
          </h5>
          <table className="w-full">
            <tbody>
              {renderRows(classificationRows)}
            </tbody>
          </table>

          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 mt-5">
            Metadane oferty
          </h5>
          <table className="w-full">
            <tbody>
              {renderRows(metaRows)}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
