import { Loader2, Mic, Square } from "lucide-react";
import type { VoiceRecState } from "../hooks/useVoiceExtraction";

interface VertexExtractAreaProps {
  extractionText: string;
  setExtractionText: (val: string) => void;
  extracting: boolean;
  handleExtraction: () => void;
  /** Optional — kept for backward compatibility, no longer used in UI. */
  onEmailFileExtract?: (file: File) => void;
  /** Optional — kept for backward compatibility, no longer used in UI. */
  emailFileExtracting?: boolean;
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
    <div className="mb-6 bg-white border border-slate-200 rounded-lg shadow-sm p-5">
      {/* Header */}
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
          AI Feature Extractor
        </h2>
        <p className="text-xs text-slate-600 mt-1 max-w-2xl">
          Wklej fragment zapytania, treść maila lub specyfikację — albo kliknij mikrofon i powiedz po polsku. Aplikacja zmapuje synonimy i wyklika filtry poniżej.
        </p>
      </div>

      {/* Input area */}
      <div className="flex gap-3">
        <div className="relative w-full">
          <textarea
            value={extractionText}
            onChange={(e) => setExtractionText(e.target.value)}
            placeholder="Np. Potrzebuję SUVa, koniecznie napęd 4x4, automat, rocznik min 2021, biały, hak, klimatyzacja automatyczna, czujniki parkowania..."
            className="w-full h-24 text-xs p-3 pr-10 border border-slate-300 hover:border-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100 rounded-md outline-none resize-none bg-white transition-colors"
            disabled={isRecording || voice?.recState === "uploading"}
          />
          {/* Mic button — Material FAB */}
          {voice && (
            <button
              type="button"
              onClick={isRecording ? voice.stopRecording : voice.startRecording}
              disabled={micDisabled}
              title={isRecording ? "Zatrzymaj nagrywanie" : "Nagraj wypowiedź (max 60s)"}
              aria-label={isRecording ? "Zatrzymaj nagrywanie" : "Nagraj wypowiedź"}
              className="absolute bottom-2 right-2 p-2 rounded-full bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {voice.recState === "uploading" || voice.recState === "requesting" ? (
                <Loader2 className="w-4 h-4 text-white animate-spin" />
              ) : isRecording ? (
                <Square className="w-4 h-4 text-white fill-white" />
              ) : (
                <Mic className="w-4 h-4 text-white" />
              )}
            </button>
          )}
          {voice && isRecording && (
            <div className="absolute top-2 right-2 inline-flex items-center gap-1.5 text-[11px] text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full shadow-sm">
              <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
              <span className="font-mono font-semibold tabular-nums">
                {formatTime(voice.elapsedSec)} / {formatTime(voice.maxSeconds)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Voice status messages */}
      {voice?.recState === "uploading" && (
        <p className="text-xs text-blue-700 mt-2 inline-flex items-center gap-1.5">
          <Loader2 className="w-3 h-3 animate-spin" /> Analizuję nagranie...
        </p>
      )}
      {voice?.recState === "error" && voice.error && (
        <p className="text-xs text-red-700 mt-2">{voice.error}</p>
      )}

      {/* Action row */}
      <div className="flex items-center justify-end mt-3">
        <button
          onClick={handleExtraction}
          disabled={
            extracting ||
            !extractionText.trim() ||
            isRecording ||
            voice?.recState === "uploading"
          }
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {extracting ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Analizowanie...</>
          ) : (
            <>Auto-Wyklikanie z Tekstu</>
          )}
        </button>
      </div>
    </div>
  );
}
