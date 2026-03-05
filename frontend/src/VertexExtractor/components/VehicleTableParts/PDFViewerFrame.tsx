import { useState, useEffect, useRef, useCallback } from "react";
import { Loader2, X, ChevronLeft, ChevronRight } from "lucide-react";
import * as pdfjsLib from "pdfjs-dist";

// Use the bundled worker from pdfjs-dist
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

interface PDFViewerFrameProps {
  rawPdfUrl: string;
  brand: string;
  model: string;
}

export function PDFViewerFrame({ rawPdfUrl, brand, model }: PDFViewerFrameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if the URL points to a PDF file
  const isPdf = /\.pdf(\?.*)?$/i.test(rawPdfUrl);

  // Load PDF document
  useEffect(() => {
    if (!isPdf) {
      setIsLoading(false);
      setError("Podgląd inline obsługuje wyłącznie pliki PDF. Ten dokument (XLS/XLSX) można otworzyć w nowej karcie.");
      return;
    }

    let cancelled = false;

    const loadPdf = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const proxyUrl = `${baseUrl}/api/pdf-proxy?url=${encodeURIComponent(rawPdfUrl)}`;

        const response = await fetch(proxyUrl);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const arrayBuffer = await response.arrayBuffer();
        const doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

        if (!cancelled) {
          setPdfDoc(doc);
          setTotalPages(doc.numPages);
          setCurrentPage(1);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("PDF.js Load Error:", err);
          setError("Nie udało się załadować dokumentu PDF.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadPdf();

    return () => {
      cancelled = true;
    };
  }, [rawPdfUrl, isPdf]);

  // Render current page — fit to container width
  const renderPage = useCallback(async () => {
    if (!pdfDoc || !canvasRef.current || !containerRef.current) return;

    try {
      const page = await pdfDoc.getPage(currentPage);

      // Calculate scale to fit container width
      const containerWidth = containerRef.current.clientWidth - 32; // subtract padding
      const unscaledViewport = page.getViewport({ scale: 1.0 });
      const fitScale = containerWidth / unscaledViewport.width;

      const viewport = page.getViewport({ scale: fitScale });
      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");
      if (!context) return;

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      await page.render({
        canvasContext: context,
        viewport,
        canvas,
      }).promise;
    } catch (err) {
      console.error("PDF.js Render Error:", err);
    }
  }, [pdfDoc, currentPage]);

  useEffect(() => {
    renderPage();
  }, [renderPage]);

  // Re-render on window resize
  useEffect(() => {
    const handleResize = () => renderPage();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [renderPage]);

  const goToPrevPage = () => setCurrentPage((p) => Math.max(1, p - 1));
  const goToNextPage = () => setCurrentPage((p) => Math.min(totalPages, p + 1));

  return (
    <div className="mt-4 pt-4 border-t border-slate-200 w-full relative bg-slate-100 rounded-lg overflow-hidden flex flex-col">
      {/* Loading state */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
          <p className="text-sm font-medium text-slate-500">Trwa ładowanie dokumentu z serwera...</p>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20 text-red-500">
          <X className="w-10 h-10 mb-4" />
          <p className="text-sm font-medium mb-4">{error}</p>
          <a
            href={rawPdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-blue-600 font-medium text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors text-sm"
          >
            Otwórz dokument w nowej karcie
          </a>
        </div>
      )}

      {/* PDF Canvas with navigation */}
      {!isLoading && !error && pdfDoc && (
        <>
          {/* Pagination toolbar */}
          <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-slate-200 shrink-0">
            <span className="text-xs font-medium text-slate-500">
              {brand} {model}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={goToPrevPage}
                disabled={currentPage <= 1}
                className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Poprzednia strona"
              >
                <ChevronLeft className="w-4 h-4 text-slate-600" />
              </button>
              <span className="text-xs font-semibold text-slate-700 min-w-[80px] text-center">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={goToNextPage}
                disabled={currentPage >= totalPages}
                className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Następna strona"
              >
                <ChevronRight className="w-4 h-4 text-slate-600" />
              </button>
            </div>
            <a
              href={rawPdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
            >
              Otwórz w nowej karcie ↗
            </a>
          </div>

          {/* Canvas area — fits width, scrolls vertically */}
          <div
            ref={containerRef}
            className="overflow-y-auto flex justify-center bg-slate-200/60 p-4"
            style={{ maxHeight: "85vh" }}
          >
            <canvas
              ref={canvasRef}
              className="shadow-lg rounded bg-white block"
            />
          </div>
        </>
      )}
    </div>
  );
}
