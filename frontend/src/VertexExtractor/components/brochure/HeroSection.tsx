import { useState, useRef } from "react";
import { ImagePlus, Trash2, Star, Sparkles, Loader2, Wand2, X } from "lucide-react";
import { API_BASE_URL } from "../../../config/env";
import { apiClient } from "../../../lib/apiClient";

export interface BrochureImage {
  id: string;
  url: string;
  isMain: boolean;
  aiGenerated?: boolean;
}

interface HeroSectionProps {
  images: BrochureImage[];
  setImages: React.Dispatch<React.SetStateAction<BrochureImage[]>>;
  vehicleId: string;
}

// Gotowe podpowiedzi promptu — najczęstsze potrzeby dla broszur.
const EDIT_PRESETS = [
  "Wyczyść tło, białe studio",
  "Usuń tablice rejestracyjne",
  "Ujęcie 3/4 z prawej strony",
  "Popraw ostrość, jasność i kontrast",
];
const GENERATE_PRESETS = [
  "Zdjęcie studyjne samochodu na białym tle, ujęcie 3/4 z przodu",
  "Samochód na nowoczesnym salonie, miękkie oświetlenie",
];

const isHttpUrl = (url: string) => /^https?:\/\//i.test(url);

export function HeroSection({ images, setImages, vehicleId }: HeroSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  // null = panel zamknięty; "new" = generowanie; inny string = id edytowanego zdjęcia
  const [aiPanel, setAiPanel] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const validFiles = Array.from(e.target.files).filter(
        (file) => file.type === "image/jpeg" || file.type === "image/png" || file.type === "image/jpg",
      );
      if (validFiles.length !== e.target.files.length) {
        alert("Pominięto formaty nieobsługiwane przez kreator PDF (np. WebP, SVG). Wgrywaj wyłącznie JPG lub PNG.");
      }
      if (validFiles.length === 0) return;
      const newImages = validFiles.map((file) => ({
        id: crypto.randomUUID(),
        url: URL.createObjectURL(file),
        isMain: images.length === 0,
      }));
      setImages((prev) => [...prev, ...newImages]);
    }
  };

  const handleRemoveImage = (id: string) => {
    setImages((prev) => {
      const filtered = prev.filter((img) => img.id !== id);
      if (filtered.length > 0 && !filtered.some((img) => img.isMain)) filtered[0].isMain = true;
      return filtered;
    });
  };

  const setMainImage = (id: string) =>
    setImages((prev) => prev.map((img) => ({ ...img, isMain: img.id === id })));

  const openPanel = (target: string) => {
    setAiPanel(target);
    setPrompt("");
    setError(null);
  };

  const runAi = async () => {
    if (!prompt.trim()) {
      setError("Wpisz prompt lub wybierz gotową podpowiedź.");
      return;
    }
    setIsProcessing(true);
    setError(null);
    try {
      const isGenerate = aiPanel === "new";
      const endpoint = isGenerate ? "/api/image/generate" : "/api/image/edit";
      const body: Record<string, string> = { vehicle_id: vehicleId, prompt: prompt.trim() };
      if (!isGenerate) {
        const src = images.find((i) => i.id === aiPanel);
        if (!src) throw new Error("Nie znaleziono zdjęcia źródłowego.");
        body.image_url = src.url;
      }
      const resp = await apiClient.fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        if (resp.status === 429) throw new Error(detail.detail || "Wyczerpano dzienny limit generacji dla tego pojazdu.");
        throw new Error(detail.detail || "Generowanie zdjęcia nie powiodło się.");
      }
      const data = await resp.json();
      setImages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), url: data.url, isMain: prev.length === 0, aiGenerated: true },
      ]);
      setAiPanel(null);
      setPrompt("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nieznany błąd generowania zdjęcia.");
    } finally {
      setIsProcessing(false);
    }
  };

  const presets = aiPanel === "new" ? GENERATE_PRESETS : EDIT_PRESETS;

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-800 flex items-center">
          <ImagePlus className="w-4 h-4 mr-2 text-indigo-500" /> Zdjęcia pojazdu
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => openPanel("new")}
            className="text-xs font-medium bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 px-3 py-1.5 rounded-lg flex items-center transition-colors"
          >
            <Wand2 className="w-3.5 h-3.5 mr-1.5" /> Wygeneruj AI
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 px-3 py-1.5 rounded-lg flex items-center transition-colors"
          >
            <ImagePlus className="w-3.5 h-3.5 mr-1.5" /> Dodaj zdjęcie
          </button>
        </div>
        <input
          type="file"
          multiple
          accept="image/png, image/jpeg, image/jpg"
          className="hidden"
          ref={fileInputRef}
          onChange={handleFileChange}
        />
      </div>

      <p className="text-xs text-slate-500 mb-4">
        Wgraj zdjęcia z oferty dealera lub użyj AI (nano-banana), aby edytować istniejące zdjęcie promptem albo
        wygenerować nowe. Edycja AI działa dla zdjęć wyciągniętych z PDF.
      </p>

      {/* Panel AI (prompt + presety) */}
      {aiPanel !== null && (
        <div className="mb-4 border border-indigo-200 rounded-lg p-4 bg-indigo-50/40">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-indigo-800 flex items-center">
              <Sparkles className="w-4 h-4 mr-1.5" />
              {aiPanel === "new" ? "Wygeneruj nowe zdjęcie" : "Edytuj zdjęcie promptem"}
            </span>
            <button onClick={() => setAiPanel(null)} className="text-slate-400 hover:text-slate-600">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {presets.map((p) => (
              <button
                key={p}
                onClick={() => setPrompt(p)}
                className="text-[11px] px-2 py-1 rounded border border-indigo-200 bg-white text-indigo-700 hover:bg-indigo-100 transition-colors"
              >
                {p}
              </button>
            ))}
          </div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={2}
            placeholder="Opisz, co AI ma zrobić ze zdjęciem…"
            className="w-full text-sm p-2 border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
          />
          {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
          <div className="flex justify-end mt-2">
            <button
              onClick={() => void runAi()}
              disabled={isProcessing}
              className="flex items-center text-xs font-medium py-2 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg transition-colors"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Przetwarzanie (5–15 s)…
                </>
              ) : (
                <>
                  <Wand2 className="w-3.5 h-3.5 mr-1.5" /> {aiPanel === "new" ? "Generuj" : "Edytuj"}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {images.length === 0 ? (
        <div className="border-2 border-dashed border-slate-200 rounded-lg p-8 flex flex-col justify-center items-center bg-slate-50/50 text-slate-400">
          <ImagePlus className="w-8 h-8 mb-2 opacity-50" />
          <p className="text-sm">Brak wgranych zdjęć.</p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="mt-3 text-xs text-indigo-600 font-medium hover:underline"
          >
            Wybierz z dysku
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {images.map((img) => (
            <div
              key={img.id}
              className={`relative group rounded-xl border-2 overflow-hidden transition-all ${
                img.isMain ? "border-indigo-500 ring-2 ring-indigo-500/20" : "border-slate-200 hover:border-indigo-300"
              }`}
            >
              <img src={img.url} alt="Vehicle preview" className="w-full h-32 object-cover" />
              {img.aiGenerated && (
                <span className="absolute top-1 left-1 bg-violet-600 text-white text-[9px] uppercase font-bold px-1.5 py-0.5 rounded shadow-sm flex items-center">
                  <Sparkles className="w-2.5 h-2.5 mr-0.5" /> AI
                </span>
              )}
              <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-2">
                <div className="flex justify-between w-full">
                  {img.isMain ? (
                    <span className="bg-indigo-600 text-white text-xs uppercase font-bold px-2 py-0.5 rounded shadow-sm flex items-center">
                      <Star className="w-3 h-3 mr-1 fill-current" /> Główne
                    </span>
                  ) : (
                    <button
                      onClick={() => setMainImage(img.id)}
                      className="bg-white/90 text-slate-700 text-xs uppercase font-bold px-2 py-0.5 rounded shadow-sm hover:bg-white"
                    >
                      Ustaw jako główne
                    </button>
                  )}
                  <button
                    onClick={() => handleRemoveImage(img.id)}
                    className="bg-red-500/90 text-white p-1 rounded hover:bg-red-600 shadow-sm"
                    title="Usuń zdjęcie"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <button
                  onClick={() => openPanel(img.id)}
                  disabled={!isHttpUrl(img.url)}
                  title={isHttpUrl(img.url) ? "Edytuj zdjęcie promptem AI" : "Edycja AI działa dla zdjęć z PDF (nie dla lokalnych uploadów)"}
                  className="w-full bg-gradient-to-r from-violet-600/90 to-indigo-600/90 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium py-1.5 rounded flex items-center justify-center shadow-sm"
                >
                  <Sparkles className="w-3 h-3 mr-1" /> Edytuj AI
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
