import { useState } from "react";
import type { FleetVehicleView } from "../../types";
import { Pencil, X, Loader2, RefreshCw, Save, Activity, Fuel, Car } from "lucide-react";
import { AccordionCard } from "./AccordionCard";
import { apiClient } from "../../../lib/apiClient";
import { SamarCategoryDropdown } from "./SamarCategoryDropdown";
import { EngineCategoryDropdown } from "./EngineCategoryDropdown";
import { VehicleTypeDropdown } from "./VehicleTypeDropdown";
import { Tag, DriveTypeTag, BodyTypeTag, TransmissionTag, type SamarCandidate, type EngineCandidate, type MappedData } from "./VehicleBaseInfo";

export interface VehicleSummaryCardProps {
  vehicle: FleetVehicleView;
  mappedData?: MappedData;
  samarCandidates?: SamarCandidate[];
  allSamarClasses?: string[];
  onSamarCategoryChange?: (v: string) => Promise<void> | void;
  engineCandidates?: EngineCandidate[];
  allEngineTypes?: string[];
  onEngineCategoryChange?: (v: string) => Promise<void> | void;
  driveType?: string;
  driveTypes?: string[];
  onDriveTypeChange?: (v: string) => Promise<void> | void;
  transmission?: string;
  transmissionTypes?: string[];
  onTransmissionChange?: (v: string) => Promise<void> | void;
  bodyType?: string;
  onBodyTypeChange?: (v: string) => Promise<void> | void;
  onVehicleTypeChange?: (v: string) => Promise<void> | void;
  bodyTypeOptions?: {name: string, vehicle_class: string}[];
  onDirectSave?: (fields: Record<string, string>) => Promise<void>;
  isSaving?: boolean;
  onRemapClassification?: () => Promise<void>;
  isRemapping?: boolean;
}

const EMPTY = "—";



function extractSeats(vehicle: FleetVehicleView): string {
  if (vehicle.number_of_seats == null) return EMPTY;
  return String(vehicle.number_of_seats);
}

function extractPaintCategory(vehicle: FleetVehicleView): string {
  if (vehicle.is_metalic_paint === true) return "Metalik";
  if (vehicle.is_metalic_paint === false) return "Niemetalik";
  return EMPTY;
}

function val(v: string | null | undefined): string {
  if (!v || v === "Brak" || v === "-") return EMPTY;
  return v;
}



interface RowProps {
  label: string;
  value: React.ReactNode;
  isEditing?: boolean;
  editValue?: string;
  onEditChange?: (newVal: string) => void;
  type?: "text" | "dropdown" | "custom";
  options?: { value: string; label: string }[];
  highlightNew?: boolean;
}

