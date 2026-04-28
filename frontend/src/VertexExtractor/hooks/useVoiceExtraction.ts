import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../../config/env";
import type { CatalogCategory } from "../types";
import { apiClient } from "../../lib/apiClient";
import {
  applyExtractionResult,
  type ExtractionResponse,
  type ExtractionSuccessHandler,
} from "./useVertexExtraction";

export type VoiceRecState =
  | "idle"
  | "requesting"
  | "recording"
  | "uploading"
  | "error";

const MAX_RECORDING_SECONDS = 60;
const PREFERRED_MIME = "audio/webm;codecs=opus";

function pickRecorderMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  if (MediaRecorder.isTypeSupported(PREFERRED_MIME)) return PREFERRED_MIME;
  if (MediaRecorder.isTypeSupported("audio/webm")) return "audio/webm";
  if (MediaRecorder.isTypeSupported("audio/mp4")) return "audio/mp4";
  return undefined;
}

export function useVoiceExtraction(
  catalog: CatalogCategory[],
  onExtractionSuccess: ExtractionSuccessHandler,
  setExtractionText: (val: string) => void
) {
  const [recState, setRecState] = useState<VoiceRecState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const autoStopRef = useRef<number | null>(null);
  const mimeRef = useRef<string | undefined>(undefined);

  const cleanupStream = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (autoStopRef.current !== null) {
      window.clearTimeout(autoStopRef.current);
      autoStopRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    recorderRef.current = null;
    chunksRef.current = [];
  }, []);

  useEffect(() => cleanupStream, [cleanupStream]);

  const uploadBlob = useCallback(
    async (blob: Blob, mimeType: string) => {
      setRecState("uploading");
      const formData = new FormData();
      const ext = mimeType.includes("mp4") ? "m4a" : mimeType.includes("ogg") ? "ogg" : "webm";
      formData.append("audio", blob, `recording.${ext}`);

      try {
        const res = await apiClient.fetch(
          `${API_BASE_URL}/api/features/extract-audio`,
          { method: "POST", body: formData, skipGlobalError: true }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: ExtractionResponse = await res.json();

        if (data.transcript) setExtractionText(data.transcript);

        const applied = applyExtractionResult(data, catalog, onExtractionSuccess);
        if (!applied || (data.extracted_filters?.length ?? 0) === 0) {
          if (!data.transcript) {
            setError("Nie zrozumiałem nagrania — spróbuj jeszcze raz lub wpisz tekst.");
            setRecState("error");
            return;
          }
        }
        setRecState("idle");
        setError(null);
      } catch (err) {
        console.error("Voice extraction failed:", err);
        setError(
          err instanceof Error
            ? `Nie udało się wysłać nagrania: ${err.message}`
            : "Nie udało się wysłać nagrania."
        );
        setRecState("error");
      }
    },
    [catalog, onExtractionSuccess, setExtractionText]
  );

  const startRecording = useCallback(async () => {
    if (recState === "recording" || recState === "requesting" || recState === "uploading") return;
    setError(null);
    setElapsedSec(0);

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("Twoja przeglądarka nie obsługuje nagrywania audio.");
      setRecState("error");
      return;
    }

    setRecState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mime = pickRecorderMime();
      mimeRef.current = mime;
      const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const usedMime = mimeRef.current || recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: usedMime });
        cleanupStream();
        if (blob.size === 0) {
          setError("Puste nagranie — spróbuj ponownie.");
          setRecState("error");
          return;
        }
        void uploadBlob(blob, usedMime);
      };

      recorder.onerror = () => {
        cleanupStream();
        setError("Błąd nagrywania audio.");
        setRecState("error");
      };

      recorder.start();
      setRecState("recording");

      timerRef.current = window.setInterval(() => {
        setElapsedSec((s) => s + 1);
      }, 1000);

      autoStopRef.current = window.setTimeout(() => {
        if (recorderRef.current && recorderRef.current.state === "recording") {
          recorderRef.current.stop();
        }
      }, MAX_RECORDING_SECONDS * 1000);
    } catch (err) {
      cleanupStream();
      const name = err instanceof Error ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setError("Brak dostępu do mikrofonu — wpisz tekst ręcznie.");
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setError("Nie znaleziono mikrofonu.");
      } else {
        setError("Nie udało się rozpocząć nagrywania.");
      }
      setRecState("error");
    }
  }, [recState, cleanupStream, uploadBlob]);

  const stopRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.stop();
    }
  }, []);

  const reset = useCallback(() => {
    cleanupStream();
    setRecState("idle");
    setError(null);
    setElapsedSec(0);
  }, [cleanupStream]);

  return {
    recState,
    error,
    elapsedSec,
    startRecording,
    stopRecording,
    reset,
    maxSeconds: MAX_RECORDING_SECONDS,
  };
}
