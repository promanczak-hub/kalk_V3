import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import { Loader2, AlertCircle } from "lucide-react";
import { API_BASE_URL } from "../../../config/env";
import { supabase } from "../../../lib/supabaseClient";

// Inicjalizacja workera PDF.js - lokalny import (nie CDN)
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

interface PDFViewerFrameProps {
  url: string;
}

export function PDFViewerFrame({ url }: PDFViewerFrameProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [loadingPage, setLoadingPage] = useState<number | null>(null);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const activeTasks: pdfjsLib.RenderTask[] = [];

    const loadPdf = async () => {
      setLoading(true);
      setError(null);
      setTotalPages(0);

      // Clear previously rendered canvases
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }

      try {
        // Fetch Supabase session to authenticate the request against our backend
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;

        const safeUrl = url.startsWith("http")
          ? `${API_BASE_URL}/api/pdf-proxy?url=${encodeURIComponent(url)}`
          : url;

        const pdf = await pdfjsLib.getDocument({
          url: safeUrl,
          httpHeaders: token ? { Authorization: `Bearer ${token}` } : undefined,
        }).promise;
        if (!isMounted) return;

        const numPages = pdf.numPages;
        setTotalPages(numPages);

        // Render each page sequentially
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
          if (!isMounted) break;
          setLoadingPage(pageNum);

          const page = await pdf.getPage(pageNum);
          if (!isMounted) break;

          const viewport = page.getViewport({ scale: 1.5 });
          const canvas = document.createElement("canvas");
          canvas.height = viewport.height;
          canvas.width = viewport.width;
          canvas.className = "w-full shadow-sm border border-slate-200 rounded";

          containerRef.current?.appendChild(canvas);

          const context = canvas.getContext("2d");
          if (!context) continue;

          const renderTask = page.render({ canvasContext: context, viewport } as any);
          activeTasks.push(renderTask);
          await renderTask.promise;
        }

        if (isMounted) {
          setLoading(false);
          setLoadingPage(null);
        }
      } catch (err) {
        console.error("PDF load error:", err);
        if (isMounted) {
          setError(
            "Nie udało się załadować pliku PDF. Prawdopodobnie wystąpił problem z CORS lub plik jest uszkodzony."
          );
          setLoading(false);
          setLoadingPage(null);
        }
      }
    };

    loadPdf();

    return () => {
      isMounted = false;
      activeTasks.forEach((t) => t.cancel());
    };
  }, [url]);

  return (
    <div className="w-full bg-slate-100 rounded-lg border border-slate-200 overflow-auto relative">
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 bg-white/80 z-10">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-2" />
          <span className="text-sm text-slate-600 font-medium">
            {loadingPage && totalPages
              ? `Ładowanie strony ${loadingPage} z ${totalPages}...`
              : "Ładowanie dokumentu..."}
          </span>
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center justify-center py-16 p-6 text-center bg-white">
          <AlertCircle className="w-10 h-10 text-red-500 mb-3" />
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Błąd podglądu PDF</h3>
          <p className="text-xs text-slate-500 max-w-sm">{error}</p>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 px-4 py-2 bg-slate-900 text-white text-xs font-medium rounded hover:bg-slate-800 transition-colors"
          >
            Pobierz plik ręcznie
          </a>
        </div>
      )}

      {/* Kontener na canvas-e — każda strona PDF to osobny element */}
      <div ref={containerRef} className="flex flex-col gap-2 p-2" />
    </div>
  );
}