function Row({ label, value, isEditing, editValue, onEditChange, type = "text", options, highlightNew }: RowProps) {
  return (
    <tr className="border-b border-slate-100 last:border-b-0">
      <td className="py-1.5 pr-4 text-[11px] text-slate-400 whitespace-nowrap align-middle">
        {label}
        {highlightNew && (
          <span className="ml-1.5 text-[8px] font-bold px-1 py-0.5 rounded bg-violet-100 text-violet-600 uppercase">
            CRUD
          </span>
        )}
      </td>
      <td className="py-1.5 text-xs text-slate-800 font-medium align-middle">
        {isEditing && type !== "custom" ? (
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
  mappedData,
  samarCandidates,
  allSamarClasses,
  onSamarCategoryChange,
  engineCandidates,
  allEngineTypes,
  onEngineCategoryChange,
  driveType,
  driveTypes,
  onDriveTypeChange,
  transmission,
  transmissionTypes,
  onTransmissionChange,
  bodyType,
  onBodyTypeChange,
  onVehicleTypeChange,
  bodyTypeOptions,
  onDirectSave,
  isSaving,
  onRemapClassification,
  isRemapping,
}: VehicleSummaryCardProps) {

  const [isEditing, setIsEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  const startEditing = () => {
    const cardSummary = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;
    setEditValues({
      "Marka": val(vehicle.brand),
      "Model": val(vehicle.model),
      "Wersja": val(vehicle.trim_level),
      "Oś napędowa": val(vehicle.drive_type) || val((cardSummary?.drive_type as string)),
      "Silnik (Paliwo)": val(vehicle.fuel),
      "Moc silnika (KM)": val(cardSummary?.power_hp?.toString()),
      "Moc silnika (kW)": val(cardSummary?.power_kw?.toString()),
      "Skrzynia biegów": val(vehicle.transmission),
      "Koła": vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY,
      "Emisja WLTP": val(vehicle.emissions),
      "Rodzaj lakieru": val(vehicle.is_metalic_paint === true ? "Metalik" : vehicle.is_metalic_paint === false ? "Niemetalik" : ""),
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
    const feedbackData: { old_value: string, new_value: string, field_name: string }[] = [];
    
    const collectIfChanged = (label: string, original: string, dbKey: string) => {
      const edited = editValues[label] ?? "";
      if (edited !== original && edited !== EMPTY) {
        fields[dbKey] = edited;
        feedbackData.push({ old_value: original, new_value: edited, field_name: dbKey });
      }
    };

    collectIfChanged("Marka", val(vehicle.brand), "brand");
    collectIfChanged("Model", val(vehicle.model), "model");
    collectIfChanged("Wersja", val(vehicle.trim_level), "trim_level");

    const cardSummary = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;
    collectIfChanged("Oś napędowa", val(vehicle.drive_type) || val((cardSummary?.drive_type as string)), "drive_type");
    collectIfChanged("Silnik (Paliwo)", val(vehicle.fuel), "fuel");
    collectIfChanged("Moc silnika (KM)", val(cardSummary?.power_hp?.toString()), "power_hp");
    collectIfChanged("Moc silnika (kW)", val(cardSummary?.power_kw?.toString()), "power_kw");
    collectIfChanged("Skrzynia biegów", val(vehicle.transmission), "transmission");
    
    const currentWheels = vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY;
    const editedWheels = editValues["Koła"] ?? "";
    if (editedWheels !== currentWheels && editedWheels !== EMPTY) {
      fields["wheels"] = editedWheels.replace('"', '');
      feedbackData.push({ old_value: currentWheels, new_value: editedWheels.replace('"', ''), field_name: "wheels" });
    }
    
    collectIfChanged("Emisja WLTP", val(vehicle.emissions), "emissions");
    const currentPaint = val(vehicle.is_metalic_paint === true ? "Metalik" : vehicle.is_metalic_paint === false ? "Niemetalik" : "");
    const editedPaint = editValues["Rodzaj lakieru"] ?? "";
    if (editedPaint !== currentPaint && editedPaint !== EMPTY) {
      const isMetalic = editedPaint === "Metalik";
      fields["is_metalic_paint"] = String(isMetalic);
    }
    collectIfChanged("Ilość miejsc", extractSeats(vehicle), "number_of_seats");
    collectIfChanged("Numer oferty", val(vehicle.offer_number), "offer_number");
    collectIfChanged("Kod konfiguracji", val(vehicle.configuration_code), "configuration_code");

    if (Object.keys(fields).length === 0) {
      setIsEditing(false);
      return;
    }

    try {
      await onDirectSave(fields);
      
      // Raportowanie poprawek do pętli sprzężenia zwrotnego AI
      for (const item of feedbackData) {
        apiClient.fetch("/api/extract/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                vehicle_id: vehicle.id,
                brand: val(vehicle.brand),
                model: val(vehicle.model),
                field_name: item.field_name,
                old_value: item.old_value,
                new_value: item.new_value,
            })
        }).catch(e => console.error("Nie udało się wysłać feedbacku ekstrakcji", e));
      }
    } catch (e) {
      console.error("Błąd podczas zapisu", e);
    }
    
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

  const renderRow = (config: { label: string; value: React.ReactNode; type?: "text" | "dropdown" | "custom"; options?: { value: string; label: string }[]; highlightNew?: boolean }) => (
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

  const renderRows = (configs: { label: string; value: React.ReactNode; type?: "text" | "dropdown" | "custom"; options?: { value: string; label: string }[]; highlightNew?: boolean }[]) => {
    return configs.map(renderRow);
  };

  const identityRows: { label: string; value: React.ReactNode; type?: "text" | "dropdown" | "custom"; options?: { value: string; label: string }[]; highlightNew?: boolean }[] = [
    { label: "Marka", value: val(vehicle.brand) },
    { label: "Model", value: val(vehicle.model) },
    { label: "Wersja", value: val(vehicle.trim_level) },
    { 
      label: "Kategoria", 
      value: (
        onVehicleTypeChange ? (
          <VehicleTypeDropdown
            currentType={mappedData?.vehicle_type || ""}
            onTypeChange={onVehicleTypeChange}
            connected={false}
          />
        ) : mappedData?.vehicle_type ? (
          <Tag icon={Car}>{mappedData.vehicle_type}</Tag>
        ) : val(vehicle.vehicle_class ?? vehicle.document_category)
      ),
      type: "custom"
    },
    {
      label: "Klasa SAMAR",
      value: (
        mappedData?.samar_category && onSamarCategoryChange ? (
          <SamarCategoryDropdown
            currentCategory={mappedData.samar_category}
            candidates={samarCandidates || []}
            allSamarClasses={allSamarClasses || []}
            onCategoryChange={onSamarCategoryChange}
            connected={false}
          />
        ) : mappedData?.samar_category ? (
          <Tag icon={Activity}>{mappedData.samar_category}</Tag>
        ) : EMPTY
      ),
      type: "custom"
    }
  ];

  const cardSummary = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.card_summary as Record<string, unknown> | undefined;
  const digitalTwin = (vehicle.synthesis_data as Record<string, unknown> | undefined)?.digital_twin as Record<string, unknown> | undefined;
  const dimensions = digitalTwin?.dimensions as Record<string, number | null> | undefined;

  const formatDim = (val: number | null | undefined, unit: string) => val ? `${val} ${unit}` : EMPTY;
  
  const isPassengerCar = (mappedData?.vehicle_type ?? vehicle.vehicle_class) === "Osobowy";

  const dimensionsRows: typeof identityRows = isPassengerCar ? [] : [
    { label: "Poj. ładunkowa", value: formatDim(dimensions?.cargo_volume_m3, "m³") },
    { label: "Długość paki", value: formatDim(dimensions?.cargo_length_mm, "mm") },
    { label: "Szerokość paki", value: formatDim(dimensions?.cargo_width_mm, "mm") },
    { label: "Wysokość paki", value: formatDim(dimensions?.cargo_height_mm, "mm") },
    { label: "Długość pojazdu", value: formatDim(dimensions?.vehicle_length_mm, "mm") },
    { label: "Liczba europalet", value: dimensions?.europallet_capacity ? String(dimensions.europallet_capacity) : EMPTY },
  ].filter(row => row.value !== EMPTY); // Only show rows that have data

  const techConfigRows: typeof identityRows = [
    { 
      label: "Oś napędowa", 
      value: <DriveTypeTag current={driveType || ""} onChange={onDriveTypeChange} connected={false} driveTypeOptions={driveTypes} />,
      type: "custom"
    },
    { 
      label: "Silnik (Paliwo)", 
      value: (
        mappedData?.engine_class && onEngineCategoryChange ? (
          <EngineCategoryDropdown
            currentCategory={mappedData.fuel}
            candidates={engineCandidates || []}
            allEngineTypes={allEngineTypes || []}
            onCategoryChange={onEngineCategoryChange}
            connected={false}
          />
        ) : mappedData?.engine_class ? (
          <Tag icon={Fuel}>{mappedData.fuel} / {mappedData.engine_class}</Tag>
        ) : val(vehicle.fuel)
      ),
      type: "custom"
    },
    { 
      label: "Skrzynia biegów", 
      value: <TransmissionTag current={transmission || ""} onChange={onTransmissionChange} connected={false} transmissionOptions={transmissionTypes} />,
      type: "custom"
    },
    { 
      label: "Nadwozie", 
      value: (
        <BodyTypeTag
          current={bodyType || ""}
          dbOptions={bodyTypeOptions}
          onChange={onBodyTypeChange}
          currentVehicleType={mappedData?.vehicle_type}
          connected={false}
        />
      ),
      type: "custom" 
    }
  ];

  const techParamRows: typeof identityRows = [
    { label: "Moc silnika (KM)", value: val(cardSummary?.power_hp?.toString()) },
    { label: "Moc silnika (kW)", value: val(cardSummary?.power_kw?.toString()) },
    { label: "Koła", value: vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY },
    { label: "Emisja WLTP", value: val(vehicle.emissions) },
    { 
      label: "Rodzaj lakieru", 
      value: extractPaintCategory(vehicle),
      type: "dropdown",
      options: [
        { value: "Metalik", label: "Metalik" },
        { value: "Niemetalik", label: "Niemetalik" }
      ] 
    },
    { label: "Ilość miejsc", value: extractSeats(vehicle) }
  ];


  const metaRows: typeof identityRows = [
    { label: "Numer oferty", value: val(vehicle.offer_number) },
    { label: "Kod konfiguracji", value: val(vehicle.configuration_code) },
  ];

  const headerRight = (
    <div className="flex items-center space-x-2">
      {isEditing ? (
        <>
          <button
            onClick={(e) => { e.stopPropagation(); cancelEditing(); }}
            className="text-xs px-3 py-1.5 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 rounded-md font-medium transition-colors flex items-center border border-slate-200"
          >
            <X className="w-3.5 h-3.5 mr-1.5" />
            Anuluj
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleSave(); }}
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
            onClick={(e) => { e.stopPropagation(); startEditing(); }}
            disabled={isSaving || !onDirectSave}
            className="text-xs px-3 py-1.5 bg-white text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-md font-medium transition-colors flex items-center shadow-sm border border-slate-200 disabled:opacity-50"
          >
            <Pencil className="w-3.5 h-3.5 mr-1.5" />
            Edytuj
          </button>
          {onRemapClassification && (
             <div onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={onRemapClassification}
                  disabled={isRemapping}
                  className="text-xs px-3 py-1.5 bg-violet-50 text-violet-700 hover:bg-violet-100 rounded-md font-medium transition-colors flex items-center shadow-sm border border-violet-100 disabled:opacity-50"
                  title="Przelicz klasyfikację pojazdu (SAMAR, silnik, serwis) na podstawie aktualnych danych"
                >
                  {isRemapping ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5 mr-1.5" />}
                  Przelicz
                </button>
             </div>
          )}
        </>
      )}
    </div>
  );

  const titleNodes = (
    <div className="flex items-center">
      Karta podsumowania pojazdu
      {isEditing && (
        <span className="ml-2 bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-[10px] font-bold border border-amber-200">
          TRYB EDYCJI
        </span>
      )}
    </div>
  );

  return (
    <AccordionCard 
      title={titleNodes} 
      headerRight={headerRight} 
      defaultOpen={false} 
      className="relative"
    >
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

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Identyfikacja + Metadane */}
        <div className="lg:col-span-5">
          <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Identyfikacja
          </h5>
          <table className="w-full">
            <tbody>
              {renderRows(identityRows)}
            </tbody>
          </table>

          <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 mt-5">
            Metadane oferty
          </h5>
          <table className="w-full">
            <tbody>
              {renderRows(metaRows)}
            </tbody>
          </table>
        </div>

        {/* Specyfikacja techniczna */}
        <div className="lg:col-span-7">
          <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center">
            Specyfikacja techniczna
          </h5>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <table className="w-full">
              <tbody>
                {renderRows(techConfigRows)}
              </tbody>
            </table>
            <table className="w-full">
              <tbody>
                {renderRows(techParamRows)}
              </tbody>
            </table>
          </div>

          {dimensionsRows.length > 0 && (
            <>
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 mt-5 flex items-center">
                Wymiary i przestrzeń ładunkowa
              </h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <table className="w-full">
                  <tbody>
                    {renderRows(dimensionsRows.slice(0, Math.ceil(dimensionsRows.length / 2)))}
                  </tbody>
                </table>
                <table className="w-full">
                  <tbody>
                    {renderRows(dimensionsRows.slice(Math.ceil(dimensionsRows.length / 2)))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </AccordionCard>
  );
}
