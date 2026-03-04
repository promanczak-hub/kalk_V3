import { useState } from "react";
import { Loader2, X, Download, Save } from "lucide-react";
import type { FleetVehicleView } from "../../types";
import { HeroSection, type BrochureImage } from "./HeroSection";
import { TechSpecsSection } from "./TechSpecsSection";
import { EquipmentToggleSection } from "./EquipmentToggleSection";
import { NotesSection } from "./NotesSection";
import { BlobProvider, PDFDownloadLink } from "@react-pdf/renderer";
import { BrochurePDFDocument } from "./BrochurePDFDocument";

interface BrochureBuilderModalProps {
  vehicle: FleetVehicleView;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  initialBrochureData: any;
  initialImages?: string[];
  onClose: () => void;
}

export function BrochureBuilderModal({
  vehicle,
  initialBrochureData,
  initialImages = [],
  onClose,
}: BrochureBuilderModalProps) {
  // Map flat VehicleBrochureSchema fields to the vehicle_name object the UI expects
  const buildVehicleName = (data: any) => ({
    brand: data?.brand || "",
    model: data?.model || "",
    edition: data?.trim_level || "",
    engine: data?.engine_description || "",
    body_type: data?.drive_type || "",
    horsepower: data?.power_hp ? String(data.power_hp) : "",
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [brochureData, setBrochureData] = useState<any | null>(
    initialBrochureData
      ? { ...initialBrochureData, vehicle_name: buildVehicleName(initialBrochureData) }
      : null
  );

  // Zunifikowany Stan Edytora
  const [images, setImages] = useState<BrochureImage[]>(
      initialImages.map((url, i) => ({ id: `ext-${i}`, url, file: null, isMain: false }))
  );
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState<string>("");

  // Map vehicle_name field keys back to flat schema keys for consistency
  const FIELD_TO_FLAT: Record<string, string> = {
    brand: "brand",
    model: "model",
    edition: "trim_level",
    engine: "engine_description",
    body_type: "drive_type",
    horsepower: "power_hp",
  };

  const handleTechSpecsChange = (field: string, value: string) => {
    if (!brochureData) return;
    const flatKey = FIELD_TO_FLAT[field] || field;
    setBrochureData({
      ...brochureData,
      [flatKey]: flatKey === "power_hp" ? (parseInt(value, 10) || null) : value,
      vehicle_name: {
        ...brochureData.vehicle_name,
        [field]: value,
      },
    });
  };

  const handleEquipmentToggle = (catIndex: number, itemIdx: number) => {
    const key = `${catIndex}-${itemIdx}`;
    const newSet = new Set(hiddenItems);
    if (newSet.has(key)) newSet.delete(key);
    else newSet.add(key);
    setHiddenItems(newSet);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden ring-1 ring-slate-900/5">
        
        <header className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <span className="text-2xl">📄</span> Kreator Broszury (White-label)
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Dostosuj dane i wygeneruj czysty plik PDF dla klienta - {vehicle.brand} {vehicle.model}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar bg-slate-50/30">
          {brochureData ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Kolumna lewa: Edytor/Sekcje */}
              <div className="lg:col-span-2 space-y-6">
                
                {/* Sekcja Głównego Obrazka i Zarządcy */}
                <HeroSection images={images} setImages={setImages} />

                {/* Sekcja Specyfikacji Technicznej */}
                <TechSpecsSection vehicleData={brochureData.vehicle_name} onChange={handleTechSpecsChange} />

                {/* Sekcja Wyposażenia z Togglowaniem */}
                <EquipmentToggleSection categories={brochureData.equipment_categories} hiddenItems={hiddenItems} onToggleItem={handleEquipmentToggle} />

                {/* Sekcja Niestandardowych Notatek */}
                <NotesSection notes={notes} onChange={setNotes} />

              </div>

              {/* Kolumna Prawa: Podgląd PDF */}
              <div className="lg:col-span-1">
                <div className="sticky top-6 bg-slate-800 rounded-xl p-4 shadow-lg text-white flex flex-col h-[700px]">
                   <h3 className="font-medium text-slate-200 flex items-center mb-4 text-sm">
                     Podgląd dokumentu
                   </h3>
                   <div className="flex-1 bg-white rounded-lg flex items-center justify-center relative overflow-hidden">
                      <BlobProvider document={<BrochurePDFDocument data={brochureData} images={images} hiddenItems={hiddenItems} notes={notes} />}>
                        {({ url, loading, error }) => {
                          if (loading) return <div className="flex items-center text-slate-500"><Loader2 className="w-5 h-5 animate-spin mr-2" /> Generowanie podglądu...</div>;
                          if (error) return <div className="text-red-500 text-sm p-4 text-center">Błąd podczas renderowania PDF:<br/>{error.message}</div>;
                          if (url) return (
                            <object data={`${url}#view=FitH`} type="application/pdf" className="w-full h-full border-0">
                              <div className="flex flex-col items-center justify-center p-6 text-center text-slate-500 w-full h-full bg-slate-100">
                                <p className="mb-2 text-sm z-10">Twoja przeglądarka blokuje wbudowany podgląd PDF.</p>
                                <a href={url} target="_blank" rel="noopener noreferrer" className="z-10 px-4 py-2 mt-2 font-medium bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors">
                                  Pobierz wygenerowany dokument
                                </a>
                              </div>
                            </object>
                           );
                          return null;
                        }}
                      </BlobProvider>
                   </div>
                   
                   <div className="mt-4 pt-4 border-t border-slate-700 grid grid-cols-2 gap-3">
                      <button className="flex items-center justify-center py-2 px-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors">
                        <Save className="w-4 h-4 mr-2" /> Zapisz draft
                      </button>
                      <PDFDownloadLink
                        document={<BrochurePDFDocument data={brochureData} images={images} hiddenItems={hiddenItems} notes={notes} />}
                        fileName={`Broszura_${brochureData.vehicle_name?.brand}_${brochureData.vehicle_name?.model}.pdf`}
                        className="flex items-center justify-center py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium shadow-md shadow-blue-900/20 transition-all"
                      >
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {({ loading }: any) =>
                          loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generowanie...</> : <><Download className="w-4 h-4 mr-2" /> Pobierz PDF</>
                        }
                      </PDFDownloadLink>
                   </div>
                </div>
              </div>

            </div>
          ) : (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
              <p className="text-red-600 font-medium">Brak danych broszury.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
