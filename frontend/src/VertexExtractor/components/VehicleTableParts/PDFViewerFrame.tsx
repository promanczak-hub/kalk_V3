import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import { Loader2, AlertCircle } from "lucide-react";
import { API_BASE_URL } from "../../../config/env";

// Inicjalizacja workera PDF.js
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

interface PDFViewerFrameProps {
  url: string;
}

export function PDFViewerFrame({ url }: PDFViewerFrameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let renderTask: pdfjsLib.RenderTask | null = null;
    let isMounted = true;

    const loadPdf = async () => {
      setLoading(true);
      setError(null);

      try {
        const safeUrl = url.startsWith("http")
          ? `${API_BASE_URL || ""}/api/pdf-proxy?url=${encodeURIComponent(url)}`
          : url;
        const loadingTask = pdfjsLib.getDocument(safeUrl);
        const pdf = await loadingTask.promise;

        if (!isMounted) return;

        // Render first page
        const page = await pdf.getPage(1);
        
        if (!isMounted) return;

        const viewport = page.getViewport({ scale: 1.5 });
        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext("2d");
        if (!context) return;

        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
          canvas: canvas
        };

        renderTask = page.render(renderContext);
        await renderTask.promise;

        if (isMounted) {
          setLoading(false);
        }
      } catch (err) {
        console.error("PDF load error:", err);
        if (isMounted) {
          setError("Nie udało się załadować pliku PDF. Prawdopodobnie wystąpił problem z CORS lub plik jest uszkodzony.");
          setLoading(false);
        }
      }
    };

    loadPdf();

    return () => {
      isMounted = false;
      if (renderTask) {
        renderTask.cancel();
      }
    };
  }, [url]);

  return (
    <div className="w-full min-h-[600px] h-full bg-slate-100 flex items-center justify-center rounded-lg border border-slate-200 overflow-auto relative">
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-10">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-2" />
          <span className="text-sm text-slate-600 font-medium">Ładowanie dokumentu...</span>
        </div>
      )}
      
      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-white z-10 p-6 text-center">
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

      <canvas ref={canvasRef} className="max-w-full shadow-sm" />
    </div>
  );
}
