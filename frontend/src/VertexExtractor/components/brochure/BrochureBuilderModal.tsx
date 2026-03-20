import { useState, useEffect, useCallback, useRef } from "react";
import { Loader2, X, Download, Save, RefreshCw } from "lucide-react";
import type { FleetVehicleView } from "../../types";
import { HeroSection, type BrochureImage } from "./HeroSection";
import { TechSpecsSection } from "./TechSpecsSection";
import { EquipmentToggleSection } from "./EquipmentToggleSection";
import { NotesSection } from "./NotesSection";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

interface EquipmentCategory {
  category_name: string;
  items: string[];
}

function buildRequestPayload(
  brochureData: Record<string, unknown>,
  images: BrochureImage[],
  hiddenItems: Set<string>,
  notes: string
) {
  const vn = (brochureData.vehicle_name ?? {}) as Record<string, unknown>;
  const rawCategories = (brochureData.equipment_categories ?? []) as Array<{
    category_name: string;
    items: string[];
  }>;

  const equipment_categories: EquipmentCategory[] = rawCategories
    .map((cat, cIdx) => ({
      category_name: cat.category_name ?? "Inne",
      items: (cat.items ?? []).filter(
        (_: string, iIdx: number) => !hiddenItems.has(`${cIdx}-${iIdx}`)
      ),
    }))
    .filter((cat) => cat.items.length > 0);

  const mainImage = images.find((i) => i.isMain) ?? images[0];

  return {
    brand: String(vn.brand ?? ""),
    model: String(vn.model ?? ""),
    trim_level: String(vn.edition ?? "") || null,
    engine_description: String(vn.engine ?? "") || null,
    power_hp: vn.horsepower ? parseInt(String(vn.horsepower), 10) || null : null,
    body_type: String(vn.body_type ?? "") || null,
    transmission: String(brochureData.transmission ?? "") || null,
    drive_type: String(brochureData.drive_type ?? "") || null,
    hero_image_url: mainImage?.url ?? null,
    equipment_categories,
    notes: notes.trim() || null,
  };
}

