import { Loader2 } from "lucide-react";

interface VertexExtractAreaProps {
  extractionText: string;
  setExtractionText: (val: string) => void;
  extracting: boolean;
  handleExtraction: () => void;
}

export function VertexExtractArea({
  extractionText,
  setExtractionText,
  extracting,
  handleExtraction
}: VertexExtractAreaProps) {
  return (
    <div className="mb-6 bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-100 rounded-xl p-5 shadow-sm">
      <div className="mb-3">
        <h2 className="text-sm font-bold text-indigo-900 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
          AI Feature Extractor
        </h2>
        <p className="text-[11px] text-indigo-700 mt-1 max-w-2xl">
          Wklej treść maila od klienta, fragment zapytania przetargowego (SIWZ) lub specyfikację. Aplikacja przeanalizuje tekst, zmapuje synonimy (np. &quot;navigacja&quot; → &quot;System nawigacji satelitarnej&quot;) i automatycznie wyklika potrzebne filtry poniżej.
        </p>
      </div>
      <div className="flex gap-3">
        <textarea 
          value={extractionText}
          onChange={(e) => setExtractionText(e.target.value)}
          placeholder="Np. Potrzebuję SUVa, koniecznie napęd 4x4, automat, rocznik min 2021, biały, hak, klimatyzacja automatyczna, czujniki parkowania..."
          className="w-full h-24 text-xs p-3 border border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none bg-white/80 backdrop-blur-sm"
        />
      </div>
      <div className="flex justify-end mt-3">
        <button 
          onClick={handleExtraction}
          disabled={extracting || !extractionText.trim()}
          className="px-5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-all shadow-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {extracting ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin"/> Analizowanie...</>
          ) : (
            <>Auto-Wyklikanie z Tekstu</>
          )}
        </button>
      </div>
    </div>
  );
}
