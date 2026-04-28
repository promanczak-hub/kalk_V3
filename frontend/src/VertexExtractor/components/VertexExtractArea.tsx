import { Loader2, Mic, Square } from "lucide-react";
import type { VoiceRecState } from "../hooks/useVoiceExtraction";

interface VertexExtractAreaProps {
  extractionText: string;
  setExtractionText: (val: string) => void;
  extracting: boolean;
  handleExtraction: () => void;
  voice?: {
    recState: VoiceRecState;
    error: string | null;
    elapsedSec: number;
    maxSeconds: number;
    startRecording: () => void;
    stopRecording: () => void;
  };
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function VertexExtractArea({
  extractionText,
  setExtractionText,
  extracting,
  handleExtraction,
  voice,
}: VertexExtractAreaProps) {
  const isRecording = voice?.recState === "recording";
  const isPreparing = voice?.recState === "requesting" || voice?.recState === "uploading";
  const micDisabled = !voice || isPreparing || extracting;

  return (
    <div className="mb-6 bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-100 rounded-xl p-5 shadow-sm">
      <div className="mb-3">
        <h2 className="text-sm font-bold text-indigo-900 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
          AI Feature Extractor
        </h2>
        <p className="text-[11px] text-indigo-700 mt-1 max-w-2xl">
          Wklej treść maila od klienta, fragment zapytania przetargowego (SIWZ) lub specyfikację — albo kliknij mikrofon i powiedz po polsku. Aplikacja przeanalizuje wejście, zmapuje synonimy (np. &quot;navigacja&quot; → &quot;System nawigacji satelitarnej&quot;) i automatycznie wyklika potrzebne filtry poniżej.
        </p>
      </div>
      <div className="flex gap-3">
        <div className="relative w-full">
          <textarea
            value={extractionText}
            onChange={(e) => setExtractionText(e.target.value)}
            placeholder="Np. Potrzebuję SUVa, koniecznie napęd 4x4, automat, rocznik min 2021, biały, hak, klimatyzacja automatyczna, czujniki parkowania..."
            className="w-full h-24 text-xs p-3 pr-10 border border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none bg-white/80 backdrop-blur-sm"
            disabled={isRecording || voice?.recState === "uploading"}
          />
          {voice && (
            <button
              type="button"
              onClick={isRecording ? voice.stopRecording : voice.startRecording}
              disabled={micDisabled}
              title={isRecording ? "Zatrzymaj nagrywanie" : "Nagraj wypowiedź (max 60s)"}
              aria-label={isRecording ? "Zatrzymaj nagrywanie" : "Nagraj wypowiedź"}
              className="absolute bottom-2 right-2 p-1.5 rounded-md bg-white border border-indigo-200 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {voice.recState === "uploading" || voice.recState === "requesting" ? (
                <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
              ) : isRecording ? (
                <Square className="w-4 h-4 text-red-600 fill-red-600" />
              ) : (
                <Mic className="w-4 h-4 text-indigo-600" />
              )}
            </button>
          )}
          {voice && isRecording && (
            <div className="absolute top-2 right-2 flex items-center gap-1.5 text-[11px] text-red-600 bg-white/90 px-2 py-0.5 rounded-md shadow-sm">
              <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
              <span className="font-mono">
                {formatTime(voice.elapsedSec)} / {formatTime(voice.maxSeconds)}
              </span>
            </div>
          )}
        </div>
      </div>
      {voice?.recState === "uploading" && (
        <p className="text-[11px] text-indigo-700 mt-1.5 flex items-center gap-1.5">
          <Loader2 className="w-3 h-3 animate-spin" /> Analizuję nagranie...
        </p>
      )}
      {voice?.recState === "error" && voice.error && (
        <p className="text-[11px] text-red-600 mt-1.5">{voice.error}</p>
      )}
      <div className="flex justify-end mt-3">
        <button
          onClick={handleExtraction}
          disabled={extracting || !extractionText.trim() || isRecording || voice?.recState === "uploading"}
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