export default function BrochureBuilderModal({
  vehicle,
  initialBrochureData,
  initialImages = [],
  onClose,
}: {
  vehicle: FleetVehicleView;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  initialBrochureData: any;
  initialImages?: string[];
  onClose: () => void;
}) {
  const buildVehicleName = (data: Record<string, unknown>) => ({
    brand: data?.brand ?? "",
    model: data?.model ?? "",
    edition: data?.trim_level ?? "",
    engine: data?.engine_description ?? "",
    body_type: data?.body_type ?? "",
    horsepower: data?.power_hp ? String(data.power_hp) : "",
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [brochureData, setBrochureData] = useState<any | null>(
    initialBrochureData
      ? { ...initialBrochureData, vehicle_name: buildVehicleName(initialBrochureData) }
      : null
  );

  const [images, setImages] = useState<BrochureImage[]>(
    initialImages.map((url, i) => ({ id: `ext-${i}`, url, file: null, isMain: false }))
  );
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState<string>("");

  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const FIELD_TO_FLAT: Record<string, string> = {
    brand: "brand",
    model: "model",
    edition: "trim_level",
    engine: "engine_description",
    body_type: "body_type",
    horsepower: "power_hp",
    transmission: "transmission",
  };

  const handleTechSpecsChange = (field: string, value: string) => {
    if (!brochureData) return;
    const flatKey = FIELD_TO_FLAT[field] ?? field;
    setBrochureData({
      ...brochureData,
      [flatKey]: flatKey === "power_hp" ? (parseInt(value, 10) || null) : value,
      vehicle_name: { ...brochureData.vehicle_name, [field]: value },
    });
  };

  const handleEquipmentToggle = (catIndex: number, itemIdx: number) => {
    const key = `${catIndex}-${itemIdx}`;
    const newSet = new Set(hiddenItems);
    if (newSet.has(key)) newSet.delete(key);
    else newSet.add(key);
    setHiddenItems(newSet);
  };

  const fetchPreview = useCallback(async () => {
    if (!brochureData) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const payload = buildRequestPayload(brochureData, images, hiddenItems, notes);
      const res = await fetch(`${API_BASE}/api/brochure/preview-html`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      setPreviewHtml(await res.text());
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Błąd pobierania podglądu");
    } finally {
      setPreviewLoading(false);
    }
  }, [brochureData, images, hiddenItems, notes]);

  // Debounced auto-refresh on data changes
  useEffect(() => {
    if (!brochureData) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { void fetchPreview(); }, 600);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [fetchPreview, brochureData]);

  const downloadPdf = async () => {
    if (!brochureData) return;
    setPdfDownloading(true);
    try {
      const payload = buildRequestPayload(brochureData, images, hiddenItems, notes);
      const res = await fetch(`${API_BASE}/api/brochure/generate-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Broszura_${brochureData.vehicle_name?.brand ?? ""}_${brochureData.vehicle_name?.model ?? ""}.pdf`.replace(/\s+/g, "_");
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Błąd generowania PDF: ${err instanceof Error ? err.message : err}`);
    } finally {
      setPdfDownloading(false);
    }
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
              Dostosuj dane i wygeneruj czysty plik PDF dla klienta — {vehicle.brand} {vehicle.model}
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
              {/* Kolumna lewa: Edytor */}
              <div className="lg:col-span-2 space-y-6">
                <HeroSection images={images} setImages={setImages} />
                <TechSpecsSection vehicleData={brochureData.vehicle_name} brochureData={brochureData} onChange={handleTechSpecsChange} />
                <EquipmentToggleSection categories={brochureData.equipment_categories} hiddenItems={hiddenItems} onToggleItem={handleEquipmentToggle} />
                <NotesSection notes={notes} onChange={setNotes} />
              </div>

              {/* Kolumna prawa: Podgląd HTML */}
              <div className="lg:col-span-1">
                <div className="sticky top-6 bg-slate-800 rounded-xl p-4 shadow-lg text-white flex flex-col h-[700px]">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-slate-200 text-sm">Podgląd dokumentu</h3>
                    <button
                      onClick={() => void fetchPreview()}
                      disabled={previewLoading}
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
                      title="Odśwież podgląd"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${previewLoading ? "animate-spin" : ""}`} />
                    </button>
                  </div>

                  <div className="flex-1 bg-white rounded-lg overflow-hidden relative">
                    {previewLoading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                        <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                      </div>
                    )}
                    {previewError && !previewLoading && (
                      <div className="absolute inset-0 flex items-center justify-center p-4">
                        <p className="text-red-500 text-xs text-center">{previewError}</p>
                      </div>
                    )}
                    {previewHtml && !previewError && (
                      <iframe
                        srcDoc={previewHtml}
                        className="w-full h-full border-0"
                        style={{ transform: "scale(0.63)", transformOrigin: "top left", width: "159%", height: "159%" }}
                        title="Podgląd broszury"
                        sandbox="allow-same-origin"
                      />
                    )}
                    {!previewHtml && !previewLoading && !previewError && (
                      <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-xs">
                        Wczytywanie podglądu...
                      </div>
                    )}
                  </div>

                  <div className="mt-4 pt-4 border-t border-slate-700 grid grid-cols-2 gap-3">
                    <button
                      onClick={() => void fetchPreview()}
                      className="flex items-center justify-center py-2 px-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      <Save className="w-4 h-4 mr-2" /> Odśwież
                    </button>
                    <button
                      onClick={() => void downloadPdf()}
                      disabled={pdfDownloading}
                      className="flex items-center justify-center py-2 px-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:text-white/50 text-white rounded-lg text-sm font-medium shadow-md shadow-blue-900/20 transition-all"
                    >
                      {pdfDownloading
                        ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generowanie...</>
                        : <><Download className="w-4 h-4 mr-2" /> Pobierz PDF</>
                      }
                    </button>
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
