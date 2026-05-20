import { useEffect, useRef, useState } from "react";
import { Loader2, X, Download } from "lucide-react";
import type { FleetVehicleView } from "../../types";
import { HeroSection, type BrochureImage } from "./HeroSection";
import { TechSpecsSection } from "./TechSpecsSection";
import { EquipmentToggleSection } from "./EquipmentToggleSection";
import { NotesSection } from "./NotesSection";
import { pdf, PDFViewer } from "@react-pdf/renderer";
import { BrochurePDFDocument } from "./BrochurePDFDocument";
import type { BrochureData } from "./buildBrochureData";

const VEHICLE_NAME_FIELDS = new Set([
  "brand",
  "model",
  "edition",
  "engine",
  "body_type",
  "horsepower",
]);

export default function BrochureBuilderModal({
  vehicle,
  initialBrochureData,
  initialImages = [],
  onClose,
}: {
  vehicle: FleetVehicleView;
  initialBrochureData: BrochureData;
  initialImages?: string[];
  onClose: () => void;
}) {
  // Persist user edits (hidden items, annotation, images, field tweaks) per vehicle
  // in localStorage so they survive closing the modal. No DB write — the spec itself
  // is always regenerated fresh from the vehicle row; only manual touches are stored.
  const storageKey = `brochure_draft_${vehicle.id}`;
  const draft = useRef<Partial<{
    brochureData: BrochureData;
    images: BrochureImage[];
    hiddenItems: string[];
    notes: string;
  }>>(
    (() => {
      try {
        const raw = localStorage.getItem(storageKey);
        return raw ? JSON.parse(raw) : {};
      } catch {
        return {};
      }
    })(),
  ).current;

  const [brochureData, setBrochureData] = useState<BrochureData>(draft.brochureData ?? initialBrochureData);
  const [images, setImages] = useState<BrochureImage[]>(
    draft.images && draft.images.length
      ? draft.images
      : initialImages.map((url, i) => ({ id: `ext-${i}`, url, isMain: i === 0 })),
  );
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(new Set(draft.hiddenItems ?? []));
  const [notes, setNotes] = useState<string>(draft.notes ?? "");
  const [pdfDownloading, setPdfDownloading] = useState(false);

  useEffect(() => {
    // Drop blob: URLs (local uploads can't survive a reload); keep http(s) extracted/AI images.
    const persistImages = images.filter((i) => /^https?:/i.test(i.url));
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({ brochureData, images: persistImages, hiddenItems: [...hiddenItems], notes }),
      );
    } catch {
      // localStorage full / unavailable — non-critical.
    }
  }, [brochureData, images, hiddenItems, notes, storageKey]);

  // TechSpecsSection edits vehicle_name fields plus top-level transmission/drive_type.
  const handleTechSpecsChange = (field: string, value: string) => {
    setBrochureData((prev) => {
      if (VEHICLE_NAME_FIELDS.has(field)) {
        return { ...prev, vehicle_name: { ...prev.vehicle_name, [field]: value } };
      }
      return { ...prev, [field]: value };
    });
  };

  const handleIdentifierChange = (field: "offer_number" | "configuration_code" | "vin", value: string) => {
    setBrochureData((prev) => ({ ...prev, [field]: value }));
  };

  const handleEquipmentToggle = (catIndex: number, itemIdx: number) => {
    const key = `${catIndex}-${itemIdx}`;
    setHiddenItems((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const downloadPdf = async () => {
    setPdfDownloading(true);
    try {
      const blob = await pdf(
        <BrochurePDFDocument data={brochureData} images={images} hiddenItems={hiddenItems} notes={notes} />,
      ).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Broszura_${brochureData.vehicle_name.brand}_${brochureData.vehicle_name.model}.pdf`.replace(
        /\s+/g,
        "_",
      );
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Błąd generowania PDF: ${err instanceof Error ? err.message : err}`);
    } finally {
      setPdfDownloading(false);
    }
  };

  const identifierFields: { key: "offer_number" | "configuration_code" | "vin"; label: string }[] = [
    { key: "offer_number", label: "Numer oferty" },
    { key: "configuration_code", label: "Numer konfiguracji" },
    { key: "vin", label: "VIN (jeśli wyprodukowane)" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden ring-1 ring-slate-900/5">
        <header className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <span className="text-2xl">📄</span> Kreator Broszury — Express Fleet Partner
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Dostosuj dane i wygeneruj plik PDF dla klienta — {vehicle.brand} {vehicle.model}
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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Kolumna lewa: Edytor */}
            <div className="lg:col-span-2 space-y-6">
              <HeroSection images={images} setImages={setImages} vehicleId={vehicle.id} />

              {/* Identyfikatory */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="font-semibold text-slate-800 mb-4">Identyfikatory oferty</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {identifierFields.map(({ key, label }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-slate-500 font-medium">{label}</label>
                      <input
                        type="text"
                        value={brochureData[key] ?? ""}
                        onChange={(e) => handleIdentifierChange(key, e.target.value)}
                        className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <TechSpecsSection
                vehicleData={brochureData.vehicle_name}
                brochureData={brochureData}
                onChange={handleTechSpecsChange}
              />
              <EquipmentToggleSection
                categories={brochureData.equipment_categories}
                hiddenItems={hiddenItems}
                onToggleItem={handleEquipmentToggle}
              />
              <NotesSection notes={notes} onChange={setNotes} />
            </div>

            {/* Kolumna prawa: Podgląd PDF */}
            <div className="lg:col-span-1">
              <div className="sticky top-6 bg-slate-800 rounded-xl p-4 shadow-lg text-white flex flex-col h-[700px]">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-slate-200 text-sm">Podgląd dokumentu</h3>
                </div>
                <div
                  className="flex-1 overflow-hidden relative"
                  style={{ borderRadius: "8px", border: "none", backgroundColor: "#fff" }}
                >
                  <PDFViewer width="100%" height="100%" className="border-0 rounded-lg" showToolbar={false}>
                    <BrochurePDFDocument
                      data={brochureData}
                      images={images}
                      hiddenItems={hiddenItems}
                      notes={notes}
                    />
                  </PDFViewer>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-700 flex justify-end gap-3">
                  <button
                    onClick={() => void downloadPdf()}
                    disabled={pdfDownloading}
                    className="flex items-center justify-center py-2 px-6 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:text-white/50 text-white rounded-lg text-sm font-medium shadow-md shadow-blue-900/20 transition-all w-full"
                  >
                    {pdfDownloading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generowanie...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4 mr-2" /> Pobierz PDF
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
