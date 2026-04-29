import { useState, useRef } from "react";
import { Loader2, Mail, Mic, Square, FileText } from "lucide-react";
import type { VoiceRecState } from "../hooks/useVoiceExtraction";

type InputTab = "search" | "email";

interface VertexExtractAreaProps {
  extractionText: string;
  setExtractionText: (val: string) => void;
  extracting: boolean;
  handleExtraction: () => void;
  onEmailFileExtract?: (file: File) => void;
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
  onEmailFileExtract,
  emailFileExtracting,
  voice,
}: VertexExtractAreaProps) {
  const [activeTab, setActiveTab] = useState<InputTab>("search");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isRecording = voice?.recState === "recording";
  const isPreparing = voice?.recState === "requesting" || voice?.recState === "uploading";
  const micDisabled = !voice || isPreparing || extracting;
  const isEmailMode = activeTab === "email";

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onEmailFileExtract) {
      onEmailFileExtract(file);
    }
    e.target.value = "";
  };

  return (
    <div className="mb-6 bg-white border border-slate-200 rounded-lg shadow-sm p-5">
      {/* Tab switcher */}
      <div className="flex items-center gap-1 mb-4 bg-slate-100 rounded-lg p-1 w-fit">
        <button
          type="button"
          onClick={() => setActiveTab("search")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === "search"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 hover:bg-slate-200"
          }`}
        >
          <Mic className="w-3 h-3" />
          Zapytanie / Głos
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("email")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === "email"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-600 hover:bg-slate-200"
          }`}
        >
          <Mail className="w-3 h-3" />
          Email klienta
        </button>
      </div>

      {/* Header */}
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
          {isEmailMode ? "Analiza maila flotowego" : "AI Feature Extractor"}
        </h2>
        <p className="text-xs text-slate-600 mt-1 max-w-2xl">
          {isEmailMode
            ? "Wklej całą treść maila od klienta — temat, treść, wymagania. LLM wyciągnie z niego zapytanie o samochód i automatycznie ustawi filtry."
            : "Wklej fragment zapytania przetargowego (SIWZ) lub specyfikację — albo kliknij mikrofon i powiedz po polsku. Aplikacja zmapuje synonimy i wyklika filtry poniżej."}
        </p>
      </div>

      {/* Input area */}
      <div className="flex gap-3">
        <div className="relative w-full">
          <textarea
            value={extractionText}
            onChange={(e) => setExtractionText(e.target.value)}
            placeholder={
              isEmailMode
                ? "Wklej tutaj pełną treść maila od klienta (temat + treść)...\n\nNp. Temat: Zapytanie ofertowe — flota 10 aut\n\nDzień dobry, poszukujemy 10 samochodów segmentu C/D do floty. Wymagania: napęd 4x4, automat, minimalny rocznik 2023, hak holowniczy, max rata 2500 PLN netto/mc..."
                : "Np. Potrzebuję SUVa, koniecznie napęd 4x4, automat, rocznik min 2021, biały, hak, klimatyzacja automatyczna, czujniki parkowania..."
            }
            className={`w-full text-xs p-3 border border-slate-300 hover:border-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100 rounded-md outline-none resize-none bg-white transition-colors ${
              isEmailMode ? "h-40 pr-3" : "h-24 pr-10"
            }`}
            disabled={isRecording || voice?.recState === "uploading" || emailFileExtracting}
          />
          {/* Mic button — only in search mode */}
          {!isEmailMode && voice && (
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
          {!isEmailMode && voice && isRecording && (
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
      {!isEmailMode && voice?.recState === "uploading" && (
        <p className="text-xs text-blue-700 mt-2 inline-flex items-center gap-1.5">
          <Loader2 className="w-3 h-3 animate-spin" /> Analizuję nagranie...
        </p>
      )}
      {!isEmailMode && voice?.recState === "error" && voice.error && (
        <p className="text-xs text-red-700 mt-2">{voice.error}</p>
      )}

      {/* Action row */}
      <div className="flex items-center justify-between mt-3">
        {/* File upload — only in email mode */}
        {isEmailMode && onEmailFileExtract ? (
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".msg,.eml"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={emailFileExtracting || extracting}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-700 border border-slate-300 rounded-md hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white"
            >
              {emailFileExtracting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <FileText className="w-3.5 h-3.5" />
              )}
              {emailFileExtracting ? "Wczytuję plik..." : "Wgraj plik .msg / .eml"}
            </button>
            <span className="text-[10px] text-slate-400">lub wklej tekst obok →</span>
          </div>
        ) : (
          <div />
        )}

        <button
          onClick={handleExtraction}
          disabled={
            extracting ||
            !extractionText.trim() ||
            isRecording ||
            voice?.recState === "uploading" ||
            emailFileExtracting
          }
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {extracting ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Analizowanie...</>
          ) : isEmailMode ? (
            <><Mail className="w-4 h-4" /> Analizuj maila</>
          ) : (
            <>Auto-Wyklikanie z Tekstu</>
          )}
        </button>
      </div>
    </div>
  );
}
